---
name: top3-compilation-short
description: >-
  Starter for a faceless Korean TOP3 compilation short — three ranked moments from official foreign show
  clips (e.g. the three biggest investor fights) cut into one 45–55s Shorts/Reels/TikTok video. Most of the
  format is unconfirmed by the user and marked TODO; it settles the open parts by sample comparison. Use when
  asked for a TOP3 / 모음 / 랭킹 / compilation short, or when building stock in a new format.
---

# top3-compilation-short (starter)

The user asked for stock in varied formats, "TOP3 모음 등" (2026-10-26). That is the only user-confirmed input for this format; everything marked TODO below was chosen by an agent and has **not** been approved. Don't present it as the agreed spec — settle each TODO by shorts-common's sample comparison and write the answer here with the date.

All of [shorts-common](../shorts-common/SKILL.md) applies. Clip sourcing, subtitles, and framing D follow [foreign-clip-short](../foreign-clip-short/SKILL.md).

## 출력 언어

사용자에게 보이는 텍스트(진행 보고, 샘플 비교 설명, 리포트)와 영상 산출물(자막, 해설, 제목, 캡션)은 **한국어**로 쓴다. 따옴표 안 한국어는 사용자 피드백 인용이므로 그대로 둔다. 코드·경로·명령어는 대상 레포의 관례를 따른다. 사용자가 다른 언어로 요청하면 그 언어를 따른다.

Narration matters more here: YouTube names low-narrative compilations as reused content ([trends](../shorts-common/references/trends-2026-10.md#reused--clipped-content--matters-for-foreign-clip-formats)) — never ship three clips stitched with rank cards alone.

## Draft structure (TODO — unconfirmed)

What the first attempt (`out/2026-10-26_top3_fights`, status needs-review, no user verdict) used:

- Theme across all three entries (e.g. investors fighting), title like "투자자끼리 싸움 났다 / 역대급 피치 TOP3" in framing D.
- Order 3위 → 2위 → 1위, each entry a hard-cut segment from a different source; a rank card (`rank {n, label, seconds}` in `plan.json`, 1.6s in the draft) before each.
- 3 narration lines with ding/hit SFX, total 62.5s.

TODO, to settle with the user:
- Per-entry length split, and whether rank cards stay or become a title overlay (rank cards eat 4–5s of a 55s budget).
- Ranking order (3→1 vs. 1 first as the hook) — the strongest moment must still land in the first seconds, as in [foreign-clip-short](../foreign-clip-short/SKILL.md#structure).
- Whether entries may repeat clips already posted as single shorts.
- Explanation-comment shape for three subjects.

Redesign B (foreign-clip-short) applies here too: silence cuts, 1.08×, B subtitles and tags. Write the settled format into the pipeline's `docs/formats/top3-compilation.md` too.
