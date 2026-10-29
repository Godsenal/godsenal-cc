#!/usr/bin/env python3
"""@haedollar 영상 장(차트 모션) 렌더 + 검사.

Usage: python3 chart_motion.py <slide.json> -o <out.mp4> [--fonts DIR] [--work DIR] [--skip-render]

JSON 하나(데이터 + 패널 문구)로 templates/chart-motion 을 채워 HyperFrames 로 렌더하고,
check → render → 규격(ffprobe) → 시작·중간·끝 프레임 → 끝 화면 유지 → 끝 프레임 숫자 OCR 대조까지 돌린다.
하나라도 어긋나면 exit 1. 필요한 것: node(npx), ffmpeg/ffprobe, tesseract(eng).
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

HF = "hyperframes@0.8.210"  # 고정. 올릴 때는 다시 렌더해서 프레임을 비교한다
TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "chart-motion"
FONTS = ("Pretendard-ExtraBold.otf", "Pretendard-Bold.otf", "Pretendard-Medium.otf")
FONT_URL = "https://cdn.jsdelivr.net/npm/pretendard@1.3.9/dist/public/static/{}"
FPS, W, H = 30, 1080, 1440
HOLD_MIN = 4.0

# 레이아웃 좌표 (slide.html / bar.css / compare.css 와 같은 값)
PAD = 72
ROWS_TOP = PAD + 40 + 8 + 36 + 48          # .cap + .sub + .rows margin
ROW_H, BAR_H, LAB_W = 104, 56, 250
TRACK = W - PAD * 2 - LAB_W                # 686px
CARD_W, CARD_GAP, CARD_PAD = 444, 48, 40
CV_TOP = PAD + 40 + 8 + 36 + 64 + CARD_PAD + 40 + 32
CV_H = 112


def die(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def num(v, d):
    return f"{v:,.{d['decimals']}f}" if d["thousands"] else f"{v:.{d['decimals']}f}"


def fmt(v, d):
    return f"{d['prefix']}{num(v, d)}{d['suffix']}"


def text_w(s, px):
    # Pretendard ExtraBold 근사: 숫자·라틴 0.62em, 한글 1em
    return sum(px * (1.0 if ord(c) > 0x2E80 else 0.62) for c in s)


def motion_end(d):
    """마지막 움직임이 끝나는 시각 (bar.js / compare.js 의 시각과 같아야 한다)."""
    n = len(d["items"])
    if d["type"] == "bar":
        grow = 0.35 + (n - 1) * 0.12 + 1.4
        return max(grow, 3.7) if d["hi"] >= 0 else grow  # 빛 2.9+0.8
    grow = 0.3 + (n - 1) * 0.2 + 0.2 + 1.2
    return max(grow, 3.4) if d["hi"] >= 0 else grow


def load(path):
    d = json.loads(Path(path).read_text())
    t = d.get("type")
    if t not in ("bar", "compare"):
        die("type 은 bar 또는 compare")
    d.setdefault("caption", "")
    d.setdefault("subcaption", "")
    d.setdefault("prefix", "")
    d.setdefault("suffix", "")
    d.setdefault("decimals", 0)
    d.setdefault("thousands", True)
    d.setdefault("duration", 8)
    if not all(c.isascii() for c in d["prefix"] + d["suffix"]):
        die("prefix/suffix 는 $ % x 같은 영문 기호만 (OCR 대조용). 한글 단위는 subcaption 에 '단위: 점'처럼")
    items = d.get("items") or []
    for it in items:
        if not isinstance(it.get("label"), str) or not isinstance(it.get("value"), (int, float)) or it["value"] < 0:
            die(f"항목마다 label(문자열)과 0 이상 숫자 value 가 필요: {it}")
    if t == "bar" and not 2 <= len(items) <= 5:
        die("bar 는 항목 2~5개")
    if t == "compare" and len(items) != 2:
        die("compare 는 항목 2개")
    his = [i for i, it in enumerate(items) if it.get("highlight")]
    if len(his) > 1:
        die("highlight 는 한 항목만")
    d["hi"] = his[0] if his else -1
    if t == "bar":
        vmax = d.get("max") or die("bar 는 축 최대값 max 가 필요")
        if any(it["value"] > vmax for it in items):
            die("값이 max 보다 큼")
    for it in items:
        it["text"] = fmt(it["value"], d)
        if t == "bar":
            it["w"] = round(it["value"] / vmax * TRACK, 1)
            right = PAD + LAB_W + it["w"] + 16 + text_w(it["text"], 32)
            if right > W - 24:
                die(f"'{it['text']}' 가 화면 밖으로 나가요 — max 를 키워요")
        elif text_w(it["text"], 96) > CARD_W - CARD_PAD * 2:
            die(f"'{it['text']}' 가 칸보다 길어요 (96px 기준 364px)")
    p = d.get("panel") or die("panel 이 필요")
    if "num" not in p or not isinstance(p.get("title"), str) or not isinstance(p.get("body"), list):
        die("panel 에 num, title, body(줄 목록)가 필요")
    if len(p.get("title", "")) > 16:
        die(f"패널 제목 {len(p['title'])}자 (16자 이하)")
    if not 1 <= len(p.get("body", [])) <= 3:
        die("패널 본문은 1~3줄")
    if sum(line.count("**") for line in p["body"]) not in (0, 2) or any(line.count("**") % 2 for line in p["body"]):
        die("굵은 구절은 한 줄 안에 **…** 하나만")
    if not 3 <= d["duration"] <= 15:
        die("duration 은 3~15초")
    hold = d["duration"] - motion_end(d)
    if hold < HOLD_MIN:
        die(f"끝 화면 유지 {hold:.1f}초 (4초 이상) — duration 을 늘려요")
    return d


def esc(s):
    return html.escape(s).replace("\n", "<br>")


def media_html(d):
    head = f'<div class="cap">{esc(d["caption"])}</div><div class="sub">{esc(d["subcaption"])}</div>'
    rows = []
    for i, it in enumerate(d["items"]):
        hi = " hi" if i == d["hi"] else ""
        if d["type"] == "bar":
            shine = '<div class="barclip" data-layout-allow-overflow><div class="shine"></div></div>' if hi else ""
            rows.append(f'<div class="row{hi}"><div class="lab">{esc(it["label"])}</div><div class="track">'
                        f'<div class="bar"></div>{shine}<div class="val">0</div></div></div>')
        else:
            note = f'<div class="cn">{esc(it.get("note", ""))}</div>'
            rows.append(f'<div class="card{hi}"><div class="ci"><div class="cl">{esc(it["label"])}</div>'
                        f'<div class="cv">0</div>{note}</div></div>')
    wrap = "rows" if d["type"] == "bar" else "cards"
    foot = f'<div class="foot">{esc(d["footnote"])}</div>' if d.get("footnote") else ""
    return head + f'<div class="{wrap}">' + "".join(rows) + "</div>" + foot


def panel_html(p):
    body = "<br>".join(re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html.escape(line)) for line in p["body"])
    return f'<span class="num">{esc(str(p["num"]))}</span><div class="h">{esc(p["title"])}</div><div class="b">{body}</div>'


def fonts_dir(arg):
    for cand in [arg, os.environ.get("PRETENDARD_DIR"), str(Path.home() / "Library" / "Fonts")]:
        if cand and all((Path(cand) / f).is_file() for f in FONTS):
            return Path(cand)
    cache = Path.home() / ".cache" / "pretendard-1.3.9"
    cache.mkdir(parents=True, exist_ok=True)
    for f in FONTS:
        if not (cache / f).is_file():
            part = cache / (f + ".part")  # 끊긴 다운로드가 캐시에 남지 않게 다 받은 뒤 옮긴다
            urllib.request.urlretrieve(FONT_URL.format(f), part)
            part.rename(cache / f)
    return cache


def build(d, work, fonts):
    t = d["type"]
    data = {k: d[k] for k in ("type", "prefix", "suffix", "decimals", "thousands", "duration", "hi")}
    data["items"] = [{k: it[k] for k in ("value", "text", "w") if k in it} for it in d["items"]]
    js_data = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    sub = {
        "{{TYPE_STYLE}}": (TEMPLATE / f"{t}.css").read_text(),
        "{{TYPE_SCRIPT}}": (TEMPLATE / f"{t}.js").read_text(),
        "{{MEDIA}}": media_html(d),
        "{{PANEL}}": panel_html(d["panel"]),
        "{{DATA}}": js_data,
        "{{DURATION}}": str(d["duration"]),
    }
    slide = (TEMPLATE / "slide.html").read_text()
    for k, v in sub.items():
        slide = slide.replace(k, v)
    (work / "compositions").mkdir(parents=True, exist_ok=True)
    (work / "compositions" / "slide.html").write_text(slide)
    (work / "index.html").write_text((TEMPLATE / "index.html").read_text().replace("{{DURATION}}", str(d["duration"])))
    shutil.copy(TEMPLATE / "hyperframes.json", work / "hyperframes.json")
    (work / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    for f in FONTS:
        shutil.copy(fonts / f, work / "assets" / "fonts" / f)


def run(cmd, cwd=None, stdout_only=False):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return r.returncode, r.stdout if stdout_only else r.stdout + r.stderr


def frame(mp4, t, out, vf=None):
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(mp4)]
    if vf:
        cmd += ["-vf", vf]
    code, log = run(cmd + ["-frames:v", "1", str(out)])
    if code:
        die(f"프레임 추출 실패 {t}s: {log}")


def ssim(a, b):
    _, log = run(["ffmpeg", "-v", "info", "-i", str(a), "-i", str(b), "-lavfi", "ssim", "-f", "null", "-"])
    m = re.search(r"All:([0-9.]+)", log)
    return float(m.group(1)) if m else 0.0


def value_boxes(d):
    """끝 프레임에서 각 숫자가 놓이는 칸 (x, y, w, h)."""
    boxes = []
    for i, it in enumerate(d["items"]):
        if d["type"] == "bar":
            x = int(PAD + LAB_W + it["w"])
            y = ROWS_TOP + i * ROW_H + (ROW_H - BAR_H) // 2
            boxes.append((x, y - 6, min(W - x, int(text_w(it["text"], 32 * 1.12)) + 48), BAR_H + 12))
        else:
            x = PAD + i * (CARD_W + CARD_GAP) + CARD_PAD
            boxes.append((x - 8, CV_TOP - 8, CARD_W - CARD_PAD * 2 + 16, CV_H + 16))
    return boxes


def ocr(png):
    _, out = run(["tesseract", str(png), "-", "--psm", "7", "-l", "eng",
                  "-c", "tessedit_char_whitelist=0123456789.,$%+-"], stdout_only=True)
    return out.strip().splitlines()[0] if out.strip() else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--fonts")
    ap.add_argument("--work")
    ap.add_argument("--skip-render", action="store_true", help="이미 렌더된 --out 으로 검사만")
    a = ap.parse_args()

    d = load(a.json)
    out = Path(a.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    work = Path(a.work).resolve() if a.work else Path(tempfile.mkdtemp(prefix="chart-motion-"))
    results = []

    if not a.skip_render:
        build(d, work, fonts_dir(a.fonts))
        code, log = run(["npx", "--yes", HF, "check"], cwd=work)
        print("\n".join(l for l in log.splitlines() if not l.startswith("[hyperframes] check:"))[-3000:])
        if code:
            die("hyperframes check 실패")
        results.append("check ok")
        code, log = run(["npx", "--yes", HF, "render", "-o", str(out), "--fps", str(FPS), "-q", "delivery", "--quiet"], cwd=work)
        if code or not out.is_file():
            print(log[-3000:])
            die("render 실패")

    # 규격: 1080x1440 H.264 30fps, 무음, 3~15초
    _, probe = run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(out)])
    info = json.loads(probe)
    v = [s for s in info["streams"] if s["codec_type"] == "video"][0]
    audio = [s for s in info["streams"] if s["codec_type"] == "audio"]
    dur = float(info["format"]["duration"])
    spec = (v["codec_name"], v["width"], v["height"], v["r_frame_rate"], v.get("pix_fmt"))
    if spec != ("h264", W, H, f"{FPS}/1", "yuv420p") or audio or not 3 <= dur <= 15:
        die(f"규격 불일치: {spec} audio={len(audio)} dur={dur:.2f}")
    results.append(f"spec h264 {W}x{H} {FPS}fps yuv420p 무음 {dur:.1f}s")

    # 시작·중간·끝 프레임
    stem = out.with_suffix("")
    end_t = dur - 2 / FPS
    shots = {"start": 0.0, "mid": 1.0, "end": end_t}  # 1.0초: 막대·숫자가 차오르는 중
    for k, t in shots.items():
        frame(out, t, f"{stem}_{k}.png")
    hold_png = f"{stem}_hold.png"
    frame(out, dur - HOLD_MIN, hold_png)
    s_hold, s_move = ssim(hold_png, f"{stem}_end.png"), ssim(f"{stem}_start.png", f"{stem}_end.png")
    os.remove(hold_png)
    if s_hold < 0.995:
        die(f"끝 화면이 {HOLD_MIN}초 동안 멈춰 있지 않아요 (SSIM {s_hold:.4f})")
    if s_move > 0.98:
        die(f"시작과 끝이 거의 같아요, 모션이 없어요 (SSIM {s_move:.4f})")
    results.append(f"hold {HOLD_MIN:.0f}s SSIM {s_hold:.4f} | motion SSIM {s_move:.3f}")

    # 끝 프레임 숫자 = 입력값 (단위·쉼표를 뺀 숫자끼리 정확히 비교)
    def number(s):
        m = re.search(r"\d[\d,]*(?:\.\d+)?", s)
        return m.group(0).replace(",", "") if m else None
    got = []
    with tempfile.TemporaryDirectory() as td:
        for i, (x, y, w, h) in enumerate(value_boxes(d)):
            crop = Path(td) / f"v{i}.png"
            frame(f"{stem}_end.png", 0, crop, f"crop={w}:{h}:{x}:{y},scale=iw*3:-1,format=gray,lutyuv=y='if(gt(val,70),0,255)'")
            got.append(ocr(crop))
    want = [it["text"] for it in d["items"]]
    bad = [(it["text"], g) for it, g in zip(d["items"], got) if number(g) != num(it["value"], d).replace(",", "")]
    if bad:
        die(f"끝 프레임 숫자 불일치 (입력 → OCR): {bad}")
    results.append("end values " + " / ".join(f"{w_}={g}" for w_, g in zip(want, got)))

    print("chart-motion-check: PASS | " + " | ".join(results))
    print(f"frames: {stem}_start.png {stem}_mid.png {stem}_end.png")
    print(f"mp4: {out}")


if __name__ == "__main__":
    main()
