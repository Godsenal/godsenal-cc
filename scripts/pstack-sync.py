#!/usr/bin/env python3
"""Keep gbase's copy of pstack (cursor/plugins, MIT) in step with upstream.

  python3 scripts/pstack-sync.py --check    one JSON line: did upstream move, and which items
  python3 scripts/pstack-sync.py --apply    regenerate every followed item, record merge diffs, update the lock
  python3 scripts/pstack-sync.py --verify   offline: followed items match the lock, no merge diff left unmerged

The lock (scripts/pstack/lock.json) says how each upstream item is handled:
  follow    regenerated from upstream on every --apply; never edited by hand
  merge     gbase keeps its own version (`into`); upstream changes land as scripts/pstack/pending/<item>.diff
  skip      not imported (`reason`)
  unusable  can't run in Claude Code (`reason`)
Its `exclude` list names upstream paths that are never copied, each with a reason.

Options: --source <dir> reads upstream from a local checkout of cursor/plugins instead of the network
(--sha names its commit); --root <dir> is the repo to write into (default: this script's repo).
Procedure for the run that applies an update: plugins/base/references/pstack-sync.md.
"""
import argparse
import difflib
import hashlib
import io
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

LOCK = "scripts/pstack/lock.json"
SNAPSHOT = "scripts/pstack/upstream"  # upstream text of merge items, the "before" side of the next diff
PENDING = "scripts/pstack/pending"
PLUGIN = "plugins/base"
AUTOMATIONS = "pstack/automations"  # not in the generated tree; listed so a new one shows up in --check
STRAY = {"node_modules", "__pycache__", ".DS_Store"}  # appear inside a followed dir at run time; not part of the copy
MOVED = {"LICENSE": "references/pstack-LICENSE"}  # gbase's own files keep the plugin root
GITHUB = "https://github.com/{repo}/blob/{ref}/pstack/{path}"
GITHUB_RAW = "https://raw.githubusercontent.com/{repo}/{ref}/pstack/{path}"  # a blob URL is an HTML page, not the image
IMAGES = {".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp"}
SCRIPT_SUFFIXES = {".sh", ".bash", ".zsh", ".py", ".js", ".mjs", ".cjs", ".ts", ".rb", ".pl", ".java"}
UPSTREAM_ADAPTER_LINE = re.compile(r"^In Claude Code, read \[the Claude Code adapter\]\([^)]*\) once per session[^\n]*\n\n?", re.M)

BLOCK = """<!-- gbase:pstack-sync — cursor/plugins pstack `{name}` 스킬을 그대로 따라가는 생성본 (MIT, Copyright (c) 2026 Lauren Tan). 직접 고치지 않는다: `python3 scripts/pstack-sync.py --apply`가 덮어쓴다. -->

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다. 코드·경로·명령어·스킬/툴 이름·상태 라벨은 그대로 둔다. 사용자가 다른 언어로 요청하면 그 언어를 따른다.

## gbase

Read [pstack-adapter.md](../../references/pstack-adapter.md) once per session before you follow this skill. It maps the Cursor names below to Claude Code and gbase, and says how to run another skill this one names.

"""

AGENT_BLOCK = """<!-- gbase:pstack-sync — cursor/plugins pstack `{name}` 에이전트를 그대로 따라가는 생성본 (MIT, Copyright (c) 2026 Lauren Tan). 직접 고치지 않는다. -->

In gbase: the plugin root is two folders above the `skills/poteto-mode/SKILL.md` path your parent gave you. Read `references/pstack-adapter.md` there before anything else; it maps the Cursor names below to Claude Code and gbase. 사용자에게 보이는 글은 한국어로 쓴다.

"""


class SyncError(Exception):
    pass


# ---------- upstream ----------

def gh(args, binary=False):
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}  # a repo-scoped token 404s on other repos
    try:
        out = subprocess.run(["gh", "api", *args], capture_output=True, env=env, timeout=180)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise SyncError(f"gh api {args[0]}: {e}")
    if out.returncode != 0:
        raise SyncError(f"gh api {args[0]}: {out.stderr.decode(errors='replace').strip()[:300]}")
    return out.stdout if binary else out.stdout.decode().strip()


def fetch_upstream(up):
    """Returns (sha, {path under the repo root: (bytes, executable)}) for the two pstack trees."""
    repo, ref = up["repo"], up["ref"]
    try:
        sha = gh([f"repos/{repo}/commits/{ref}", "--jq", ".sha"])
        blob = gh([f"repos/{repo}/tarball/{sha}"], binary=True)
    except SyncError as first:
        try:  # no gh (CI): the repo is public
            with urllib.request.urlopen(f"https://api.github.com/repos/{repo}/commits/{ref}", timeout=60) as r:
                sha = json.load(r)["sha"]
            with urllib.request.urlopen(f"https://codeload.github.com/{repo}/tar.gz/{sha}", timeout=180) as r:
                blob = r.read()
        except Exception as e:  # noqa: BLE001 — any network failure is the same report
            raise SyncError(f"{first}; https fallback: {e}")
    files = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
            for m in tar:
                if not m.isfile():
                    continue  # symlinks and devices are never copied
                rel = m.name.split("/", 1)[1] if "/" in m.name else ""
                if rel.startswith((up["tree"] + "/", AUTOMATIONS + "/")):
                    files[rel] = (tar.extractfile(m).read(), bool(m.mode & 0o111))
    except tarfile.TarError as e:
        raise SyncError(f"tarball: {e}")
    return sha, files


def read_local(source, up, sha):
    root = Path(source)
    if not (root / up["tree"]).is_dir():
        raise SyncError(f"--source {source}: no {up['tree']}/")
    files = {}
    for base in (up["tree"], AUTOMATIONS):
        for p in sorted((root / base).rglob("*")):
            if p.is_file() and not p.is_symlink():
                files[p.relative_to(root).as_posix()] = (p.read_bytes(), os.access(p, os.X_OK))
    return sha or "local", files


def upstream_items(files, up, excludes):
    """Groups upstream files into items: {item: {path relative to the generated tree: (bytes, exec)}}."""
    tree = up["tree"] + "/"
    items = {}
    for path, data in files.items():
        if path.startswith(AUTOMATIONS + "/"):
            parts = path.split("/")
            if len(parts) > 3:
                items.setdefault(f"automations/{parts[2]}", {})
            continue
        rel = path[len(tree):]
        item, _ = item_of(rel)
        bucket = items.setdefault(item, {})  # even when every file is excluded, so the item doesn't look removed
        if not any(rel.startswith(e) for e in excludes):
            bucket[rel] = data
    return items


def tree_hash(entries):
    """Stable hash of {path: (bytes, exec)}."""
    h = hashlib.sha256()
    for path in sorted(entries):
        data, executable = entries[path]
        h.update(f"{path}\0{int(executable)}\0{len(data)}\0".encode())
        h.update(data)
    return h.hexdigest()[:16]


# ---------- transform ----------

def is_script(path, data, executable):
    return executable or Path(path).suffix in SCRIPT_SUFFIXES or data.startswith(b"#!")


def out_path(rel):
    """Where a path of the generated tree lands under plugins/base. The trees share a layout on purpose, so relative links hold."""
    return MOVED.get(rel, rel)


def rewrite_links(text, rel, lock, kept):
    """Points links at where their target went: a merged item's gbase file, or upstream's GitHub page for anything not copied."""
    up = lock["upstream"]
    here = posixpath.dirname(rel)

    def swap(m):
        link = m.group(3)
        if re.match(r"[a-z]+:|#|/", link):
            return m.group(0)
        path, _, frag = link.partition("#")
        target = posixpath.normpath(posixpath.join(here, path))
        if target.startswith(".."):
            return m.group(0)
        item, rest = item_of(target)
        entry = lock["items"].get(item, {})
        mode = entry.get("mode")
        new = None
        if mode == "merge":
            into = entry["into"]
            if rest in ("", "SKILL.md") or not into.startswith("skills/"):
                new_target = into if not into.startswith("skills/") else posixpath.join(into, rest or "")
                new = posixpath.relpath(new_target, here)
        elif mode == "follow" and (target in kept or any(k.startswith(target.rstrip("/") + "/") for k in kept)):
            if out_path(target) == target:
                return m.group(0)
            new = posixpath.relpath(out_path(target), here)
        if new is None:
            url = GITHUB_RAW if posixpath.splitext(target)[1].lower() in IMAGES else GITHUB
            new = url.format(repo=up["repo"], ref=up["ref"], path=target)
        return f"{m.group(2)}({new}{'#' + frag if frag else ''})"

    return outside_code(text, r"(\])\(([^)\s]+)\)", swap)


def item_of(rel):
    """(item, path inside it) for a path of the generated tree — a file, or a directory a link points at."""
    parts = rel.split("/")
    if parts[0] in ("skills", "docs") and len(parts) > 2:
        return (parts[1] if parts[0] == "skills" else "docs/" + parts[1]), "/".join(parts[2:])
    if parts[0] in ("skills", "docs") and len(parts) == 2 and "." not in parts[1]:
        return (parts[1] if parts[0] == "skills" else "docs/" + parts[1]), ""  # a link to the item's folder
    if parts[0] == "agents" and len(parts) == 2:
        return "agents/" + parts[1].removesuffix(".md"), ""
    return "root/" + rel, ""  # README.md, LICENSE, plugin.json


def outside_code(text, pattern, fn):
    """re.sub that leaves fenced blocks and inline code alone: `handlers[name](event)` in an example is not a link."""
    out, fenced = [], False
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        elif not fenced:
            line = re.sub(r"(`[^`\n]*`)|" + pattern, lambda m: m.group(1) or fn(m), line)
        out.append(line)
    return "".join(out)


def insert_after_title(body, block):
    m = re.search(r"^(# .*\n\n?|```|~~~)", body, re.M)  # a `# comment` inside a fence is not the title
    if not m or not m.group(0).startswith("#"):
        return block + body
    return body[:m.end()] + block + body[m.end():]


def transform_skill(text, name):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise SyncError(f"skill {name}: no frontmatter")
    front, body = m.group(1), text[m.end():]
    if not re.search(r"^disable-model-invocation:\s*true\s*$", front, re.M):
        # followed skills stay out of the model's skill listing; gbase's own skills reach them by path
        front = re.sub(r"^disable-model-invocation:.*\n?", "", front, flags=re.M).rstrip("\n") + "\ndisable-model-invocation: true"
    body = UPSTREAM_ADAPTER_LINE.sub("", body)
    return f"---\n{front}\n---\n\n" + insert_after_title(body.lstrip("\n"), BLOCK.format(name=name))


def transform_agent(text, name):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise SyncError(f"agent {name}: no frontmatter")
    # a Cursor model slug in `model:` would reach the API; without the line the agent runs on the session's model
    front = re.sub(r"^(model|is_background):.*\n?", "", m.group(1), flags=re.M).rstrip("\n")
    return f"---\n{front}\n---\n\n" + insert_after_title(text[m.end():].lstrip("\n"), AGENT_BLOCK.format(name=name))


def generate(item, entries, lock, kept):
    """{output path under plugins/base: (bytes, exec)} for one followed item."""
    out = {}
    for rel, (data, executable) in entries.items():
        if rel.endswith(".md"):
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError as e:
                raise SyncError(f"{rel}: not UTF-8 ({e.reason})")
            text = rewrite_links(text, rel, lock, kept)
            if rel == f"skills/{item}/SKILL.md":
                text = transform_skill(text, item)
            elif rel.startswith("agents/"):
                text = transform_agent(text, item.split("/", 1)[1])
            data = text.encode("utf-8")
        out[out_path(rel)] = (data, executable)
    return out


def target_of(item):
    """The path under plugins/base one followed item owns (a dir, or a file for agents and top-level files)."""
    if item.startswith("agents/"):
        return item + ".md"
    if item.startswith("root/"):
        return out_path(item.removeprefix("root/"))
    if "/" in item:
        return item
    return f"skills/{item}"


def read_tree(base, target):
    path = base / target
    if path.is_file():
        return {target: (path.read_bytes(), os.access(path, os.X_OK))}
    entries = {}
    if path.is_dir():
        for p in sorted(path.rglob("*")):
            if p.is_file() and not STRAY.intersection(p.parts):
                entries[p.relative_to(base).as_posix()] = (p.read_bytes(), os.access(p, os.X_OK))
    return entries


def write_tree(base, target, entries):
    path = base / target
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()
    for rel, (data, executable) in entries.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        p.chmod(0o755 if executable else 0o644)


# ---------- commands ----------

def load_lock(root):
    path = root / LOCK
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise SyncError(f"{LOCK}: {e}")


def save_lock(root, lock):
    lock["items"] = dict(sorted(lock["items"].items()))
    (root / LOCK).write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_upstream(args, lock):
    up = lock["upstream"]
    sha, files = read_local(args.source, up, args.sha) if args.source else fetch_upstream(up)
    excludes = [e["path"] for e in lock.get("exclude", [])]
    items = upstream_items(files, up, excludes)
    if not any("/" not in k for k in items):
        raise SyncError(f"upstream {up['tree']}/skills is empty — layout changed?")
    return sha, items


def compare(lock, items):
    known = lock["items"]
    changed = {"follow": [], "merge": []}
    for name, entry in known.items():
        if entry["mode"] in changed and name in items and tree_hash(items[name]) != entry.get("hash"):
            changed[entry["mode"]].append(name)
    return {
        "skills_changed": sorted(changed["follow"]),
        "custom_changed": sorted(changed["merge"]),
        "new_upstream": sorted(set(items) - set(known)),
        "removed_upstream": sorted(set(known) - set(items)),
    }


def check(args, root):
    lock = load_lock(root)
    sha, items = load_upstream(args, lock)
    diff = compare(lock, items)
    return {"upstream_sha": sha, "locked_sha": lock["upstream"].get("sha"), "changed": any(diff.values()), **diff}


def unified(old, new):
    lines = []
    for path in sorted(set(old) | set(new)):
        a = old.get(path, (b"", False))[0].decode("utf-8", "replace").splitlines(keepends=True)
        b = new.get(path, (b"", False))[0].decode("utf-8", "replace").splitlines(keepends=True)
        lines += difflib.unified_diff(a, b, f"a/{path}", f"b/{path}")
    return "".join(line if line.endswith("\n") else line + "\n" for line in lines)


def apply(args, root):
    lock = load_lock(root)
    sha, items = load_upstream(args, lock)
    diff = compare(lock, items)
    base = root / PLUGIN
    known = lock["items"]
    kept = {rel for name, e in known.items() if e["mode"] == "follow" for rel in items.get(name, {})}
    report = {"applied": [], "pending": [], "removed": [], "scripts_new": [], "scripts_changed": [],
              "new_upstream": diff["new_upstream"]}

    # Plan first, write after: a failure while generating leaves the tree and the lock as they were.
    writes, removals, diffs = [], [], []
    for name in sorted(known):
        entry = known[name]
        target = target_of(name)
        if entry["mode"] != "follow":
            if "out" in entry and entry["mode"] != "merge":
                removals.append(target)  # was followed, now skip/unusable: the generated copy goes
                report["removed"].append(name)
            entry.pop("out", None)  # a merge item keeps the copy as gbase's own file
        if name not in items:
            if entry["mode"] == "follow":  # following upstream includes following a removal
                removals.append(target)
                del known[name]
                report["removed"].append(name)
            continue  # a removed merge/skip item stays in the lock until a person decides (see pstack-sync.md)
        upstream = items[name]
        if entry["mode"] == "follow":
            before = read_tree(base, target)
            if before and "out" not in entry:
                raise SyncError(f"{PLUGIN}/{target} exists and is not a generated copy — `{name}` can't be `follow`; "
                                f"make it `merge` with `into`, or `skip`")
            after = generate(name, upstream, lock, kept)
            for rel, (data, executable) in after.items():
                if is_script(rel, data, executable) and before.get(rel) != (data, executable):
                    report["scripts_changed" if rel in before else "scripts_new"].append(f"{PLUGIN}/{rel}")
            if before != after:
                writes.append((base, target, after))
                report["applied"].append(name)
            entry["hash"], entry["out"] = tree_hash(upstream), tree_hash(after)
        elif entry["mode"] == "merge":
            before = read_tree(root / SNAPSHOT, target)
            text = unified(before, upstream)  # an exec-bit-only change has nothing to merge
            if before and text:
                diffs.append((name, f"# pstack {name}: {lock['upstream'].get('sha', '?')[:12]} → {sha[:12]} — merge into "
                                    f"{PLUGIN}/{entry['into']}, then delete this file\n{text}"))
            if before != upstream:
                writes.append((root / SNAPSHOT, target, upstream))
            entry["hash"] = tree_hash(upstream)
    plugin_json = items.get("root/plugin.json", {}).get("plugin.json")
    if plugin_json:
        try:
            lock["upstream"]["version"] = json.loads(plugin_json[0]).get("version")
        except ValueError as e:
            raise SyncError(f"upstream plugin.json: {e}")

    for target in removals:
        write_tree(base, target, {})
    for where, target, entries in writes:
        write_tree(where, target, entries)
    for name, text in diffs:
        pending = root / PENDING / (name.replace("/", "__") + ".diff")
        pending.parent.mkdir(parents=True, exist_ok=True)
        with pending.open("a", encoding="utf-8") as f:  # an unmerged earlier diff is kept: it still has to be merged
            f.write(text)
        report["pending"].append(str(pending.relative_to(root)))
    lock["upstream"]["sha"] = sha
    save_lock(root, lock)
    report["locked_sha"] = sha
    return report


def verify(root):
    """Offline: every followed item on disk is what the last --apply wrote, and no merge diff is left unmerged."""
    lock = load_lock(root)
    problems = []
    for name, entry in sorted(lock["items"].items()):
        if entry["mode"] == "follow":
            got = tree_hash(read_tree(root / PLUGIN, target_of(name)))
            if got != entry.get("out"):
                problems.append(f"{PLUGIN}/{target_of(name)}: differs from the generated copy (follow item `{name}`) — don't edit it; rerun scripts/pstack-sync.py --apply, or change its mode in {LOCK}")
        elif entry["mode"] == "merge":
            if not (root / PLUGIN / entry.get("into", "?")).exists():
                problems.append(f"{LOCK}: merge item `{name}` points at missing {entry.get('into')}")
        else:
            if not entry.get("reason"):
                problems.append(f"{LOCK}: `{name}` is {entry['mode']} without a reason")
            if "out" in entry:
                problems.append(f"{LOCK}: `{name}` was followed and is now {entry['mode']} — run scripts/pstack-sync.py --apply to remove its generated copy")
    for p in sorted((root / PENDING).glob("*.diff")):
        problems.append(f"{p.relative_to(root)}: upstream change not merged yet — merge it into the gbase skill it names, then delete the file")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify", action="store_true", help="offline: followed items match the lock, no pending merge diffs")
    ap.add_argument("--source", help="local checkout of the upstream repo (no network)")
    ap.add_argument("--sha", help="commit of --source")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    args = ap.parse_args(argv)
    root = Path(args.root)
    try:
        if args.verify:
            problems = verify(root)
            print(json.dumps({"ok": not problems, "problems": problems}, ensure_ascii=False))
            return 1 if problems else 0
        print(json.dumps(check(args, root) if args.check else apply(args, root), ensure_ascii=False))
        return 0
    except SyncError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
