#!/usr/bin/env python3
"""레퍼런스·자체 게시물을 '그 계정 평소 대비 몇 배'(outlier multiple)로 랭킹한다.

Ported from swipe.py in github.com/Jakeschincariol/instagram-agent-skill (MIT, (c) 2026 Jake Schincariol;
full notice in LICENSE-instagram-agent-skill).
영어 훅 분류·hookscore·단어 수는 뺐고(한국어에서 0/4 분류), sends/saves/follows/reach 비율을 더했다.

Usage: python3 ig_rank.py posts.tsv [--json]
       python3 ig_rank.py posts.csv            (확장자 .csv 면 쉼표 구분)

입력: 헤더 줄이 있는 TSV/CSV. 필수 열 views; 기준선은 median(그 계정 최근 게시물 조회수 중앙값),
없으면 followers. 선택 열: account, hook, url, sends, saves, follows, reach.
reach 와 sends/follows 가 있으면 sends/reach, follows/reach 를 % 로 낸다. '#' 로 시작하는 줄은 무시.
판정: 3x 이상 = 레퍼런스로 인정, 1.5x 미만 = 평범한 날 (content-common 규칙).
"""
import argparse
import csv
import io
import json
import re
import statistics
import sys

STRONG, ORDINARY = 3.0, 1.5
UNITS = {"억": 100_000_000, "만": 10_000, "천": 1_000, "k": 1_000, "m": 1_000_000}
NUM_COLS = ("views", "median", "followers", "sends", "saves", "follows", "reach")


def num(cell):
    """'12,000' / '1.2만' / '3.4K' → int. 빈 칸은 None."""
    s = (cell or "").strip().replace(",", "")
    if not s:
        return None
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(억|만|천|[kKmM])?\s*(회|뷰|명|views?)?", s)
    if not m:
        print(f"숫자로 못 읽어서 비워 둠: {cell!r}", file=sys.stderr)
        return None
    mult = UNITS.get((m.group(2) or "").lower(), 1)
    return int(float(m.group(1)) * mult)


def read_rows(path):
    raw = sys.stdin.read() if path == "-" else open(path, encoding="utf-8-sig").read()
    lines = [l for l in raw.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    if not lines:
        return []
    delim = "," if path.lower().endswith(".csv") or ("\t" not in lines[0] and "," in lines[0]) else "\t"
    reader = csv.reader(io.StringIO("\n".join(lines)), delimiter=delim)
    head = [c.strip().lower() for c in next(reader)]
    if "views" not in head:
        sys.exit("헤더에 views 열이 없어요. 예: account\\tmedian\\tviews\\thook")
    rows = []
    for cells in reader:
        r = dict(zip(head, [c.strip() for c in cells]))
        for k in NUM_COLS:
            r[k] = num(r.get(k))
        if r["views"]:
            rows.append(r)
    return rows


def pct(a, b):
    return round(a * 100 / b, 2) if a is not None and b else None


def analyse(rows):
    for r in rows:
        r["baseline"] = r.get("median") or r.get("followers")
        r["baseline_kind"] = "median" if r.get("median") else "followers" if r.get("followers") else None
        r["outlier"] = round(r["views"] / r["baseline"], 2) if r["baseline"] else None
        r["verdict"] = ("?" if r["outlier"] is None else "strong" if r["outlier"] >= STRONG
                        else "ordinary" if r["outlier"] < ORDINARY else "ok")
        r["sends_reach"] = pct(r.get("sends"), r.get("reach"))
        r["follows_reach"] = pct(r.get("follows"), r.get("reach"))
        r["saves_reach"] = pct(r.get("saves"), r.get("reach"))
    ranked = sorted(rows, key=lambda r: -(r["outlier"] or 0))
    scored = [r for r in ranked if r["outlier"] is not None]   # 기준선 없는 줄은 상·하위 비교에서 뺀다
    third = len(scored) // 3
    top, bottom = scored[:third], scored[-third:] if third else []

    def med(items, key):
        vals = [i[key] for i in items if i.get(key) is not None]
        return round(statistics.median(vals), 2) if vals else None

    compare = {k: (med(top, k), med(bottom, k))
               for k in ("outlier", "sends_reach", "saves_reach", "follows_reach")}
    return {
        "baseline": "/".join(sorted({r["baseline_kind"] for r in rows if r["baseline_kind"]})) or "none",
        "n": len(ranked),
        "accounts": len({r.get("account", "") for r in ranked}),
        "posts": ranked,
        "top_vs_bottom": compare,
    }


def fmt(v):
    return f"{v:.2f}" if v is not None else "-"


def render(a):
    print(f"RANK  ·  {a['n']}개  ·  {a['accounts']}계정  ·  기준선: {a['baseline']}")
    if "/" in a["baseline"]:
        print("  주의: median 줄과 followers 줄이 섞여 있다. followers 기준 배수는 훨씬 작게 나오니 같은 잣대로 비교하지 말 것")
    print("=" * 78)
    print(f"  {'mult':>7}  {'verdict':<8} {'account':<14} {'views':>9}  {'send%':>6} {'save%':>6} {'follow%':>7}")
    for r in a["posts"]:
        mult = f"{r['outlier']:.1f}x" if r["outlier"] is not None else "?"
        print(f"  {mult:>7}  {r['verdict']:<8} {(r.get('account') or '')[:14]:<14} {r['views']:>9,}"
              f"  {fmt(r['sends_reach']):>6} {fmt(r['saves_reach']):>6} {fmt(r['follows_reach']):>7}")
        label = r.get("hook") or r.get("url")
        if label:
            print(f"           \"{label[:60]}\"")
    print("-" * 78)
    if a["top_vs_bottom"]["outlier"][0] is not None:
        print("상위 1/3 vs 하위 1/3 (중앙값)")
        for k, (t, b) in a["top_vs_bottom"].items():
            if t is not None or b is not None:
                print(f"  {k:<14} 상위 {t if t is not None else '-'}  vs  하위 {b if b is not None else '-'}")
    print(f"\n  {STRONG:g}x 이상만 레퍼런스로 인정, {ORDINARY:g}x 미만은 평범한 날. 손으로 모은 표본은 근거이지 증명이 아니다.")


def main():
    ap = argparse.ArgumentParser(description="게시물을 계정 평소 대비 배수로 랭킹")
    ap.add_argument("input", nargs="?", default="-", help="TSV/CSV 파일, - 면 stdin")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    rows = read_rows(args.input)
    if not rows:
        sys.exit("쓸 수 있는 줄이 없어요 (views 가 비었거나 0).")
    a = analyse(rows)
    if args.json:
        print(json.dumps(a, indent=2, ensure_ascii=False))
    else:
        render(a)


if __name__ == "__main__":
    main()
