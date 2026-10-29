---
name: x-voice
description: >-
  Sets how an X (Twitter) post from the gshorts accounts (@wolgeupnal, 월급날) sounds, how long it is, and how
  it engages, so it reads like one person and not a link bot: 해요체 or title-style information posts, short
  roots (top-quartile median 52자), quote posts with a one-line opinion instead of link replies on other
  people's posts, direct replies to comments on our own posts, and no source wording anywhere. Rules come from
  140 posts of 20 Korean money accounts opened on 2026-10-29. Use before writing any X post, quote post,
  thread reply, or comment reply, or when the user says an X post sounds like a bot.
---

# x-voice — X 글 말투·형식

Read this before writing anything for X. Every rule in [content-common](../content-common/SKILL.md) still applies (references first, no source credits, no made-up numbers or experiences, root holds the conclusion), and so does [hook-templates](../hook-templates/SKILL.md) for the first line, including its bans ("현직 OO"). Threads posts follow [threads-voice](../threads-voice/SKILL.md) instead. New feedback goes through content-common's feedback intake and lands here.

## 출력 언어

사용자에게 보이는 텍스트(진행 보고, 리포트)와 X 산출물(글, 인용 글, 이어쓰기, 답글)은 **한국어**로 쓴다. 아래 따옴표 안 한국어는 레퍼런스 원문이나 사용자 피드백 원문이라 고치지 않는다. 코드·경로·명령어는 대상 레포의 관례를 따른다. 사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Why this skill exists

2026-10-29 "이거 x쪽도 동일하게 리서치시켜봐". Of 32 @wolgeupnal posts checked that day, 18 were replies on other people's popular posts, each "one fact + blog.naver.com link" at even intervals over 13 hours; 4 were source replies ("출처 (2026.10.27 확인) …"); the roots were 음슴체 ("모음", "확인함"). Among the 20 reference accounts, that link-reply shape showed up only on a promo account, and the "same sentence frame, 60+ posts a day" account (afterwork2604) sat at a median of 0 likes. Measurements: 20 Korean money/benefit accounts, 140 posts opened one by one (likes, views, author's own thread and comment replies), plus 1,213 timeline posts. The account's topic is money and benefits (지원금·환급·연말정산·생활 혜택), so the references are money accounts; collect AI accounts first before writing AI posts here.

## Voice

- **Information posts: 해요체 (합쇼 is fine) or a title-style noun phrase** ("~하는 법", "~정리", "10/30(금) 메가커피 50% 할인"). Of the 12 top-quartile money posts (♥700+), 6 were 존댓말 and 4 title-style; 음슴체 was 1, though 19 음슴체 information posts were in the sample. No 음슴체 information roots.
- **Reaction posts may be 반말, 음슴체, `ㅋㅋ`, `..`.** None of the top 23 non-information posts were 존댓말. Still no 반말 telling the reader what to do ("~해", "~셈", "~둬"): 4 of 140, none in the top quartile.
- **Honest takes**: good is good, underwhelming is underwhelming. Posts with an opinion line beat the same account's other posts in 9 accounts and trailed in 3, the clearest marker measured.
- **Reaction posts only about money or work**, and only real: the user's own reaction or a feeling added to a fact in real news. Everyday-life monologue mostly underperformed (61 of 80 below the account median). No made-up experience, count, or earnings.

## Length

- **Short.** Top-quartile body median is **52자**, the rest 151자; 17 of 36 posts under 50자 were top quartile, 4 of 25 over 300자. Aim for about 50자 on reactions and opinions.
- **Information posts**: first line about 25자 or less (top quartile 20자), key numbers and the deadline in the root, everything else cut. They run longer than reactions (money info median 243자), so count and report it, and cut before adding a thread.
- **Thread**: 0–1 continuation that extends the body or adds a short aside. No continuation that holds only a source or a link.

## Engaging

- **Other people's posts: quote post + one line of opinion, no link.** 12 of 26 money/work reaction posts were quote posts, including the top 3 (♥483, 117, 91). Don't reply to other people's posts with a blog link; don't reply on a schedule.
- **Comments on our own posts: answer them directly** — 2026-10-29 (user decision). 17 of 20 accounts did, on 101 of 140 posts; the 3 that never did were a save-curation account, a discount-notice account, and the 0-like automation account.
- **No source wording anywhere**: no source reply, no "(2026.10.27 확인)", no "출처", no "공고 원문 보고 출처 같이 남김" in the bio. No account in the sample posted a source reply. Sources stay in the work report (content-common).
- No DM bait, no band or Telegram links, no "맞팔드려요" in copy. Following back is content-common's follow-back rule (follow back by default, skip impersonation/spam/bots, ≤5 per round, logged), not a post.

## Bot signals — if any of these is in the draft, rewrite it

1. 음슴체 information root, or 반말 telling the reader what to do.
2. A reaction post over ~100자, or an information post padded past its numbers and deadline.
3. A link in a reply on someone else's post, or a reply where a quote post belongs.
4. Any source wording, check date, or source-only continuation.
5. The same sentence frame or ending as the previous post.
6. No take at all, or an experience the user didn't have.

## Self-check before handing off

Count, don't estimate. Save the post to a file and run:

```bash
python3 -c 'import re,sys;t=open(sys.argv[1]).read().strip();L=[l for l in t.splitlines() if l.strip()];print(len(L),"줄",len("".join(L)),"자 | 숫자후보",re.findall(r"\d+(?:[.,]\d+)*",t),"| 첫줄",len(L[0]),"자")' post.txt
```

Walk the bot-signal list, then put one line in the work report, for example `voice-check: x 정보 2줄 64자 | 봇 신호 0 | 인용 글`.
