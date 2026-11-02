#!/usr/bin/env python3
"""한국어 인스타 캡션 린터: 피드에서 '... 더 보기' 전에 보이는 부분을 박스로 보여주고 규칙을 점검한다.

Ported from caption.py in github.com/Jakeschincariol/instagram-agent-skill (MIT, (c) 2026 Jake Schincariol;
full notice in LICENSE-instagram-agent-skill).
한국어 패치: 해시태그를 유니코드로 세고(원본은 #AI뉴스 를 #AI 로 셌다), 한국어 CTA를 인식하고,
DM 약속 문구를 FAIL 로 잡고, 박스 줄바꿈을 east_asian_width(한글 2칸) 기준으로 한다.

Usage: python3 ig_caption.py caption.txt [--truncate 125] [--keywords "엔비디아,실적"] [--reward-slide] [--json]
       pbpaste | python3 ig_caption.py -

--truncate 는 '더 보기' 전 글자 수 근사치(기본 125, 영어 기준). 한글은 글자가 넓어서 실제 폰에서는 더 일찍
잘릴 수 있다. 확인 전까지는 박스가 아니라 첫 줄 길이(카드뉴스는 30자 이하)를 기준으로 본다.
--reward-slide: 게시물에 content-common 조건을 다 채운 보상 슬라이드가 있을 때만. DM 문구를 FAIL 대신 WARN.
마지막 줄은 instagram-card-news 작업 보고에 그대로 붙이는 `caption-check:` 줄. exit 0 = READY, 1 = 아니면.
"""
import argparse
import json
import re
import sys
import unicodedata

LIMIT = 2200
TRUNCATE = 125
HASHTAG_LIMIT = 5

LINK_RE = re.compile(r"https?://\S+|\bwww\.\S+|\b[a-z0-9-]+\.(?:com|co|io|net|org|ai|app|kr)/\S*", re.I)
HASHTAG_RE = re.compile(r"#\w+")          # \w 는 유니코드라 #엔비디아 #AI뉴스 를 통째로 센다
MENTION_RE = re.compile(r"(?:^|\s)(@[\w.]+)")
EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF☀-➿]")
CONCRETE_RE = re.compile(r"\d|(?<![A-Za-z])[A-Z][A-Za-z]{2,}(?![A-Za-z])")  # Claude가: 한글 조사 앞에는 \b 가 없다   # 숫자, 또는 Claude·Nvidia 같은 이름

ASKS = [
    (re.compile(r"저장\s*(해|하|각)"), "저장"),
    (re.compile(r"공유\s*(해|하)"), "공유"),
    (re.compile(r"팔로우\s*(해|하|하면|하고|하시)"), "팔로우"),
    (re.compile(r"댓글\s*(로|에|을|좀|\s*남|\s*달)"), "댓글"),
    (re.compile(r"프로필\s*(링크|상단)|link in (my )?bio"), "프로필 링크"),
    (re.compile(r"(?i)\bsave (this|it)\b"), "save"),
    (re.compile(r"(?i)\bshare (this|it)\b"), "share"),
    (re.compile(r"(?i)\bfollow (me|for)\b"), "follow"),
]

# DM 약속·유도: content-common 이 Instagram 보상 슬라이드 외에는 금지한다.
DM_RE = re.compile(
    r"(?i)(dm|디엠)\s*(으로|로)?\s*(보내|드려|드릴|드립|전달|쏴)"
    r"|(dm|디엠)\s*(주세요|주시면|보내\s*주세요|부탁)"
    r"|댓글.{0,40}(보내\s*드|드릴게|드려요|드립니다)"
    r"|(자료|파일|링크|pdf|템플릿|원본|전문|리스트).{0,12}(보내\s*드|드릴게|드려요|드립니다)"
    r"|\bcomment\b.{0,30}\b(send|dm)\b|\bdm me\b")

# instagram-card-news 의 봇 신호(2026-10-29): 첫 줄 머리 '(저장/공유)' 태그, '여러분 ~? 👇' 마무리.
BOT_RE = [
    ("first", re.compile(r"^\s*[\[(【]\s*(저장|공유|필독)"), "첫 줄 머리 (저장/공유) 태그"),
    ("last", re.compile(r"여러분[^\n]{0,40}\?\s*[👇⬇️]*\s*$"), "'여러분 ~?' 마무리 질문"),
]


def width(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def wrap(line, cols):
    """표시 폭 기준 줄바꿈. 인스타는 글자 중간에서도 자르므로 단어 경계는 무시한다."""
    out, cur, cur_w = [], "", 0
    for c in line:
        w = width(c)
        if cur_w + w > cols:
            out.append(cur)
            cur, cur_w = "", 0
        cur += c
        cur_w += w
    return out + [cur]


def render_box(window, truncated, cols=52):
    print("\n  피드에 보이는 부분")
    print("  +" + "-" * (cols + 2) + "+")
    lines = [w for raw in window.split("\n") for w in wrap(raw, cols)]
    for line in lines[:8]:
        print(f"  | {line}{' ' * (cols - width(line))} |")
    tail = " ... 더 보기 " if truncated else " (전부 보임) "
    print("  +" + "-" * (cols + 2 - width(tail)) + tail + "+")


def analyse(text, cut=TRUNCATE, keywords=(), reward_slide=False):
    text = text.strip()
    body_nolink = LINK_RE.sub(" ", text)
    tags = HASHTAG_RE.findall(body_nolink)
    links = LINK_RE.findall(text)
    no_tags = HASHTAG_RE.sub("", body_nolink)
    body_lines = [l.strip() for l in no_tags.splitlines() if l.strip()]
    first_line = text.splitlines()[0].strip() if text else ""
    emoji = EMOJI_RE.findall(no_tags)
    window = text[:cut]
    truncated = len(text) > cut
    asks = [name for p, name in ASKS if p.search(text)]
    dm = [m.group(0) for m in DM_RE.finditer(text)]
    last_line = body_lines[-1] if body_lines else ""
    lines = {"first": first_line, "last": last_line}
    bots = [name for where, p, name in BOT_RE if p.search(lines[where])]
    keywords = [k.strip() for k in keywords if k.strip()]

    checks = []

    def add(name, status, detail):
        checks.append({"check": name, "status": status, "detail": detail})

    add("LENGTH", "FAIL" if len(text) > LIMIT else "PASS", f"{len(text)} / {LIMIT}자")
    if not first_line:
        add("FIRST LINE", "FAIL", "빈 줄로 시작")
    elif first_line[0] in "#@":
        add("FIRST LINE", "FAIL", "해시태그·멘션으로 시작. 첫 줄은 문장 자리")
    else:
        add("FIRST LINE", "PASS" if len(first_line) <= cut else "WARN", f"{len(first_line)}자")
    concrete = CONCRETE_RE.search(window)
    add("HOOK CONCRETE", "PASS" if concrete else "WARN",
        "보이는 부분에 숫자·이름 있음" if concrete else "보이는 부분에 숫자·이름이 없음")
    add("HASHTAGS", "FAIL" if len(tags) > HASHTAG_LIMIT else "PASS",
        f"{len(tags)}개 / 최대 {HASHTAG_LIMIT}" + (f": {' '.join(tags)}" if tags else ""))
    tag_visible = HASHTAG_RE.search(window)
    add("TAG PLACEMENT", "WARN" if tag_visible else "PASS",
        "보이는 부분에 해시태그가 있음" if tag_visible else "태그는 더 보기 아래")
    add("LINKS", "WARN" if links else "PASS",
        f"링크 {len(links)}개. 캡션 링크는 안 눌린다" if links else "링크 없음")
    if not dm:
        add("DM PROMISE", "PASS", "없음")
    else:
        status, why = (("WARN", "보상 슬라이드 조건(content-common) 다시 확인") if reward_slide
                       else ("FAIL", "DM 약속은 보상 슬라이드가 있을 때만 (content-common)"))
        add("DM PROMISE", status, f"{', '.join(dm[:3])} — {why}")
    if len(asks) == 1:
        add("ONE ASK", "PASS", f"CTA: {asks[0]}")
    else:
        add("ONE ASK", "WARN", f"CTA {len(asks)}개 ({', '.join(asks)})" if asks else "CTA 없음")
    add("EMOJI", "WARN" if len(emoji) > 5 else "PASS", f"{len(emoji)}개")
    add("BOT SIGNAL", "WARN" if bots else "PASS", ", ".join(bots) or "없음")
    if keywords:
        missing = [k for k in keywords if k.lower() not in text.lower()]
        add("SEARCH TERMS", "PASS" if not missing else "WARN",
            f"{len(keywords) - len(missing)}/{len(keywords)}" + (f", 빠짐: {', '.join(missing)}" if missing else ""))

    fails = sum(c["status"] == "FAIL" for c in checks)
    warns = sum(c["status"] == "WARN" for c in checks)
    first_body = body_lines[0] if body_lines else ""
    summary = (f"caption-check: 첫줄 {len(first_body)}자 | {len(''.join(body_lines))}자 {len(body_lines)}줄 | "
               f"이모지 {len(emoji)} | 태그 {len(tags)} | 봇 신호 {len(bots)}")
    return {"characters": len(text), "truncate_at": cut, "visible": window, "truncated": truncated,
            "hashtags": tags, "links": links, "asks": asks, "dm_promises": dm, "bot_signals": bots,
            "checks": checks, "verdict": "FIX" if fails else "REVIEW" if warns else "READY", "summary": summary}


def render(a):
    print(f"CAPTION LINT  ·  {a['characters']}자  ·  태그 {len(a['hashtags'])}  ·  CTA {len(a['asks'])}")
    render_box(a["visible"], a["truncated"])
    print()
    for c in a["checks"]:
        print(f"  {c['status']:<5} {c['check']:<14} {c['detail']}")
    print(f"\n  VERDICT  {a['verdict']}\n{a['summary']}")


def main():
    ap = argparse.ArgumentParser(description="한국어 인스타 캡션 린트")
    ap.add_argument("input", nargs="?", default="-", help="캡션 파일, - 면 stdin")
    ap.add_argument("--truncate", type=int, default=TRUNCATE, help=f"더 보기 전 글자 수 (기본 {TRUNCATE})")
    ap.add_argument("--keywords", default="", help="쉼표로 구분한 검색어")
    ap.add_argument("--reward-slide", action="store_true", help="보상 슬라이드가 있는 게시물: DM 문구 FAIL→WARN")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    raw = sys.stdin.read() if args.input == "-" else open(args.input, encoding="utf-8").read()
    a = analyse(raw, args.truncate, args.keywords.split(","), args.reward_slide)
    if args.json:
        print(json.dumps(a, indent=2, ensure_ascii=False))
    else:
        render(a)
    sys.exit(0 if a["verdict"] == "READY" else 1)


if __name__ == "__main__":
    main()
