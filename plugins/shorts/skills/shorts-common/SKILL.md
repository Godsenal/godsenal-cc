---
name: shorts-common
description: >-
  Holds the user-confirmed rules that apply to every faceless Korean short-form video (YouTube Shorts,
  Instagram Reels, TikTok) — length, pacing, BGM/SFX mix, narration voice and tone, captions,
  explanation comment, AI label, sample comparison before deciding, delivery and posting gates — and the feedback-intake rule
  that reports every new piece of user feedback the same turn as a `교훈:` line for the matching gshorts skill. Use before
  planning, editing, or delivering any short, whenever the user gives feedback on a short ("속도감이 없다",
  "BGM이 약하다"), or when another gshorts format skill points here.
---

# shorts-common — rules for every short

Format skills (`foreign-clip-short`, `top3-compilation-short`) hold only what differs per format and point here for the rest. Rules for every piece of content, video or not (writing from opened references, recording mistakes the same turn), live in [content-common](../content-common/SKILL.md) and apply here too. When a format skill and this file disagree, the newer dated feedback wins.

## 출력 언어

사용자에게 보이는 텍스트(진행 보고, 샘플 비교 설명, 리포트)는 **한국어**로 쓴다. 영상 산출물 — 해설 문구, 자막, 제목, 캡션, 설명 댓글 — 도 한국어다. 아래 따옴표 안 한국어는 사용자 피드백 원문 인용이므로 번역하지 않는다. 코드·경로·명령어·환경변수 이름과 커밋 메시지는 대상 레포의 관례를 따른다. 사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Pipeline

The render pipeline is a separate repo (`tiktok-automation`); run its commands there and never copy its code into this plugin. On the reference machine it is `$HOME/LTH/tiktok-automation`; if that path doesn't exist, ask the user for its location once.

- Render: `npm run clip -- out/<date>_<slug>/work/plan.json` (`src/clipPace.ts`, default `PACE_B`); format rules in `docs/CLIP.md`, `docs/formats/*.md`. Flicker check: `npm run flicker -- video.mp4` (also run by the render; result in `metadata.json` `flicker`).
- Work dir `out/<date>_<slug>/` (`work/plan.json`, `video.mp4`, `subtitles.srt`, `metadata.json`, `check/`). Delivery copy in `$HOME/tiktok-share/<date>/<nn>_<slug>/`: `video.mp4`, `caption.txt`, `cover.jpg`, `subtitles.srt`, `check/`, `REPORT.md`.
- Narration: `npm run make` (TTS defaults to fishaudio); a standalone narration is `npm run narrate -- --text-file a.txt --out a.mp3`, with word timings in `a.mp3.words.json`.
- Keys come from the environment or key file by name only — `FISH_API_KEY` or `$HOME/.config/fish-audio/api_key` (TTS; `TYPECAST_API_KEY` only for the fallback in Voice), `FAL_KEY` (BGM); optional knobs are in the pipeline's `.env.example`. Never read, print, or copy key values, the key file, or the shell file that sets them.
- Cost: every paid call is logged in `cost-ledger.jsonl`; check the monthly budget (`MONTHLY_BUDGET_KRW`) before a batch. Reuse cached TTS/BGM when the line or prompt is unchanged.

## Rules for every video (user-confirmed)

Quotes are the user's words with the date they were said. Undated items are from the 2026-10-25 format agreement.

- **Length** — clips 45–55s: 2026-10-26, the user picked redesign B ("61초 하한은 없앤다"); the 61s Creator Rewards floor is gone. Well-performing foreign-clip shorts run 36–56s. Narration shorts (the 12:00 slot) run 25–35s, fast-paced (2026-10-27; 2026-10-29 "10~30초는 릴스에만, 쇼츠는 25~35초 유지"); 1-minute-plus versions are on hold until the follower count grows (2026-10-28). The cover is a frame at 0.5–1s that shows the headline, so the headline is on screen from the start; start the headline and the caption's hook line from [hook-templates](../hook-templates/SKILL.md). Reach the length by dropping weak lines (side remarks, a lone "와", self-promotion), never by padding. Hard cuts only — no slide/wipe transitions. **No black frame at the end**; the last frame is real footage.
- **Explanatory video pace and opening** — 2026-10-28 "좀더 빠른게나으려나? 레퍼런스 릴스 속도감봐봐": narration runs at about 7.8 syllables per second (measured on the reference reels; count syllables over narration seconds), with fast scene changes. 2026-10-29 "ㅇㅇ": the first screen is the result itself (a number, table, or chart) under a two-line question subtitle, and the result is on screen within 3 seconds. Explanatory reels run 10–30s; the 12:00 narration shorts keep the 25–35s in Length.
- **Pace** — 2026-10-26 "속도감이 없다", settled by redesign B: remove **every silence over 0.15s between lines**, leaving ~0.06s before and after so line endings aren't clipped. Find the silences on the actual waveform (demucs vocal stem), not on Whisper word timestamps alone: Whisper stretches words over pauses and missed every 0.2s pause in a clip. Use word timestamps to check that no word was cut. Then play everything at 1.08× with pitch kept. Pipeline: `scripts/clip/make_b.py` (prints "소리 걸친 컷 경계" and "잘린 단어", both must be 0) and `scripts/clip/listen_check.py` (re-transcribes the render).
- **No flicker at cuts** — 2026-10-26 "장면 전환 때 화면이 깜빡이는 현상": the cause was one to three frames of a different camera angle or crop at a cut. Clip pieces were cut one frame late (the first frame after the seek wasn't at PTS 0), and plan boundaries sat 1–3 frames off the source's own camera cuts. The pipeline now cuts from PTS 0, fills edge frames that straddle a source cut (`fixEdges`), merges pieces under 4 frames, and aligns color flashes to cut frames. **Before showing a video, `metadata.json` `flicker.issues` must be empty and `blackframe` empty**; any 1–3 frame shot or black frame blocks delivery.
- **BGM** — 2026-10-26 "BGM이 약하다", settled by redesign B: measured against the dialogue track, -9 LU under speech, -5 in gaps, -6 under narration (2 dB below the B draft so speech isn't buried); master -14 LUFS (`PACE_B.bgmDb`).
- **SFX**: subtle shorts-style — whoosh+hit at the hook, ding at a key reveal, a tension hit before the decision. Synthesized by the pipeline (`src/sound.ts`), free.
- **Narration — never zero lines.** 3–4 short Korean hearsay bridge lines (1–3s each) in the shorts storytelling tone: "~했다는데", "침묵이 이어지는데", "잠깐 고민하더니". Not a news-style who/what/result summary. Write numbers in Korean words; commas and ellipses for natural line endings. Narration is also what keeps clip-based shorts out of "reused content" ([trends](references/trends-2026-10.md#reused--clipped-content--matters-for-foreign-clip-formats)).
- **Voice** — 2026-10-30 user decision: all narration, shorts (머니알림) and @haedollar reels alike, is fish.audio's official voice 지훈 Jihoon (`1faa840246094164bf4b0b0b94ae1675`, model `s2.1-pro`) at `prosody.speed` 1.4, with no ffmpeg `atempo`; silences over 0.15s are cut. Measured 8.03 syllables/s (Typecast 대진 was 8.16). Never a community-shared clone, another person's or a celebrity's voice, or a clone of Typecast output (Fish terms risk), and never an `s1` model (retired 2026-12-31). Typecast is cancelled: `--tts typecast` works as a fallback only until 2026-11-23; after that the fallback is MiniMax. A new voice only after a side-by-side sample comparison.
- **Caption — lean** (2026-10-28): only a hook or summary line, the **series line**, and 5 hashtags — no source credit, clips included (2026-10-29, [content-common](../content-common/SKILL.md)'s no-sources rule). Nothing else — no AI notice, no "광고·협찬 없음", no `※` memo lines, no comment bait ("너라면…? 댓글로…", "자세한 조건은 댓글"). YouTube descriptions follow the same rule. Since 2026-10-28 production (subscriber-conversion plan, pipeline `docs/SERIES.md` "시리즈 안내 줄"), line 2 of a series clip is `<쇼 이름> #<다음 회차>는 <다음 예약 날짜 시각>, 지난 회차는 프로필에서`, generated by `node scripts/series-cta.mjs <stock folder>` from `topics/clips/queue.json` slots and the `SCHEDULE-RESULT.md` booking records; when the next episode's slot is unknown it says `다음 회차도 곧 올라와요` with no date. Non-series videos (narration, TOP3) use a general line such as `이런 돈 정보 매일 올려요`. **Never** conditional or reward-style follow bait ("팔로우하면 2편 공개", "구독해야 결과 공개") — TikTok's integrity guidelines drop follow-manipulating content from For You. Captions and comments of videos already scheduled or posted are never rewritten.
- **End card**: series clips (from 2026-10-28 production) end with a 1.5s yellow next-episode line in the headline spot, from the same schedule as the caption series line (pipeline `docs/SERIES.md` "엔드카드", `plan.json` `stock`). Narration videos and TOP3 get none.
- **AI-generated content label — off on TikTok and YouTube, on for narrated Reels** — 2026-10-28 user decision: on TikTok and YouTube the AI-generated content label stays off for every video, narration videos with AI images included. The label is required for realistic AI content ([trends](references/trends-2026-10.md#ai-labeling)), so the one exception is a future short drama with photoreal AI people (storyShort): label those. **Instagram Reels with TTS narration are the other way round**: turn the AI label on when uploading (2026-10-30 user decision).
- **Explanation comment, not pinned** — 2026-10-27 "고정 없이 댓글만 계속": post it under each video and don't pin it (TikTok web can't pin; pinning on YouTube needs advanced verification). TikTok can filter a comment silently, so check after posting that it's visible; if it's gone, post it once more, and if that's filtered too, stop and note it in REPORT.md. Content: like the reference short https://youtube.com/shorts/J17s13-O3hE — who the person / what the product is, plus what happened after the broadcast. For series clips the comment is **behind-the-story only** (user, 2026-10-27: "댓글은 비하인드 스토리"): what happened after the broadcast (closure, rename, lawsuit, local reports, the episode's own epilogue), not a recap of the video. Only facts you confirmed with a source; the source goes in REPORT.md, never in the comment, and never guess a 근황. For a series clip the last line (after the viewer question) repeats the caption's series line; no URLs (Shorts comment links are not clickable).
- **Five posts a day, foreign clips first** — 2026-10-26 "해외 클립 영상이 가장 인기 있으니 주력으로 유지, 업로드는 하루 3편보다 더 늘려도 됨": slots 07:30, 12:00, 18:00, 21:00, 23:00 KST, same slots on TikTok and YouTube Shorts. 12:00 is the narration video (next rule); the other four are foreign-show clips from pre-rendered stock, one fixed show per slot (pipeline `docs/SERIES.md`, `node scripts/day-slots.mjs <date> --clip`). A slot someone already scheduled is listed in `topics/overrides/<date>.json` `skipSlots` and never touched.
- **12:00 is narration only, one narration video a day** — 2026-10-28 user decision: start at one narration video a day, in 12:00, and go to two only once fact-checking keeps up (the second slot's time is the user's call then). No clip video, TOP3 included, takes or overrides 12:00 — not in `topics/clips/queue.json`, not from `day-slots.mjs`, not in an overrides file. This is for scheduling from now on; videos already scheduled stay as they are.
- **Narration stays at today's amount** — 2026-10-26 "해설 양은 지금 그대로(늘리지 말 것)": 3–4 lines, about 70 characters in total. More stock or a new show is not a reason to add lines.
- **Fixed series** — 2026-10-26 "인기 많은 쇼는 '고정 시리즈'로 운영": pick shows by measured Korean view counts (record the numbers and sources), give each a slot, and start the caption's first line (and the YouTube title) with `[<시리즈명> #<회차>]`, numbered per show in posting order. Nothing about the series goes on screen unless the user picks it from samples.
- **Stock**: build inventory ahead in varied formats (TOP3 compilations etc.), not only the current one. A stock folder per slot holds `video.mp4`, `caption.txt`, `COMMENT.md` (explanation comment + sources), `FACTS.md` (every claim with its source time or URL).

## Sample comparison before deciding

Any screen or format option (framing, title style, BGM level, pace, voice) is decided by the user from **2–3 samples side by side**, never by description. Render short excerpts of the same segment with only the option changed, put them in one folder with a one-line label each, and say what differs. Once the user picks, report the choice as a `교훈:` line for the matching skill (intake below) and set the pipeline default.

## Feedback intake — same turn, every time

Every new piece of feedback about a short becomes a dated, quoted `교훈:` line for the matching skill before the work continues — every video → this file's "Rules for every video", one format → `foreign-clip-short` or `top3-compilation-short`. The full procedure (classification, the line format, why a content run never edits the harness source, who ships it) is [content-common's intake](../content-common/SKILL.md#feedback-intake--same-turn-every-time).

## Checks before showing the user

2026-10-26 "품질 최우선 … 통과 못한 영상은 재고에 넣지 않는다": a video that fails any gate below is fixed or dropped, never stocked. Compare each new show against at least three high-view Korean shorts of the same show (hook, cuts per minute, 0.15s+ gaps, BGM under speech, subtitle look) and write the table down.


- Duration 45–55s for clips, 25–35s for narration shorts, 10–30s for explanatory reels (`ffprobe`); the cover frame (0.5–1s) shows the headline; `metadata.json` `flicker` has no issues and no black frames; last frame is footage.
- Frames grabbed into `check/` at several timestamps (title, crop, subtitles, `last.jpg`) and looked at.
- No line ending cut off and no leftover gap: make_b's "소리 걸친 컷 경계" and "잘린 단어" are 0, and the render's 0.15s+ gaps are listed. The automatic re-transcription share (`listen_check.py`) drops to 0.7–0.8 on crying or music-heavy scenes even when every word is there; in that case re-transcribe the vocal stem in 4-second chunks and confirm each line is heard. The make_b vocal cache must be keyed by the clip ranges: a stale cache after editing clip ranges shifted every later clip and cut real words (fixed 2026-10-26).
- Loudness near -14 LUFS. You can't hear the mix — say "귀로 듣지 않음" in REPORT.md rather than claiming the audio is fine.
- Narration timestamps land where intended; numbers and names match the source.
- REPORT.md: source URL, title, length/resolution/LUFS/blackdetect/last frame, narration lines with timestamps and SFX, how subtitles were verified, cost, and a "확인 못 한 것" list.

## Delivery and posting

- Send the video, caption, narration lines with timestamps, and the explanation-comment draft.
- **Never schedule or post a video without the user's explicit OK for that video.** After the OK: the pipeline's `scripts/prepare-upload.mjs` (see its `docs/UPLOAD.md`) fills TikTok Studio and stops before the submit button by design — don't change that stop. Before scheduling, check the filled form: the content reuse toggle (on by default) is turned **off**, and the AI-generated content toggle is off per the rule above. The script never submits: after the OK you click schedule yourself, exactly once, then confirm the scheduled list with a screenshot. Under `AGENT_HEADLESS=1` nothing is scheduled; report it as pending the user's OK.
