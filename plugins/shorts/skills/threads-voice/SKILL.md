---
name: threads-voice
description: >-
  Sets how a Threads post sounds and how long it is, so it reads like one person typing on a phone and not
  like a bot. It gives hard length caps for the root post, 해요체 for every information post, the @haedollar
  topic range (AI news, hands-on AI tips, AI companies' earnings and money), the occasional real one-line
  reaction post about an AI tool the user actually used, a checklist of bot signals, and a self-check that
  counts lines, characters, and figures before handing off. Every rule comes from top Threads posts opened on
  2026-10-29, each with its URL. Use before writing or rewriting any Threads root post, thread reply, or
  comment reply, including the Threads summary of a card-news carousel (where and when to comment is
  comment-guide's), or when the user says a Threads
  post sounds like a bot or is too long.
---

# threads-voice — Threads 글 말투·형식

Read this before writing any Threads root, reply, or comment. Every rule in [content-common](../content-common/SKILL.md) still applies (references first, no source credits, no made-up numbers or experiences, root holds the conclusion), and so does [hook-templates](../hook-templates/SKILL.md) for the first line, including its bans ("현직 OO" and other impersonation). X posts follow [x-voice](../x-voice/SKILL.md) instead. New feedback goes through content-common's feedback intake and lands here. The measurements and every opened URL are in [references/refs-2026-10-29.md](references/refs-2026-10-29.md).

## 출력 언어

사용자에게 보이는 텍스트(진행 보고, 리포트)와 Threads 산출물(루트, 이어쓰기, 댓글 답글)은 **한국어**로 쓴다. 아래 따옴표 안 한국어는 레퍼런스 원문이나 사용자 피드백 원문이라 고치지 않는다. 코드·경로·명령어는 대상 레포의 관례를 따른다. 사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Why this skill exists

2026-10-29 "아 쓰레드 말투나 형식 별론데... 레퍼런스기반으로 쓰고있는거맞음?", then "다 졸라 봇같음. 사람이쓴것처럼. 그리고 첫 타래가 왤케기냐고 ㅋ". Every @haedollar post had come out of one template: a headline line, a `[대괄호]` keyword, 🦦 at the end, a closing "여러분은 ~?", and far too many numbers. Here is what measuring the posts showed (method in the reference file):

| | 돈 계정 상위 글 (👁1만 이상, 32개) | 직장인 AI 계정 글 (30개) | @haedollar (6개) |
|---|---|---|---|
| 루트 줄 수, 중앙값 | 4 | 6.5 | 8 |
| 루트 글자 수, 중앙값 | 95 | 172 | 263 |
| 루트 숫자 개수, 중앙값 | 1 | 1 | 11 |
| 첫 줄 글자 수, 중앙값 | 17 (돈 45개 기준) | 18 | 27 |
| "여러분 ~?"로 끝난 글 | 0 | 0 | 4 |
| `[대괄호]` 강조를 쓴 글 | 3 (전부 요시샘) | 0 | 3 |
| 이모지 개수, 중앙값 | 0 | 0 | 1 (매번 🦦) |
| 괄호 단서를 쓴 글 ("(27일까지)") | 5/45 | 7/30 | 5/6 |

The problem was the template and the length, not 해요체: see Voice below.

## Topics (@haedollar)

2026-10-29 (user decision): **AI news, hands-on AI tips (everyday use outside work counts), and AI companies' earnings and money.** Money and economy news stays in. Pick each topic from recent X posts (the last ~3 days, official accounts' announcements and Korean posts with big reactions), open the original, and check the numbers and the conditions (plan, region, rollout) before writing. A feature whose conditions you couldn't confirm doesn't get posted. The X URL and numbers go only in the work report; the post never says where it came from ("X에서 봤는데", "○○ 발표에 따르면"). A company or product name is fine as the subject of the sentence.

Readers are ordinary office workers, not developers: no coding, no "프로그램을 만들게 하세요", no developer persona.

## Length caps (count them, don't eyeball)

| | (a) AI 회사 실적·돈·경제 뉴스 | (b) AI 뉴스·실전 팁 |
|---|---|---|
| 루트 줄 수 | **6줄 이하** (목표 4줄) | **8줄 이하** (목표 5줄) |
| 루트 글자 수 (줄바꿈 빼고 공백 포함) | **150자 이하** (목표 100자 안팎) | **170자 이하** |
| 루트에 넣는 수치 (금액·%·배수. "1등", "3일"은 안 셈) | **2개 이하** | **1개 이하**, 0개가 기본 |
| 첫 줄 | 20자 이하 | 20자 이하 |
| 한 줄 | 25자 안팎, 한 호흡에 끊는다 | 같음 |
| 이어쓰기 | 0~1개 (최대 2개), 각 4줄·120자 이하 | 0~1개. 복사해 쓸 문장이나 메뉴 경로만 6줄까지 |

The caps come from 75 posts: money posts with 1만+ views sit at a median of 4 lines and 95 characters, with p75 at 6 lines and 146 characters. On the AI side, the top posts with 20만+ views ran 11 lines / 164자 ([k__j__min](https://www.threads.com/@k__j__min/post/Dd3EZW7is0t), lines of about 15자), 4 lines / 85자 ([jinjin__love](https://www.threads.com/@jinjin__love/post/DewLniEmbTr)), and 4 lines / 133자 at 4.9만 ([the.ddanjit](https://www.threads.com/@the.ddanjit/post/DfBQXAmE69y)). Root-complete still holds: the root says what happened and what you think of it. One reason is enough; the rest goes in a reply or nowhere.

## Voice

- **Information posts are 해요체** — 2026-10-29 (user decision, replacing this skill's earlier "직장인 AI = 반말 혼잣말체", which came from 30 posts of 6 accounts). Of 82 AI/office-work tip posts from 17 accounts, 존댓말 was the most common voice (35%); both accounts with 5만+ followers (choi.openai 29만, aicoffeechat 6.3만) write in 존댓말, and 8 of the top 10 money posts were 존댓말. Telling the reader to do something in 반말 ("~해", "~둬", "~셈") showed up in only 7 of 82 posts (9%). So when you ask the reader to do something, write "~해 두세요", "~넣어 보세요".
- **Prompts keep their own voice.** A line the reader pastes into ChatGPT or Claude goes on its own line in plain instruction form ("모르면 지어내지 말고 모른다고 해줘"); the voice rule doesn't apply inside it. 18 of the 82 posts did this.
- **One person reacting, not a report.** Write what happened, then what you think of it. Even choi.openai, the most article-like account, opens with "🚨속보) 와 미친.. 대구글.." ([DfC9HOlj_Pd](https://www.threads.com/@choi.openai/post/DfC9HOlj_Pd)). At most one short reaction line per root ("~네요", "..") — not `ㅋ`/`ㅋㅋ` in an information root (1 of 82 had it).
- **Honest takes** — 2026-10-29 (user decision): if something is good, say it's good; if it's underwhelming, say so ("이건 생각보다 별로예요"). Posts with an opinion line beat the same account's other posts in 7 accounts and trailed in 2. An opinion is a judgment, not an experience: "개인적으로는 ○○가 더 쓸모 있어 보여요" is fine, "써 보니 ○○였어요" needs a real case.
- **End on the take, not a summary or a question.** Ask a question in at most one post out of three, short and plain, never opened with "여러분". In the measurement, posts with a question trailed the same account's other posts in 6 accounts and beat them in 3.
- **No fixed signature.** Emoji 0 by default; one is fine when it carries a feeling. No 🦦 on every post, no `[대괄호]` keywords (yoshisam_rich's mark, not ours), no ending line reused post after post (quitting_time_lab repeats the same CTA 9–12 times).
- **No precision clutter in the root.** Parentheses like "(27일까지)" or "(1달러 1,343.5원으로 계산)" read as a report. If a basis has to be stated (content-common's price rule), say it in words in the sentence or move it to a reply.

## Human touch without made-up experience

2026-10-29 "진짜 사람이 운영하는것처럼 하는게 좋을듯. 다그러던데..": the top accounts read as human through reactions, opinions, and conversation, not through "I" stories (first-person rate: choi.openai 24%, aicoffeechat 15%, all 17 accounts 34%).

- **Reaction posts, about 1 in 10** — 2026-10-29 "이런글도 올리는거지 claude 5.5 딸깍하니까 일할게 없긴하네요 ㅋㅋ 이런느낌". Mix in a one- or two-line post with no information: the user's own reaction to an AI tool they actually used that day ("claude 5.5 딸깍하니까 일할게 없긴하네요 ㅋㅋ"), or a feeling added to a fact from real news ("크... 드디어 터치스크린 맥북이 나왔네요", choi.openai [DfDdJHhAvVn](https://www.threads.com/@choi.openai/post/DfDdJHhAvVn)). `~네요 ㅋㅋ` is fine here and only here. **The 1-in-10 ratio is an assumption** (measured: 2.3% of 607 root posts; 5 of 6 AI-tool reactions beat their account median, everyday-life ones mostly didn't) — report it as `가정:` and adjust from reactions. No real use or real news that day → no reaction post. A real chat screenshot plus one line beats the line alone (sumrkite ♥9.4천), once it's checked for personal or company information.
- **Never made up**: no experience the user didn't have ("써 보니", "처음 나왔을 때부터 써왔고" — quitting_time_lab pasted that into 13 of 53 posts), no invented counts, hours saved, or earnings, no everyday-life chatter unrelated to AI, no brag numbers.
- **Comments** — replies to comments on our posts and comments on other people's posts follow [comment-guide](../comment-guide/SKILL.md); write them in this skill's voice. Follow-backs follow [content-common](../content-common/SKILL.md)'s follow-back rule.

## (a) AI 회사 실적·돈·경제 뉴스

One number, one twist, one take, in 해요체. Reference originals for the length and shape (full table in the reference file; borrow the shape, not their 반말 lines):
- "찐 하락장은 / SCHD, 코카콜라, 알트리아 / 같은 배당주도 박살 나야해요 / 지금은 성장주만 빠지고 / 배당주는 올라가고 있으니 / 단순히 [조정장]이라 생각🦖" 6줄 77자, 👁3.4만 ♥846 [De1XIA8E4xK](https://www.threads.com/@yoshisam_rich/post/De1XIA8E4xK)
- "큰손들이 5년 만에 가장 크게 '하락'에 베팅했다고 합니다." 1줄, 👁8.4만 [De0lMZMEsR7](https://www.threads.com/@ho_ho_ju_ju/post/De0lMZMEsR7)
- "한번 더 강조하는데 / 6억 대출 받으면 이자만 6.2억입니다… / 배보다 배꼽이 더 큰데 집 왜 사는거야;;;;" 👁36만 ♥596 [DeJpx7vAaBU](https://www.threads.com/@busang.gu/post/DeJpx7vAaBU)

### 전→후 1: 2026-10-29 08시 구글 글 ([DfDsYhCE_cH](https://www.threads.com/@haedollar/post/DfDsYhCE_cH), 8줄 270자 수치 9개)

전:
```
AI 1등 모델 낸 날, 구글 주가는 -8%였어요

어제 구글 새 AI가 성능 순위 1위에 올랐는데
같은 날 실적 발표 뒤 시간외에서 한때 8% 넘게 빠졌어요.

클라우드 매출은 1년 새 두 배(41조 원)로 뛰었는데
AI 설비에 한 분기 69조 원을 쓰면서 [남는 현금]이 -12조 원이 됐거든요.

같은 날 MS는 설비투자를 2배로 늘리고도 남는 현금 +25조 원, 주가는 +5%였어요.

AI를 잘 만드는 것보다 현금이 남는지를 먼저 보는 장 같아요🦦
여러분 계좌엔 구글이 있어요, MS가 있어요?
```
후 (6줄 100자, 수치 2개):
```
구글 AI가 1등 한 날
주가는 한때 8% 넘게 빠졌어요

AI 설비에 한 분기 69조를 쓰니까
남는 현금이 마이너스가 됐거든요

요즘 장은 AI 잘 만드는 회사보다
돈 남기는 회사를 사주네요
```
What changed: the MS comparison, 41조, and -12조 leave the root. The headline line, `[대괄호]`, 🦦, and the "여러분" question are gone. It ends on the take.

### 전→후 2: 환율 글 ([DfCg2XXk2Y-](https://www.threads.com/@haedollar/post/DfCg2XXk2Y-), 9줄 377자)

전: "환율 구간별로 달라지는 AI 값 6가지 (원/달러, 가격 페이지 표시가 기준) / 1. 1,300원 — 클로드 Pro 월 28,600원, 챗GPT Plus(29,000원)보다 싸요 / … / 여러분은 어떤 AI 구독 쓰세요?🦦"

후 (4줄 83자, 수치 1개):
```
환율 1,319원 넘으면
클로드 Pro가 챗GPT Plus보다 비싸져요

챗GPT는 원화, 클로드는 달러로 받아서
오늘 환율이면 이미 클로드가 더 비싸요..
```

### 전→후 3: 앤트로픽 S-1 글 ([DfByo5JE6q_](https://www.threads.com/@haedollar/post/DfByo5JE6q_), 5줄 185자)

전: "Claude 회사 장부 열어보니 직원 1명이 87억 원을 벌었어요.. / 앤트로픽이 10월 26일 나스닥 상장 서류(S-1)를 냈는데요. / 올해 상반기 매출이 163억 달러로 1년 만에 14배가 됐어요. / 그런데 같은 서류에 순손실 107조 원이 찍혀 있어요. / 11월 16일 주간 상장이 목표라는데, 살지 말지 고민하기 전에 숫자부터 까봤어요 🧵"

후 (4줄 76자, 수치 1개):
```
Claude 회사가 상장 서류 냈는데
1년 만에 매출이 14배래요

근데 같은 서류에 적자도 찍혀 있어요
매출만 보고 들뜰 일은 아닌 것 같아요
```

## (b) AI 뉴스·실전 팁

Shape: one line of news or one problem, then the one thing to do today. Three shapes did well (originals quoted in their own voice; ours is 해요체):
1. **"이렇게 시키지 마" → what to say instead**: "ChatGPT한테 / "잘 써줘" / "자연스럽게 고쳐줘" / 이렇게만 말하지 마세요❌ …" 👁28만 ♥1천 [Dd3EZW7is0t](https://www.threads.com/@k__j__min/post/Dd3EZW7is0t)
2. **One scene at work and one question**: "신규직원이 들어왔는데. / 서류를 전부 챗지피티로 작성을 해. / … 나는 꼰대일까." 4줄 85자, 👁21만 💬114 [DewLniEmbTr](https://www.threads.com/@jinjin__love/post/DewLniEmbTr). Only from a scene the user actually saw.
3. **A money tip in plain talk**: "개인사업자 있는 사람, AI 구독료 10% 그냥 내고 있으면 손해야. / …" 👁4.9만 ↗125 [DfBQXAmE69y](https://www.threads.com/@the.ddanjit/post/DfBQXAmE69y)

### 전→후 1: 직장인AI 1편 ([DfC3rkykwaW](https://www.threads.com/@haedollar/post/DfC3rkykwaW), 20줄 338자)

전: "ChatGPT한테 / "이거 확실해?" / 매번 되묻고 있다면 / 설정에 한 번만 적어 두세요 / 설정 → 개인 맞춤 설정 / → '맞춤 설정 활성화' 켜기 / … / 여러분은 ChatGPT한테 매번 하는 잔소리 뭐 있어요?🦦"

후 (루트 5줄 102자, 수치 0개. 메뉴 경로는 답글 1개에):
```
ChatGPT한테 "이거 확실해?"
매번 되묻고 있으면 설정에 한 줄 넣어 두세요

모르면 지어내지 말고 모른다고 해줘

새 채팅마다 말 안 해도 되고 무료도 돼요
넣는 곳은 답글에 적어 둘게요
```

### 전→후 2: 시리즈 기획안의 첫 글 초안 (15줄 235자)

전: "개발자로 일하다가 알게 된 것 하나 / AI한테 매일 같은 일을 시키지 마세요 / 그 일을 대신 하는 작은 프로그램을 / 한 번만 만들어 달라고 하세요 / … / 여러분은 AI한테 매일 시키는 일 뭐 있어요?" The developer framing and the "make a program" angle are wrong for this audience.

후 (5줄 90자, 수치 0개):
```
ChatGPT한테 매주 같은 설명
처음부터 다시 하고 있다면
'프로젝트' 하나 만들어서 거기 넣어 두세요

넣어 둔 설명이랑 파일은
그 안에서 새 채팅 열어도 그대로 가요
```
Check feature names, menus, and which plan has them on the official page right before posting; the check goes in the work report, not the post.

## Bot signals — if any of these is in the draft, rewrite it

1. More lines or characters than the caps above, or more figures than allowed.
2. A headline first line followed by an explanation paragraph ("○○한 날, ○○는 -8%였어요" + "어제 ~했는데 ~했어요.").
3. 반말 telling the reader what to do ("~해", "~둬", "~셈") in an information post, or 음슴체 information posts.
4. A closing "여러분은 ~?" or any question that starts with "여러분".
5. `[대괄호]` emphasis, or the same emoji or ending line on every post.
6. Parenthetical qualifiers or calculation notes in the root.
7. Report verbs and connectors: "~했는데요", "~라고 합니다" (passing on news is fine once), "~거든요" chained twice, "집계", "기준", "발표에 따르면".
8. A because-chain that explains everything: cause, comparison, and a second comparison in one root.
9. A closing lesson line ("결국 중요한 건 ~", "~를 먼저 보는 장 같아요") that restates the post instead of giving a take.
10. Numbered list roots for news.
11. No reaction or opinion anywhere — or a hedge where a plain "좋아요" / "별로예요" belongs. `ㅋㅋ` in an information root.
12. An experience, count, or saving the user didn't actually have.
13. Same opening template or same ending shape as the previous post (hook-templates' no-repeat rule).

## Self-check before handing off

Count, don't estimate. Save the root to a file and run:

```bash
python3 -c 'import re,sys;t=open(sys.argv[1]).read().strip();L=[l for l in t.splitlines() if l.strip()];print(len(L),"줄",len("".join(L)),"자 | 숫자후보",re.findall(r"\d+(?:[.,]\d+)*",t),"| 첫줄",len(L[0]),"자")' root.txt
```

Then walk the bot-signal list line by line, rewrite until nothing matches, and read it aloud once: if a line sounds like a news anchor, cut it. Put one line in the work report, for example `voice-check: (a) 6줄 100자 수치 2 | 봇 신호 0 | 훅 #없음`, so the next bot and the user can see it was done.

## Not copied from references

- "(댓글에 계속)" and "끝까지 읽어보세요": the root ends the post.
- Comment→DM bait ("댓글에 저요", kook0526 — 109 comments, 0 author replies), 단톡방·무료특강 links, and flat buy/sell orders ("금 사지마세요", "따라갈거면 지금 사는 게 맞아요"). We give the number and a take; we never tell people to buy or sell.
- Source credits in any form, and job-title claims ("현직 OO").
