---
name: shorts-common
description: >-
  Holds the user-confirmed rules that apply to every faceless Korean short-form video (YouTube Shorts,
  Instagram Reels, TikTok) — length, pacing, BGM/SFX mix, narration voice and tone, captions, pinned
  comment, sample comparison before deciding, delivery and posting gates — and the feedback-intake rule
  that writes every new piece of user feedback into the matching gshorts skill the same turn. Use before
  planning, editing, or delivering any short, whenever the user gives feedback on a short ("속도감이 없다",
  "BGM이 약하다"), or when another gshorts format skill points here.
---

# shorts-common — rules for every short

Format skills (`foreign-clip-short`, `top3-compilation-short`) hold only what differs per format and point here for the rest. When a format skill and this file disagree, the newer dated feedback wins.

## 출력 언어

사용자에게 보이는 텍스트(진행 보고, 샘플 비교 설명, 리포트)는 **한국어**로 쓴다. 영상 산출물 — 해설 문구, 자막, 제목, 캡션, 고정 댓글 — 도 한국어다. 아래 따옴표 안 한국어는 사용자 피드백 원문 인용이므로 번역하지 않는다. 코드·경로·명령어·환경변수 이름과 커밋 메시지는 대상 레포의 관례를 따른다. 사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Pipeline

The render pipeline is a separate repo (`tiktok-automation`); run its commands there and never copy its code into this plugin. On the reference machine it is `$HOME/LTH/tiktok-automation`; if that path doesn't exist, ask the user for its location once.

- Render: `npm run clip -- out/<date>_<slug>/work/plan.json` (`src/clipCommentary.ts`); format rules in `docs/CLIP.md`, `docs/SHARK_TANK.md`.
- Work dir `out/<date>_<slug>/` (`work/plan.json`, `video.mp4`, `subtitles.srt`, `metadata.json`, `check/`). Delivery copy in `$HOME/tiktok-share/<date>/<nn>_<slug>/`: `video.mp4`, `caption.txt`, `cover.jpg`, `subtitles.srt`, `check/`, `REPORT.md`.
- Keys come from the environment by name only — `TYPECAST_API_KEY` (TTS), `FAL_KEY` (BGM); optional knobs are in the pipeline's `.env.example`. Never read, print, or copy key values or the shell file that sets them.
- Cost: every paid call is logged in `cost-ledger.jsonl`; check the monthly budget (`MONTHLY_BUDGET_KRW`) before a batch. Reuse cached TTS/BGM when the line or prompt is unchanged.

## Rules for every video (user-confirmed)

Quotes are the user's words with the date they were said. Undated items are from the 2026-10-25 format agreement.

- **Length 61–65s** (TikTok Creator Rewards needs over 1 min). Hard cuts only — no slide/wipe transitions. **No black frame at the end**; the last frame is real footage.
- **Pace** — 2026-10-26 "속도감이 없다": cut dragging stretches and the silence between lines. Remove dead air rather than adding cuts for their own sake ([trends](references/trends-2026-10.md#cut-frequency--pacing)).
- **BGM** — 2026-10-26 "BGM이 약하다": clearly audible and matched to the scene. The pipeline default (`BGM_DB` in `src/clipCommentary.ts`: about -4 dB in gaps, -13 dB under speech, +3 dB build, final -14 LUFS) is the level the user called weak, so mix BGM louder than that. TODO (open): no new level is agreed yet. The louder pace-test variants (`scripts/pace-test/make_plans.py`, A/B/C) haven't been shown to the user. Settle it by sample comparison (below), then write the chosen levels here and into the pipeline default.
- **SFX**: subtle shorts-style — whoosh+hit at the hook, ding at a key reveal, a tension hit before the decision. Synthesized by the pipeline (`src/sound.ts`), free.
- **Narration — never zero lines.** 3–4 short Korean hearsay bridge lines (1–3s each) in the shorts storytelling tone: "~했다는데", "침묵이 이어지는데", "잠깐 고민하더니". Not a news-style who/what/result summary. Write numbers in Korean words; commas and ellipses for natural line endings. Narration is also what keeps clip-based shorts out of "reused content" ([trends](references/trends-2026-10.md#reused--clipped-content--matters-for-foreign-clip-formats)).
- **Voice**: Typecast voice 대진 with toneup 1.3 and tempo 1.1; the pipeline then speeds it up with ffmpeg `atempo=1.3`, pitch kept (`CLIP_VOICE_SPEEDUP`). Chosen from 8 samples; never 현준. A new voice only after a side-by-side sample comparison.
- **Caption**: a curiosity hook line + a comment/save/tag CTA line + 5 hashtags. No AI-disclosure line, no summary. The TikTok AI-generated-content toggle stays ON.
- **Pinned comment**: like the reference short https://youtube.com/shorts/J17s13-O3hE — who the person / what the product is, plus what happened after the broadcast. Only facts you confirmed with a source; cite the source in REPORT.md, never guess a 근황.
- **Stock**: build inventory ahead in varied formats (TOP3 compilations etc.), not only the current one.

## Sample comparison before deciding

Any screen or format option (framing, title style, BGM level, pace, voice) is decided by the user from **2–3 samples side by side**, never by description. Render short excerpts of the same segment with only the option changed, put them in one folder with a one-line label each, and say what differs. Once the user picks, write the choice into the matching skill (intake below) and the pipeline default.

## Feedback intake — same turn, every time

Every new piece of user feedback about a short is written into a skill **before** continuing the work:

1. Classify it: applies to every video → this file's "Rules for every video"; specific to one format → that format skill; a new format → a new `skills/<format>-short/SKILL.md` that points here.
2. Write it as a rule with the date and the user's own words in quotes (`2026-10-26 "BGM이 약하다": …`). If it contradicts an existing rule, rewrite that rule instead of adding a second one, and give it the new date.
3. Then update the pipeline default it implies, if any.

Edit the gshorts source in the godsenal-cc checkout (`plugins/shorts/skills/…`; on the reference machine `$HOME/LTH/godsenal-cc`), not the installed plugin cache — the cache is overwritten on update. Bump the gshorts version in both `plugins/shorts/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` (patch for a rule, minor for a new format skill); installed copies only change once it ships.

## Checks before showing the user

- Duration 61–65s (`ffprobe`); `blackdetect` finds no black frame; last frame is footage.
- Frames grabbed into `check/` at several timestamps (title, crop, subtitles, `last.jpg`) and looked at.
- Loudness near -14 LUFS. You can't hear the mix — say "귀로 듣지 않음" in REPORT.md rather than claiming the audio is fine.
- Narration timestamps land where intended; numbers and names match the source.
- REPORT.md: source URL, title, length/resolution/LUFS/blackdetect/last frame, narration lines with timestamps and SFX, how subtitles were verified, cost, and a "확인 못 한 것" list.

## Delivery and posting

- Send the video, caption, narration lines with timestamps, and the pinned-comment draft.
- **Never schedule or post a video without the user's explicit OK for that video.** After the OK: the pipeline's `scripts/prepare-upload.mjs` (see its `docs/UPLOAD.md`) fills TikTok Studio and stops before the submit button by design — don't change that stop. The script never submits: after the OK you click schedule yourself, exactly once, then confirm the scheduled list with a screenshot. Under `AGENT_HEADLESS=1` nothing is scheduled; report it as pending the user's OK.
