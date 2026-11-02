#!/usr/bin/env python3
"""캡션·대본·카드 문구의 보이지 않는 문자와 타이포 기호를 정리한다. 텍스트만 다룬다.

Ported from humanize.py (passes 1-2) in github.com/Jakeschincariol/instagram-agent-skill (MIT, (c) 2026 Jake Schincariol;
full notice in LICENSE-instagram-agent-skill).
영어 slop 치환(pass 3)과 detect.py 의 "human score" 는 가져오지 않았다(한국어에서는 0건 탐지, 점수 무의미).
AI 라벨·메타데이터와는 무관하고 '탐지 불가'를 만들지 않는다. 라벨 판단은 shorts-common 규칙을 따른다.

Usage: python3 ig_clean.py draft.txt [-o clean.txt] [--report] [--slop [slop_ko.json]] [--json]

1. 보이지 않는 문자: ZWSP·ZWJ·BOM·soft hyphen·태그 문자 등은 삭제, NBSP·얇은 공백 등은 일반 공백으로.
2. 타이포: em dash → 쉼표, en dash → 하이픈, 둥근 따옴표 → 곧은 따옴표, … → ..., • → -.
   가운뎃점(·)은 한국어 나열에 쓰므로 그대로 둔다. URL 안은 건드리지 않는다.
--slop: slop_ko.json(사용자가 고쳐 쓰는 시작 목록)의 표현을 찾아 '보고만' 한다. 고쳐 쓰기는 사람·모델 몫.
"""
import argparse
import json
import os
import re
import sys
import unicodedata
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SLOP = os.path.join(HERE, "slop_ko.json")
URL_RE = re.compile(r"https?://\S+|www\.\S+|\S+@\S+\.\S+")

DELETE = {0x200B: "ZERO WIDTH SPACE", 0x200C: "ZERO WIDTH NON-JOINER", 0x200D: "ZERO WIDTH JOINER",
          0x2060: "WORD JOINER", 0xFEFF: "BOM", 0x00AD: "SOFT HYPHEN", 0x180E: "MONGOLIAN VOWEL SEPARATOR",
          0x061C: "ARABIC LETTER MARK", 0x200E: "LRM", 0x200F: "RLM", 0x2063: "INVISIBLE SEPARATOR"}
SPACE = {0x00A0: "NO-BREAK SPACE", 0x202F: "NARROW NO-BREAK SPACE", 0x2009: "THIN SPACE",
         0x2007: "FIGURE SPACE", 0x2003: "EM SPACE", 0x2002: "EN SPACE", 0x3000: "IDEOGRAPHIC SPACE"}
TYPO = {"‘": "'", "’": "'", "“": '"', "”": '"', "…": "...", "′": "'", "•": "-"}


def protect_urls(text):
    found = []

    def stash(m):
        found.append(m.group(0))
        return f"\x00URL{len(found) - 1}\x00"

    return URL_RE.sub(stash, text), found


def restore_urls(text, found):
    for i, url in enumerate(found):
        text = text.replace(f"\x00URL{i}\x00", url)
    return text


def is_emoji(c):
    cp = ord(c)
    return cp >= 0x1F000 or 0x2600 <= cp <= 0x27BF


def pass_invisible(text):
    hits = Counter()

    def keep(i, c):
        cp = ord(c)
        if cp == 0x200D and 0 < i < len(text) - 1 and is_emoji(text[i - 1]) and is_emoji(text[i + 1]):
            return c   # 이모지 사이 ZWJ(👨‍💻)는 이모지의 일부라 남긴다
        if cp in DELETE or 0xE0000 <= cp <= 0xE007F or unicodedata.category(c) == "Cf":
            name = DELETE.get(cp, "TAG CHARACTER" if cp >= 0xE0000 else unicodedata.name(c, f"U+{cp:04X}"))
            hits[f"{name} → 삭제"] += 1
            return ""
        if cp in SPACE:
            hits[f"{SPACE[cp]} → 공백"] += 1
            return " "
        return c

    return "".join(keep(i, c) for i, c in enumerate(text)), dict(hits)


def pass_typographic(text):
    hits = {}
    # 대시 자리는 먼저 \x01 로 표시해 두고, 그 자리 주변 문장부호만 정리한다(사용자가 쓴 쉼표·줄바꿈은 그대로).
    n = text.count("—")
    if n:
        hits["— EM DASH → ,"] = n
        text = re.sub(r"[ \t]*—[ \t]*", "\x01", text)
    n = text.count("–")
    if n:
        hits["– EN DASH → -"] = n
        text = re.sub(r"[ \t]*–[ \t]*(?=\d)", "-", text)
        text = re.sub(r"[ \t]+–[ \t]+", "\x01", text)
        text = text.replace("–", "-")
    for ch, to in TYPO.items():
        n = text.count(ch)
        if n:
            hits[f"{ch} → {to}"] = n
            text = text.replace(ch, to)
    text = re.sub(r"\x01[ \t]*(?=[,.;:!?\n]|$)", "", text, flags=re.M)
    text = re.sub(r"^\x01", "", text, flags=re.M)
    text = text.replace("\x01", ", ")
    return text, hits


def scan_slop(text, path):
    """한국어 항목은 \\b 없이 매칭한다(조사 앞에서 \\b 가 기대대로 안 걸린다)."""
    lex = json.load(open(path, encoding="utf-8"))
    flags = []
    for e in lex["items"]:
        found = re.findall(e["regex"], text, re.MULTILINE)
        if found:
            flags.append({"name": e["name"], "count": len(found), "fix": e.get("fix", "")})
    return flags


def clean(text, slop=None):
    text, urls = protect_urls(text)
    text, inv = pass_invisible(text)
    text, typo = pass_typographic(text)
    text = restore_urls(text, urls)
    report = {"invisible": inv, "typographic": typo}
    if slop:
        report["slop"] = scan_slop(text, slop)
    return text.strip() + "\n", report


def render_report(r, out=sys.stderr):
    total = sum(r["invisible"].values()) + sum(r["typographic"].values())
    print(f"\nCLEAN REPORT  ·  문자 {total}개 정리", file=out)
    for title, key in (("1. 보이지 않는 문자", "invisible"), ("2. 타이포", "typographic")):
        if r[key]:
            print(title, file=out)
            for name, n in r[key].items():
                print(f"  {n:>3}x  {name}", file=out)
    if "slop" in r:
        print(f"3. 한국어 slop (자동 수정 안 함, 직접 고쳐 쓰기)  ·  {len(r['slop'])}종", file=out)
        for f in r["slop"]:
            print(f"  {f['count']:>3}x  {f['name']}" + (f"  — {f['fix']}" if f["fix"] else ""), file=out)
    print("", file=out)


def main():
    ap = argparse.ArgumentParser(description="보이지 않는 문자·타이포 정리 (텍스트만)")
    ap.add_argument("input", nargs="?", default="-", help="파일, - 면 stdin")
    ap.add_argument("-o", "--out", help="정리한 텍스트를 여기에 쓴다 (기본 stdout)")
    ap.add_argument("--report", action="store_true", help="무엇을 바꿨는지 stderr 로")
    ap.add_argument("--slop", nargs="?", const=SLOP, help=f"한국어 slop 목록으로 검사 (기본 {os.path.basename(SLOP)})")
    ap.add_argument("--json", action="store_true", help="{text, report} JSON")
    args = ap.parse_args()
    raw = sys.stdin.read() if args.input == "-" else open(args.input, encoding="utf-8").read()
    text, report = clean(raw, args.slop)
    if args.json:
        print(json.dumps({"text": text, "report": report}, indent=2, ensure_ascii=False))
        return
    if args.out:
        open(args.out, "w", encoding="utf-8").write(text)
    else:
        sys.stdout.write(text)
    if args.report or args.slop:
        render_report(report)


if __name__ == "__main__":
    main()
