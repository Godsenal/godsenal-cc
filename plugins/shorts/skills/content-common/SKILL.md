---
name: content-common
description: >-
  Holds the user-confirmed rules for every piece of content the gshorts harness makes — shorts, Instagram
  card news, and any account name, bio, caption, script, or post copy — chiefly that it is written from
  high-performing references actually opened on the target platform (X, Instagram, YouTube, Threads), that
  public copy reads as one real person's own first-hand writing with no source credits, and that every mistake
  or lesson is reported the same turn as a `교훈:` line that a reviewed gbase:work run writes into this plugin,
  so other bots don't repeat it. Use before naming an
  account, writing a bio, caption, card, script, or text post (Threads, X), when the user gives feedback that
  applies across formats, or when a gshorts skill points here.
---

# content-common — rules for every piece of content

Applies to everything gshorts makes. Video-wide rules live in [shorts-common](../shorts-common/SKILL.md), Instagram card news in [instagram-card-news](../instagram-card-news/SKILL.md), Naver blog strategy in [naver-blog](../naver-blog/SKILL.md), Threads posts in [threads-voice](../threads-voice/SKILL.md), X posts in [x-voice](../x-voice/SKILL.md); all point here. When they disagree, the newer dated feedback wins.

## 출력 언어

사용자에게 보이는 텍스트(진행 보고, 샘플 비교 설명, 리포트)와 콘텐츠 산출물(이름, 소개글, 캡션, 카드 문구, 대본)은 **한국어**로 쓴다. 따옴표 안 한국어는 사용자 피드백 원문 인용이므로 번역하지 않는다. 코드·경로·명령어·환경변수 이름과 커밋 메시지는 대상 레포의 관례를 따른다. 사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Rules for every piece of content (user-confirmed)

Quotes are the user's words with the date they were said.

- **Written from real references** — 2026-10-28 "항상 이런 컨텐츠 관련은 x나 인스타 유튜브등 적절한 플랫폼에 있는 잘나가는 레퍼런스를 기반으로": applies to every content judgment and every line of copy — names, bios, captions, card news, scripts. First open references that actually perform well on that platform (X, Instagram, YouTube, whichever the content is for), collect their original text, then write from it. Note the references (URL + the quoted original) in the work folder's report. If the references can't be opened (timeout, login wall), stop and say so; don't write from memory.
- **Made-up numbers and scope are assumptions, reported first** — 2026-10-28 "왜 주 4회임?" (a "월·수·금·일 아침 7시 반" schedule an agent had planned on its own went straight into the bio), 2026-10-28 "해외 AI회사라고 할 필요가 있나 … 왤케좁혀?": a number, schedule, or scope (N posts a week, a time, a narrowed audience) that comes from neither the references nor a user decision goes at the top of the report as a `가정:` line, and stays out of public copy (bio, caption, cards) until the user confirms it. Anything else the task didn't ask for is reported the same way, as one tiktok report did unprompted: "2줄째에 시리즈 안내 줄 … 을 새로 넣었는데, 이건 지시에 없던 추가야."
- **Opening lines start from [hook-templates](../hook-templates/SKILL.md)** — 2026-10-28·2026-10-29 "이거참고": before writing a first line, a cover or first-card headline, a thumbnail phrase, or a blog title, read hook-templates. It owns every hook rule (which templates fit, no impersonation or inflated hooks, no made-up numbers in experience hooks); the opened references decide which hook to use, but its bans hold.
- **References win over the task's style conditions** — 2026-10-28 "너무구린거같은데": a "줄 앞 이모지 금지" condition in the task went against the references (an emoji per line, short memo tone) and pulled the cards away from them. When a style condition in the task contradicts the references collected, follow the references and write the conflict in the report.
- **No sources in public copy; written as a real person** — 2026-10-29 "출처붙이지말라고 내가진짜 사람이고 내가쓴것처럼하라고": post bodies, replies, captions, cards, and scripts carry no source at all — no source reply or original-link reply, no footnote or source card, no "기준: ○○", no "○○ 발표에 따르면". Write in a natural first person, as someone who saw, used, and wrote it themselves. Sources and the number check go only in the work folder's report. This replaces every older rule that asked for a credit in public copy. It covers written credits only (source replies, footnotes, links, "기준:" lines); showing the original post itself as a visual, like card news' real tweet captures, stays (2026-10-29 "캡처는 유지하셈").
- **No mascot name, no character voice** — 2026-10-29 (user decision 17:34): the @haedollar sea-otter drawing stays as the account's face, but its name "금동이" is retired. Bios, captions, cards, and posts never have a character speak in the third person ("금동이가 ~해 봤어요"); write "제가" or leave the subject out. Everything has to read as written by a person, and the bio is now built on the user's real career (네이버·당근·토스).
- **Phrases the user rejected** — 2026-10-28: "브리핑" (in names and copy); words that narrow the audience (the "해외 AI회사" case above); saying where the material came from ("x에서 골라왔다는건 왜쓰니"); promising material by DM for a comment ("번역본 dm 은 진짜주는거임? 아니면 빼야할듯"); AI-sounding phrasing ("지금 좀 ai같은데") — match the tone of the references' original text instead.
- **Price comparisons state their basis** — 2026-10-28: check whether each price includes VAT and how it's displayed (won price vs. dollar list price). If you can't confirm it, narrow the claim in the title or body in plain words ("부가세 빼고 달러 가격으로 보면"), not as a source-style note.
- **Text posts (Threads, X): everything that matters in the root** — 2026-10-28: thread replies get only 2–4% of the root's views, so the key numbers and the conclusion all go in the root post; replies only add detail.
- **Threads posts follow [threads-voice](../threads-voice/SKILL.md)** — 2026-10-29 "다 졸라 봇같음. 사람이쓴것처럼. 그리고 첫 타래가 왤케기냐고 ㅋ": before writing any Threads root, reply, or comment reply, read threads-voice and run its self-check. It holds the root length caps, the 해요체 voice and topic range, the reaction-post mix, and the bot-signal checklist.
- **X posts follow [x-voice](../x-voice/SKILL.md)** — 2026-10-29 "이거 x쪽도 동일하게 리서치시켜봐": before writing any X post, quote post, or reply, read x-voice and run its self-check. It holds the voice, length, and how to react to other people's posts (quote post, no link) and to comments on ours.
- **Mistakes are recorded the same turn** — 2026-10-28 "똑같은 실수가 여러봇들에서 반복되지않게": several bots run this harness, so a mistake one makes or a lesson one learns is reported within that turn as a `교훈:` line for the skill the feedback intake below points to, and shipped into this plugin from there — never only in a chat reply or a bot's own memory.

## Operations

- **Background remote jobs** — 2026-10-28: a remote job started in the background may never send its completion notice. Wait for its completion file with a blocking loop that has a timeout (`until [ -f <done-file> ]; do sleep 30; done`), not for the notice.
- **A post counts as published only when the logged-out public view shows it** — 2026-10-28 (사용자 승인 16:46): a YouTube comment reported as posted turned out to be someone else's. Report success only after finding, while logged out, an item whose author and text match yours, and record its ID; not found → report it as `미확인`, not as posted.
- **Automated actions start after the platform's official policy is read** — 2026-10-28 (공식 정책 대조 22:31): X bans automated likes at any volume, up to permanent suspension, and a bot was already auto-liking that day. Before turning on likes, follows, replies, or link comments, open that platform's official spam/automation policy and put its URL and the clause quoted in the work folder's report. A reference account doing it is not evidence that it's allowed.
- **Follow back by default; new follows only to references** — 2026-10-29 (user decision 18:11, "x 든 인스타든 팔로우 들어오는건 앵간하면 맞팔하셈. 좋잖아", "네이버블로그도 그렇고"): on X, Instagram/Threads, and Naver blog (이웃·서로이웃 신청), follow back or accept accounts that followed us. Skip: accounts imitating a reference account's handle (likely impersonation); ad, loan, gambling, Telegram-funnel, spam, or bot accounts; promo blogs with almost no posts. At most 5 per round, spread over rounds, never all at once; log every follow-back (platform, account, time) in the work folder's report. Any other new follow goes only to reference accounts. The official-policy rule above still applies before any of it is automated.
- **Causes are reported as `가설:`; operating rules change on facts** — 2026-10-28 "확실한지조사부터": the cause of vanished YouTube comments changed five times in one day, and the link and pause rules changed with each guess. Report a cause as a `가설:` line with how sure you are and how it was checked (logged-in view, logged-out public list, official help page); change an operating rule (a ban, a pause) only on a confirmed fact. This is the operations side of the `가정:` rule above.

## Feedback intake — same turn, every time

Every new piece of user feedback or lesson becomes a `교훈:` line **before** continuing the work:

1. Classify it — this names the target skill: every piece of content → this file's rules; Threads voice, length, or format → `threads-voice`; X voice, length, or format → `x-voice`; every video → shorts-common's "Rules for every video"; one format → that format skill (`foreign-clip-short`, `top3-compilation-short`, `instagram-card-news`, `naver-blog`); a new format → a new `skills/<format>/SKILL.md` that points here (and at shorts-common if it's a video).
2. Write it as a rule with the date and the user's own words in quotes, one line each at column 0 of the report: `교훈: <target skill> — <date "user's words">: <rule>` (`교훈: content-common — 2026-10-28 "지금 좀 ai같은데": …`). Say when it contradicts an existing rule, so the rewrite replaces that rule instead of adding a second one.
3. Then update the pipeline or tooling default it implies, if any.

**Don't edit the harness source (`plugins/shorts/…` in any godsenal-cc checkout) or the installed plugin cache from a content run.** Whatever branch a checkout has out, an uncommitted edit there was left behind on a stale branch and collided with a version that shipped meanwhile (2026-10-28). The `교훈:` lines are the handoff: under `gbase-run` they go to a `work` run on a fresh worktree of the runner's checkout, which reviews them and opens the PR; in an interactive session, hand them to `/gbase:work` once the content is done.
