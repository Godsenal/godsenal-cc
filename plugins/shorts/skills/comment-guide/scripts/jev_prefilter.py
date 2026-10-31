#!/usr/bin/env python3
"""댓글 대상 사전 필터: 후보 글을 Claude가 읽기 전에 Jev로 스팸·'끼어들 만함' 낮은 글을 거른다.

Usage: python3 jev_prefilter.py <candidates.json|-> [-o out.json] [--min-fit 1.0]

입력: 글 객체 배열(각각 "text"), 문자열 배열, 또는 {검색어: [글...]} (search.json 꼴).
출력 JSON: {"jev": "ok" | "skipped: <이유>", "kept": [...], "dropped": [...]}
  kept 는 끼어들 만함(fit, 0~3) 높은 순, 각 글에 "jev": {"spam", "fit"} 가 붙는다.
  dropped 는 spam >= 0.5 이거나 fit < --min-fit 인 글(이유 "jev_drop").
TYPESAFE_API_KEY 가 없거나 한 요청이라도 실패하면 아무것도 거르지 않고 입력 순서 그대로 kept 에 낸다(exit 0).
측정(2026-11-01, X 글 120개): 스팸 판정 Haiku와 119/120 일치, fit 과 Haiku 0~3 스피어만 0.76,
min-fit 1.0 이면 120개 중 75개를 남기고 Haiku 2점 이상 59개 중 3개만 빠진다.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = os.environ.get("TYPESAFE_BASE_URL", "https://api.typesafe.ai").rstrip("/")
MODEL = os.environ.get("TYPESAFE_DEFAULT_MODEL", "jev-latest")
SPAM_MAX = 0.5
QUESTIONS = {
    "spam": {"type": "noul", "instructions": "이 글은 종목 추천·리딩방·코인·대출·도박·부업 홍보나 DM·링크 유도 스팸이다"},
    "fit": {"type": "score",
            "instructions": "지원금·세금·재테크·AI 정보 계정이 짧은 정보성 답글이나 인용으로 자연스럽게 끼어들 수 있는 글인가",
            "criteria": ["끼어들면 안 됨(사적인 글·민감·스팸)", "애매함", "끼어들 만함", "딱 맞음(정보 질문·오해 바로잡기 기회)"]},
}


def ask(key, text, tries=4):
    body = json.dumps({"model": MODEL, "state": text[:1500], "questions": QUESTIONS}).encode()
    req = urllib.request.Request(BASE + "/v1/systemone", data=body, method="POST", headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "gshorts-prefilter/1"})
    for a in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                ans = json.load(r)["answers"]
            return {"spam": ans["spam"]["noul"], "fit": ans["fit"]["score"]}
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 529) and a < tries - 1:
                time.sleep(2 ** a)
                continue
            raise RuntimeError(f"HTTP {e.code}") from None
        except (urllib.error.URLError, TimeoutError):
            if a < tries - 1:
                time.sleep(2 ** a)
                continue
            raise


def load(src):
    if src == "-":
        data = json.load(sys.stdin)
    else:
        with open(src, encoding="utf-8") as f:
            data = json.load(f)
    if isinstance(data, dict):
        data = [p for arr in data.values() if isinstance(arr, list) for p in arr]
    return [p if isinstance(p, dict) else {"text": str(p)} for p in data]


def prefilter(items, min_fit):
    key = os.environ.get("TYPESAFE_API_KEY")
    if not key:
        return {"jev": "skipped: TYPESAFE_API_KEY 없음", "kept": items, "dropped": []}
    ex = ThreadPoolExecutor(6)
    try:
        scores = list(ex.map(lambda p: ask(key, p.get("text") or ""), items))
    except Exception as e:  # 네트워크·API 오류는 거르지 않고 기존 동작으로
        return {"jev": f"skipped: {type(e).__name__}: {e}"[:200], "kept": items, "dropped": []}
    finally:  # 한 요청이 실패하면 남은 요청은 기다리지 않는다
        ex.shutdown(wait=False, cancel_futures=True)
    kept, dropped = [], []
    for p, s in zip(items, scores):
        p = {**p, "jev": s}
        (dropped if s["spam"] >= SPAM_MAX or s["fit"] < min_fit else kept).append(p)
    kept.sort(key=lambda p: -p["jev"]["fit"])
    return {"jev": "ok", "kept": kept, "dropped": dropped}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("src")
    ap.add_argument("-o", "--out")
    ap.add_argument("--min-fit", type=float, default=1.0, help="fit(0~3) 이 이보다 낮으면 뺀다. 0 이면 스팸만 거른다")
    a = ap.parse_args()
    res = prefilter(load(a.src), a.min_fit)
    out = json.dumps(res, ensure_ascii=False, indent=1)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(out + "\n")
    else:
        print(out)
    print(f"jev-prefilter: {res['jev']} | 남김 {len(res['kept'])} · 뺌 {len(res['dropped'])}", file=sys.stderr)


if __name__ == "__main__":
    main()
