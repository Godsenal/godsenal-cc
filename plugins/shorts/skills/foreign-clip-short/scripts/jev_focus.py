#!/usr/bin/env python3
"""9:16 크롭 초점: plan.json 의 컷마다 주인공 얼굴을 Jev Box 로 찾아, 지금 크롭 창에서 얼굴이 잘리는 컷만 x 를 옮긴다.

Usage: python3 jev_focus.py <plan.json> [--sheet out.jpg]

컷마다 가운데 프레임을 뽑아 Jev(jev-preview)에 "얼굴 보이는 사람이 있나"(noul)와 "주인공 얼굴 위치"(box)를 묻는다.
사람이 있고(noul >= 0.5, box confidence >= 0.5) 얼굴이 지금 x(없으면 0.5)의 크롭 창을 벗어나면 x 를 얼굴 중심으로 옮긴다.
사람이 없거나 얼굴이 창 안이면 그대로 둔다. 바뀐 컷이 있을 때만 plan.json 을 고쳐 쓴다.
확인용 시트(기본 out/<폴더>/check/jev-focus.jpg): 빨강 = 얼굴, 회색 = 원래 창, 노랑 = 새 창. 렌더 전에 열어 본다.
TYPESAFE_API_KEY 가 없거나 Jev·ffmpeg 가 실패하면 plan 을 건드리지 않고 exit 0 (기존 가운데 크롭).
측정(2026-11-01, 원본 프레임 6장): 사람 있는 4장 얼굴 박스 모두 정확, 사람 없는 2장 noul 0.02·0.03.
"""
import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = os.environ.get("TYPESAFE_BASE_URL", "https://api.typesafe.ai").rstrip("/")
MODEL = "jev-preview"  # Box 는 preview 모델 + 이미지 헤더에서만 된다
BOX_RATIO, FILL_RATIO = 1080 / 930, 9 / 16  # 파이프라인 src/clipCommentary.ts cropFilter 와 같은 값
FRAME_W = 960  # Jev에 보내는 프레임 폭 = 시트 좌표계 폭
MIN_PERSON, MIN_BOX = 0.5, 0.5  # 2026-11-01 키친 나이트메어 20컷: 맞게 옮긴 컷 0.67~0.78, 뒤통수를 잡은 여러 명 샷 0.35
EDGE = 0.02  # 얼굴이 창 가장자리에 이만큼 붙어 있어도 잘린 것으로 본다(박스가 실행마다 0.01씩 흔들림)
QUESTIONS = {
    "has": {"type": "noul", "instructions": "Is there a person whose face is visible in `frame`?"},
    "face": {"type": "box", "instructions": "the face of the main person in `frame` (the one the shot is about, usually speaking or largest)"},
}


def window(x, r):
    """크롭 창 [left, right] (원본 폭 대비 비율). 파이프라인: crop x 오프셋 = (iw-ow)*x"""
    left = (1 - r) * min(1, max(0, x))
    return left, left + r


def refocus(x, r, faces):
    """faces: [(left, right, ...)] 얼굴 가로 범위. 하나라도 창 밖(가장자리 EDGE 포함)이면 얼굴 중심(중앙값)으로 옮긴 x, 아니면 None."""
    if not faces or r >= 1:
        return None
    lo, hi = window(x, r)
    if all(lo + EDGE <= f[0] and f[1] <= hi - EDGE for f in faces):
        return None
    cs = sorted((f[0] + f[1]) / 2 for f in faces)
    cx = cs[len(cs) // 2]
    new = round(min(1, max(0, (cx - r / 2) / (1 - r))), 2)
    return None if new == round(min(1, max(0, x)), 2) else new


def targets(plan):
    """x 를 가진 자리마다 (그 dict, 원본 구간들, crop, source)"""
    for seg in plan["segments"]:
        src = seg.get("source") or plan["source"]
        if seg.get("type") == "clip":
            for v in seg.get("video") or []:
                yield v, v["cuts"], v.get("crop"), src
            if not seg.get("video"):
                yield seg, [[seg["from"], seg["to"]]], seg.get("crop"), src
        elif isinstance(seg.get("over"), dict):
            o = seg["over"]
            yield o, o.get("cuts") or [[o["from"], o["from"] + 2]], o.get("crop"), src


def ratio(frame, crop, iw, ih):
    h = crop if isinstance(crop, (int, float)) and not isinstance(crop, bool) else 0.86 if crop else 1
    return h * ih * (BOX_RATIO if frame == "box" else FILL_RATIO) / iw


def ask(key, jpg, tries=4):
    body = json.dumps({"model": MODEL, "state": {"frame": "frame"}, "questions": QUESTIONS, "assets": {
        "frame": {"type": "image", "format": "jpeg", "data_base64": base64.b64encode(jpg.read_bytes()).decode()}}}).encode()
    req = urllib.request.Request(BASE + "/v1/systemone", data=body, method="POST", headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json",
        "TypeSafe-Danger-Zone-Images": "true", "User-Agent": "gshorts-focus/1"})
    for a in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                ans = json.load(r)["answers"]
            b, conf = ans["face"]["box"], ans["face"].get("confidence", 0)
            return (b["left"], b["right"], b["top"], b["bottom"]) if ans["has"]["noul"] >= MIN_PERSON and conf >= MIN_BOX else None
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


def ff(*args):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], check=True)


def run(plan_path, sheet):
    key = os.environ.get("TYPESAFE_API_KEY")
    if not key:
        return "skipped: TYPESAFE_API_KEY 없음", []
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    frame = plan.get("frame", "box")
    if frame == "band":
        return "skipped: frame band 는 x 를 안 씀", []
    base = plan_path.parent.parent  # 파이프라인처럼 source 는 work/ 위 폴더 기준
    tg = list(targets(plan))
    tmp = Path(tempfile.mkdtemp(prefix="jev-focus-"))
    try:
        srcs = [str((base / t[3]).resolve()) for t in tg]
        jobs = []  # (target index, 프레임 jpg)
        sizes = {}
        for i, ((_, cuts, _, _), s) in enumerate(zip(tg, srcs)):
            if s not in sizes:
                out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                      "-of", "csv=p=0", s], capture_output=True, text=True, check=True).stdout
                sizes[s] = tuple(map(int, out.strip().split(",")[:2]))
            for k, (a, b) in enumerate(cuts[:3]):
                jpg = tmp / f"{i:03d}_{k}.jpg"
                ff("-ss", f"{(a + b) / 2:.3f}", "-i", s, "-frames:v", "1", "-vf", f"scale={FRAME_W}:-2", "-q:v", "3", str(jpg))
                jobs.append((i, jpg))
        ex = ThreadPoolExecutor(6)
        try:
            faces = list(ex.map(lambda j: ask(key, j[1]), jobs))
        finally:  # 한 요청이 실패하면 남은 요청은 기다리지 않는다
            ex.shutdown(wait=False, cancel_futures=True)
        by_target = {}  # i -> [(jpg, face)]
        for (i, jpg), f in zip(jobs, faces):
            by_target.setdefault(i, []).append((jpg, f))
        changes, tiles = [], []
        for i, (d, cuts, crop, _) in enumerate(tg):
            iw, ih = sizes[srcs[i]]
            r = ratio(frame, crop, iw, ih)
            fs = [f for _, f in by_target[i] if f]
            old = d.get("x", 0.5)
            new = refocus(old, r, fs)
            if new is not None:
                d["x"] = new
                changes.append(f"#{i} {cuts[0][0]:.1f}s x {old} → {new}")
            # 시트: 이 자리의 첫 프레임에 그 프레임의 얼굴·원래 창·새 창
            jpg, face = by_target[i][0]
            W, H = FRAME_W, round(FRAME_W * ih / iw / 2) * 2
            draw = []
            if face:
                left, right, top, bottom = face
                draw.append(f"drawbox=x={left * W:.0f}:y={top * H:.0f}:w={(right - left) * W:.0f}:h={(bottom - top) * H:.0f}:color=red:t=4")
            draw.append(f"drawbox=x={window(old, r)[0] * W:.0f}:y=0:w={r * W:.0f}:h={H}:color=gray:t=3")
            if new is not None:
                draw.append(f"drawbox=x={window(new, r)[0] * W:.0f}:y=0:w={r * W:.0f}:h={H}:color=yellow:t=5")
            tile = tmp / f"tile_{len(tiles):03d}.jpg"
            ff("-i", str(jpg), "-vf", ",".join(draw + ["scale=480:-2"]), str(tile))
            tiles.append(tile)
        if tiles:
            sheet.parent.mkdir(parents=True, exist_ok=True)
            cols = min(4, len(tiles))
            ff("-i", str(tmp / "tile_%03d.jpg"), "-vf", f"tile={cols}x{-(-len(tiles) // cols)}:padding=4", "-frames:v", "1", str(sheet))
        if changes:
            plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return f"ok: 자리 {len(tg)}개 중 {len(changes)}개 x 변경, 시트 {sheet}", changes
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("--sheet")
    a = ap.parse_args()
    plan = Path(a.plan).resolve()
    sheet = Path(a.sheet).resolve() if a.sheet else plan.parent.parent / "check" / "jev-focus.jpg"
    try:
        status, changes = run(plan, sheet)
    except Exception as e:  # Jev·ffmpeg 실패는 plan 을 건드리지 않고 기존 가운데 크롭으로
        status, changes = f"skipped: {type(e).__name__}: {e}"[:200], []
    for c in changes:
        print(c)
    print(f"jev-focus: {status}", file=sys.stderr)


if __name__ == "__main__":
    main()
