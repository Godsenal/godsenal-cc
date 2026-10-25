---
name: mockup
description: "Turns a design request into a quick, clickable HTML mockup instead of a description — one self-contained HTML file at real device size, built from the app's actual screens, colors, fonts, and copy, with several options compared on one page, PNG screenshots of each step, and a tailnet-only URL to open it on a phone. Saved outside the app repo, never committed. Use whenever someone asks for 시안, a mockup, a design option, 'how would this screen look', or to compare layouts before building; also for a revision round on an earlier mockup, or on /gbase:mockup."
allowed-tools: Bash Read Write Edit Glob Grep
---

# /gbase:mockup

A 시안 is something to look at and click, not a paragraph. Make the mockup first and let the feedback come back on it. Don't ask questions before the first round: pick the reading of the request that fits the app, say which you picked, and build it. The next round fixes what was wrong.

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드, 보고 줄의 접두사(`mockup:` 등). 목업 안의 UI 문구는 앱의 언어를 따른다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## 1. Read the app first

When the current directory is the app's repo, read before drawing: the screen being changed and its neighbors (layout, navigation, component structure), the theme or token file (colors, spacing, radius), the fonts the app bundles, `DESIGN.md` if there is one, and the real strings (i18n files, the screen's text). A mockup in the app's own look is judged on the idea; one in a generic look gets judged on the look. Use real copy, and mark copy you invented. With no app repo, take the look from the request and say so.

Read only. The app's code isn't changed here, and nothing from the mockup goes into the app repo.

## 2. Where it goes

```bash
root="${GBASE_MOCKUP_DIR:-$([ -d "$HOME/LTH" ] && echo "$HOME/LTH/design-mockups" || echo "$HOME/design-mockups")}"
common=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null) && app=$(basename "$(dirname "$common")")  # the main repo's name, also from a worktree
```

Outside a repo, take a short app name from the request. The round directory `dir` is `$root/<app>-<topic>-r<N>`: `<topic>` is a short kebab-case slug of what's being designed (`onboarding`, `paywall`), and `<N>` is one more than the highest existing `r<N>` for that app and topic, starting at 1. A revision is a new round: copy the previous round's directory and edit the copy, so earlier rounds stay openable for comparison.

Inside it: `index.html`, `shots/`, and a few lines of `notes.md` (the request, what each option tries, what was read from the app).

## 3. The HTML

- **One file, nothing from the network.** No CDN, web-font service, remote image, or analytics. It has to open from `file://`, from the tailnet server on a phone with no internet detour, and render the same in a headless screenshot. Inline the CSS and JS; the app's own fonts and image assets go in as base64 `data:` URLs (a font over ~2 MB may sit beside the file as a relative path).
- **`<meta charset="utf-8">` first.** Without it Korean comes out as mojibake in headless Chrome over `file://`.
- **Real device size.** Draw each screen in a frame at the target's CSS size (iPhone 393×852, Android 412×915, or the app's own breakpoints for web), safe areas included. On a viewport narrower than the frame, drop the frame and fill the screen, so it looks native on a phone.
- **It actually works.** Taps move between screens, toggles toggle, sheets open, inputs accept text. Every state is reachable by URL hash `#<option>-<step>` (`#a-1`, `#b-3`) and updates the hash when reached by clicking, so a screenshot and a feedback message can name the exact state.
- **Options side by side.** Two or three options go on one page, labeled A/B/C with one line each on what it tries and the tradeoff. On a phone, one option at a time with a small switcher. `?shot` in the URL hides labels, switcher, and frame so only the screen renders.
- **No copyrighted references.** Other apps' screenshots, stock photos, logos, and characters you don't own stay out, even as placeholders. Use the app's own assets, or CSS/SVG shapes and solid placeholder blocks.
- **No secrets or real user data.** API keys, `.env` values, tokens, real names, emails, or photos from the app's data never go in; the file is served to every device on the tailnet. Use made-up sample data.

## 4. Screenshots

One PNG per option and step, named `shots/<option>-<step>.png`. Use `chrome-headless-shell`. Regular Chrome's `--headless` clamps the window to at least 500 CSS px wide, so a 393 px phone layout renders at 500 and gets cropped:

```bash
find_shell() { find "$HOME/Library/Caches/ms-playwright" "$HOME/.cache/ms-playwright" -type f -name chrome-headless-shell 2>/dev/null | sort | tail -1; }
shell=$(find_shell); [ -n "$shell" ] || { npx -y playwright install chromium-headless-shell && shell=$(find_shell); }
"$shell" --hide-scrollbars --force-device-scale-factor=3 --window-size=393,852 --virtual-time-budget=1000 \
  --screenshot="$dir/shots/a-1.png" "file://$dir/index.html?shot#a-1"
```

Use the frame size you drew at for `--window-size`. Then look at the PNGs yourself — wrong fonts, overflowing text, a state that didn't render — and fix the HTML before reporting. A mockup that's broken in its own screenshot isn't ready to show.

## 5. Phone URL (tailnet only)

One static server per machine serves the whole `$root`, bound to the machine's tailnet IPv4 only, so devices on the tailnet can reach it and the LAN and internet can't:

```bash
ip=$(tailscale ip -4 2>/dev/null | head -1); port="${GBASE_MOCKUP_PORT:-8765}"
url="http://$ip:$port/$(basename "$dir")/index.html"
curl -sf -o /dev/null --max-time 2 "$url" || nohup python3 -c 'import functools,http.server as h,socketserver as s,sys; s.ThreadingTCPServer.allow_reuse_address=True; s.ThreadingTCPServer((sys.argv[1],int(sys.argv[2])),functools.partial(h.SimpleHTTPRequestHandler,directory=sys.argv[3])).serve_forever()' "$ip" "$port" "$root" >/dev/null 2>&1 &
```

Keep `GBASE_MOCKUP_PORT` as written; don't type a port in. Fetch `$url` with `curl` before reporting it: a server already on the port that serves a different root (another `GBASE_MOCKUP_DIR`) answers 404 and the new one can't bind, so take the next port. Not `python3 -m http.server --bind <tailnet ip>`: it reverse-resolves the address on startup and hangs about 35 seconds on a tailnet IP.

- **Never** `tailscale funnel`, a bind to `0.0.0.0` or the LAN address, or a tunnel service — the mockup would be on the internet. Don't edit `tailscale serve` either: its handlers belong to other apps on the machine.
- No `tailscale` or no tailnet IP → no server; the URL line says `none` and why.

## Report

A short summary first: the options and what each tries, what was read from the app, what was invented. Then these lines at column 0, so a caller can parse them:

```
mockup: <absolute path to index.html>
mockup url: <http URL> | none — <reason>
mockup shots: <absolute path to shots/>
```

Ask for feedback in terms of the hash states (`b-2 의 버튼 위치` …); the next request is the next round.
