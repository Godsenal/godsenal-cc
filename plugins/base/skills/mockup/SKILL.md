---
name: mockup
description: "Turns a design request into a quick, clickable HTML mockup instead of a description — one self-contained HTML file at real device size, built from the app's actual screens, colors, fonts, and copy, with several options compared on one page and PNG screenshots of each step, delivered where the user can open it. Saved outside the app repo, never committed. Run on /gbase:mockup <request> (시안, a mockup, comparing layouts, or a revision round) or the orchestrator's mockup slot; explicit only, so gbase:work and the other slots never pull it in."
allowed-tools: Bash Read Write Edit Glob Grep
disable-model-invocation: true
---

# /gbase:mockup

A 시안 is something to look at and click, not a paragraph. Make the mockup first and let the feedback come back on it. Don't ask questions before the first round: pick the reading of the request that fits the app, say which you picked, and build it. The next round fixes what was wrong.

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸, 집계/tally 라인까지 전부. 하위 에이전트를 띄울 때도, 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 고정 라벨과 상태 키워드, 보고 줄의 접두사(`mockup:` 등). 목업 안의 UI 문구는 앱의 언어를 따른다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## 1. Read the app first

When the current directory is the app's repo, read before drawing: the screen being changed and its neighbors (layout, navigation, component structure), the theme or token file (colors, spacing, radius), the fonts the app bundles, `DESIGN.md` if there is one, and the real strings (i18n files, the screen's text). A mockup in the app's own look is judged on the idea; one in a generic look gets judged on the look. Use real copy, and mark copy you invented. With no app repo, take the look from the request and say so.

Read [`gbase:design-taste`](../design-taste/SKILL.md) before drawing; its rules are what the user rejects a 시안 for.

Read only. The app's code isn't changed here, and nothing from the mockup goes into the app repo.

Before any HTML, write the plan into `notes.md`: the tokens you took (a few named colors, type roles, spacing, radius, with the file each came from) and a small ASCII wireframe per option. Two wireframes that look alike mean two options that are alike; change one before building it.

## 2. Where it goes

```bash
root="${GBASE_MOCKUP_DIR:-$HOME/design-mockups}"
common=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null) && app=$(basename "$(dirname "$common")")  # the main repo's name, also from a worktree
```

Outside a repo, take a short app name from the request. The round directory `dir` is `$root/<app>-<YYYYMMDD>-<topic>-r<N>` (`myapp-20261025-onboarding-r1`): the date is today's, `<topic>` is a short kebab-case slug of what's being designed, and `<N>` is one more than the highest `r<N>` for that app and topic on any date, starting at 1. A revision is a new round: copy the previous round's directory and edit the copy, so earlier rounds stay openable.

Inside it: `index.html`, `shots/`, and `notes.md` (the request, the plan above, what each option tries).

## 3. The HTML

- **One file, nothing from the network.** No CDN, web-font service, remote image, or analytics. It has to open from `file://` and render the same in a headless screenshot. Inline the CSS and JS; the app's own fonts and image assets go in as base64 `data:` URLs (a font over ~2 MB may sit beside the file as a relative path). No framework or build step: plain HTML, CSS, and a little JS are enough for a throwaway, and a component kit's default look would cover the app's.
- **`<meta charset="utf-8">` first.** Without it Korean comes out as mojibake in headless Chrome over `file://`.
- **Real device size.** Draw each screen in a frame at the target's CSS size (iPhone 393×852, Android 412×915, or the app's own breakpoints for web), safe areas included. On a viewport narrower than the frame, drop the frame and fill the screen, so it looks native on a phone.
- **It actually works.** Taps move between screens, toggles toggle, sheets open, inputs accept text. Every state is reachable by URL hash `#<option>-<step>` (`#a-1`, `#b-3`) and updates the hash when reached by clicking, so a screenshot and a feedback message can name the exact state. Where the request touches them, the empty, very long, and error states get their own steps; a layout that only works with average content isn't decided yet.
- **Options that differ on purpose.** Two or three options on one page, labeled A/B/C, each with one line on what it tries and the tradeoff. Make them differ in structure or emphasis (density, hierarchy, where the main action sits), not in color alone, and keep each one loud in one place and quiet elsewhere. When an existing screen is being changed, put the current screen first as `now`, so the options are judged against it. On a phone, one option at a time with a small switcher. `?shot` in the URL hides labels, switcher, and frame so only the screen renders.
- **Copy and small details.** An action keeps one name through the flow (a "보내기" button leads to a "보냈어요" toast, not "전송 완료"); an empty or error state says what to do next. Sample data looks real and adds up (totals match their rows, dates are plausible), never lorem ipsum or grey bars standing in for text. Touch targets at least 44 px, text contrast at least 4.5:1, `…` rather than `...`, tabular figures for numbers that line up.
- **No look of its own.** The app's look always wins. Only when there's none to follow, avoid the defaults that make a mockup read as generated: Inter on everything, a purple gradient, every block centered, one radius on everything, a card grid as the answer to every layout.
- **No copyrighted references.** Other apps' screenshots, stock photos, logos, and characters you don't own stay out, even as placeholders. Use the app's own assets, or CSS/SVG shapes and solid placeholder blocks.
- **No secrets or real user data.** API keys, `.env` values, tokens, real names, emails, or photos from the app's data never go in; the file may be opened on other devices. Use made-up sample data.

## 4. Screenshots

One PNG per option and step, named `shots/<option>-<step>.png`. Use `chrome-headless-shell`. Regular Chrome's `--headless` clamps the window to at least 500 CSS px wide, so a 393 px phone layout renders at 500 and gets cropped:

```bash
find_shell() { find "$HOME/Library/Caches/ms-playwright" "$HOME/.cache/ms-playwright" -type f -name chrome-headless-shell 2>/dev/null | sort | tail -1; }
shell=$(find_shell); [ -n "$shell" ] || { npx -y playwright install chromium-headless-shell && shell=$(find_shell); }
"$shell" --hide-scrollbars --force-device-scale-factor=3 --window-size=393,852 --virtual-time-budget=1000 \
  --screenshot="$dir/shots/a-1.png" "file://$dir/index.html?shot#a-1"
```

Use the frame size you drew at for `--window-size`. Then look at the PNGs yourself (wrong fonts, overflowing text, a state that didn't render) and fix the HTML; up to three look-and-fix rounds, then report what is still off instead of looping. A mockup that's broken in its own screenshot isn't ready to show, and the report claims only checks you actually ran.

## 5. Delivery

Give the user the mockup in a form they can open: the local path always, and when they'll look on a phone and the machine has Tailscale, a tailnet URL for the round directory. Use the one-liner below rather than `python3 -m http.server --bind`, which hangs about 35 seconds resolving a tailnet IP:

```bash
ip=$(tailscale ip -4 2>/dev/null | head -1); port="${GBASE_MOCKUP_PORT:-8765}"
[ -n "$ip" ] && nohup python3 -c 'import functools,http.server as h,socketserver as s,sys; s.ThreadingTCPServer((sys.argv[1],int(sys.argv[2])),functools.partial(h.SimpleHTTPRequestHandler,directory=sys.argv[3])).serve_forever()' "$ip" "$port" "$dir" >/dev/null 2>&1 &
```

Fetch the URL with `curl` before reporting it; if the port is taken, use the next one. **Never** `tailscale funnel`, a bind to `0.0.0.0` or the LAN address, or a tunnel service, which would put the mockup on the internet; and leave `tailscale serve` alone, since its handlers belong to other apps.

## Report

A short summary first: the options and what each tries, what was read from the app, what was invented. Then these lines at column 0, so a caller can parse them:

```
mockup: <absolute path to index.html>
mockup url: <http URL> | none — <reason>
mockup shots: <absolute path to shots/>
```

Ask for feedback in terms of the hash states (`b-2 의 버튼 위치` …); the next request is the next round.
