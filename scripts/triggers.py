#!/usr/bin/env python3
"""Deterministic trigger check: does a prompt meant for a skill pick that skill's description first?

  python3 scripts/triggers.py            train prompts of plugins/base/evals/triggers.json: rank of the meant skill, top-3
  python3 scripts/triggers.py --test     the held-out test prompts, the ones check.py judges, with floors
  python3 scripts/triggers.py --pairs    the most similar description pairs, highest first

Tune a description against train only; test is held out (as skill-creator's run_loop.py splits train/test), so a
rank1 ratio measured on it says how the description does on prompts it wasn't written for.
A miss means the description lacks the words people use for that task: fix the description, never the prompt.
Floors in triggers.json record a skill that doesn't pass yet; they only go up.
"""
import importlib.util
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "plugins" / "base" / "evals" / "triggers.json"
STOP = set("""an and are as at be by for from in into is it its of on or that the this to with when what which who
use used uses using via not no any all one their them they than then there these those your you was were
has have had do does done can could should would will may might must also only each every other own same so such
""".split())


def stem(word):
    if re.search(r"(ss|x|z|ch|sh)es$", word):
        word = word[:-2]
    elif not re.search(r"(ss|us|is)$", word):
        for suffix in ("ing", "ed", "s"):
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                word = word[: -len(suffix)]
                break
    return word[:-1] if word.endswith("e") and len(word) >= 4 else word


def tokens(text):
    out = []
    for run in re.findall(r"[a-z0-9]+|[가-힣]+", text.lower()):
        if not run.isascii():
            out += [run[i:i + 2] for i in range(len(run) - 1)]
        elif run not in STOP and len(run) > 1:
            out.append(stem(run))
    return out


def check_module():
    spec = importlib.util.spec_from_file_location("check", ROOT / "scripts" / "check.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def listing(frontmatter, root=None):
    out = {}
    for md in sorted((root or ROOT).glob("plugins/*/skills/*/SKILL.md")):
        fm = frontmatter(md.read_text(encoding="utf-8")) or {}
        if fm.get("disable-model-invocation", "").lower() in ("true", "yes", "on") or not fm.get("description"):
            continue
        if md.parent.name in out:
            raise ValueError(f"two plugins have a skill named {md.parent.name}: key triggers.json by plugin before scoring them")
        out[md.parent.name] = md.parent.name.replace("-", " ") + " " + fm["description"]
    return out


class Index:
    def __init__(self, docs):
        self.names = list(docs)
        counts = {n: Counter(tokens(t)) for n, t in docs.items()}
        df = Counter(w for c in counts.values() for w in c)
        self.idf = {w: math.log((len(docs) + 1) / (d + 1)) + 1 for w, d in df.items()}
        self.vecs = {n: self.vector(c) for n, c in counts.items()}

    def vector(self, counts):
        v = {w: (1 + math.log(c)) * self.idf[w] for w, c in counts.items() if w in self.idf}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {w: x / norm for w, x in v.items()}

    def rank(self, prompt):
        q = self.vector(Counter(tokens(prompt)))
        scores = {n: sum(x * v.get(w, 0.0) for w, x in q.items()) for n, v in self.vecs.items()}
        order = sorted(self.names, key=lambda n: (-scores[n], n))
        # a prompt that matches nothing, or ties, picks no skill: the alphabet would otherwise decide
        top = scores[order[0]] if order else 0.0
        winner = order[0] if top > 0 and (len(order) < 2 or top > scores[order[1]]) else None
        return order, winner

    def similarity(self, a, b):
        va, vb = self.vecs[a], self.vecs[b]
        return sum(x * vb.get(w, 0.0) for w, x in va.items())


def measure(cases, docs, split):
    index = Index(docs)
    out = {}
    for name, case in cases["skills"].items():
        row = {"rank1": 0, "prompts": len(case.get(split, [])), "floor": case.get("min_rank1", len(case.get(split, []))),
               "allowed": case.get("max_negative_hits", 0), "misses": [], "negative_hits": [], "korean": [0, 0]}
        for prompt in case.get(split, []):
            order, winner = index.rank(prompt)
            ko = bool(re.search(r"[가-힣]", prompt))
            row["korean"][1] += ko
            if winner == name:
                row["rank1"] += 1
                row["korean"][0] += ko
            else:
                row["misses"].append((prompt, order[:3], order.index(name) + 1 if name in order else None))
        for prompt in case.get("negative", []):
            order, winner = index.rank(prompt)
            if winner == name:
                row["negative_hits"].append((prompt, order[:3]))
        out[name] = row
    return out, index


def pairs(index):
    names = index.names
    sims = [(index.similarity(a, b), a, b) for i, a in enumerate(names) for b in names[i + 1:]]
    return sorted(sims, reverse=True)


def problems(cases, docs):
    found = []
    for name in cases["skills"]:
        if name not in docs:
            found.append(f"{name}: no model-invocable skill by that name — remove it from triggers.json or restore the skill")
    for name, case in cases["skills"].items():
        both = set(case.get("train", [])) & set(case["test"])
        if both:
            found.append(f"{name}: {sorted(both)} in both train and test — a held-out prompt can't also be tuned on; keep it in test")
    result, index = measure(cases, docs, "test")
    hits = total = ko_hits = ko_total = 0
    for name, row in result.items():
        if name not in docs:
            continue
        hits, total = hits + row["rank1"], total + row["prompts"]
        ko_hits, ko_total = ko_hits + row["korean"][0], ko_total + row["korean"][1]
        floor, allowed = row["floor"], row["allowed"]
        if row["rank1"] < floor:
            missed = "; ".join(f"{p!r} → {', '.join(top)}" for p, top, _ in row["misses"])
            found.append(f"{name}: {row['rank1']}/{row['prompts']} test prompts pick it first, floor {floor} — "
                         f"fix its description so these pick it (missed: {missed})")
        if len(row["negative_hits"]) > allowed:
            wrong = "; ".join(f"{p!r} → {', '.join(top)}" for p, top in row["negative_hits"])
            found.append(f"{name}: {len(row['negative_hits'])} negative prompts pick it first, allowed {allowed} — "
                         f"fix its description so they go elsewhere ({wrong})")
        case = cases["skills"][name]
        if row["rank1"] > floor:
            found.append(f"{name}: {row['rank1']} test prompts pick it first, above its floor {floor} — raise min_rank1 to {row['rank1']}"
                         + (" or remove it" if row["rank1"] == row["prompts"] else "") + " (a floor records today's value)")
        if "max_negative_hits" in case and len(row["negative_hits"]) < allowed:
            found.append(f"{name}: {len(row['negative_hits'])} negative prompts pick it first, below max_negative_hits {allowed} — lower it")
    limit = cases["max_similarity"]
    allowed_pairs = {tuple(sorted(p)) for p in cases.get("similar_pairs", [])}
    for sim, a, b in pairs(index):
        if sim <= limit:
            break
        if tuple(sorted((a, b))) not in allowed_pairs:
            found.append(f"{a} and {b}: descriptions are {sim:.2f} similar (limit {limit}) — "
                         "fix one description so the two say different things")
    pct = round(100 * hits / total) if total else 0
    skills = sum(n in docs for n in result)
    return f"triggers: rank1 {hits}/{total} ({pct}%) across {skills} skills (held-out test; Korean {ko_hits}/{ko_total})", found


def main():
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    docs = listing(check_module().frontmatter)
    split = "test" if "--test" in sys.argv else "train"
    result, index = measure(cases, docs, split)
    if "--pairs" in sys.argv:
        for sim, a, b in pairs(index)[:15]:
            print(f"{sim:.3f}  {a}  {b}")
        return
    for name, row in result.items():
        floor = f" (floor {row['floor']})" if split == "test" else ""
        print(f"{name}: {split} rank1 {row['rank1']}/{row['prompts']}{floor}, Korean {row['korean'][0]}/{row['korean'][1]}, "
              f"negative hits {len(row['negative_hits'])}")
        for prompt, top, rank in row["misses"]:
            print(f"  miss  {prompt!r}  rank {rank}  top3 {', '.join(top)}")
        for prompt, top in row["negative_hits"]:
            print(f"  neg   {prompt!r}  top3 {', '.join(top)}")
    if split == "train":
        hits, total = sum(r["rank1"] for r in result.values()), sum(r["prompts"] for r in result.values())
        ko = [sum(r["korean"][i] for r in result.values()) for i in (0, 1)]
        print(f"train: rank1 {hits}/{total}, Korean {ko[0]}/{ko[1]} (not judged; --test for what check.py judges)")
    line, found = problems(cases, docs)
    print(line)
    for p in found:
        print("FAIL", p)


if __name__ == "__main__":
    main()
