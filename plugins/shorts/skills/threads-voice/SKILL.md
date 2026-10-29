---
name: threads-voice
description: >-
  Sets how a Threads post sounds and how long it is, so it reads like one person typing on a phone and not
  like a bot. It gives hard length caps for the root post, separate voice rules for money and economy news
  posts and for the everyday-AI-at-work series, a checklist of bot signals, and a self-check that counts
  lines, characters, and figures before handing off. Every rule comes from 75 top Threads posts opened on
  2026-10-29, each with its URL. Use before writing or rewriting any Threads root post, thread reply, or
  comment reply, including the Threads summary of a card-news carousel, or when the user says a Threads
  post sounds like a bot or is too long.
---

# threads-voice — Threads 글 말투·형식

Read this before writing any Threads root, reply, or comment. Every rule in [content-common](../content-common/SKILL.md) still applies (references first, no source credits, no made-up numbers or experiences, root holds the conclusion), and so does [hook-templates](../hook-templates/SKILL.md) for the first line, including its bans. New feedback goes through content-common's feedback intake and lands here. The measurements and every opened URL are in [references/refs-2026-10-29.md](references/refs-2026-10-29.md).

## 출력 언어

사용자에게 보이는 텍스트(진행 보고, 리포트)와 Threads 산출물(루트, 이어쓰기, 댓글 답글)은 **한국어**로 쓴다. 아래 따옴표 안 한국어는 레퍼런스 원문이나 사용자 피드백 원문이라 고치지 않는다. 코드·경로·명령어는 대상 레포의 관례를 따른다. 사용자가 다른 언어로 요청하면 그 언어를 따른다.

## Why this skill exists

2026-10-29 "아 쓰레드 말투나 형식 별론데... 레퍼런스기반으로 쓰고있는거맞음?", then "다 졸라 봇같음. 사람이쓴것처럼. 그리고 첫 타래가 왤케기냐고 ㅋ". Every @haedollar post had come out of one template: 해요체 on every line, a `[대괄호]` keyword, 🦦 at the end, and a closing "여러분은 ~?". Here is what measuring the posts showed (method in the reference file):

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
| ㅋ·ㅠ·;;·..·!!·… 가 하나라도 있는 글 | 20/45 | 9/30 | 1/6 |
| 줄 끝이 "~요/~니다"인 비율 | 0.25 | 0.13 | 0.48 (반말 줄 0) |

## Length caps (count them, don't eyeball)

| | (a) 돈·경제 뉴스 | (b) 직장인 AI 활용법 |
|---|---|---|
| 루트 줄 수 | **6줄 이하** (목표 4줄) | **8줄 이하** (목표 5줄) |
| 루트 글자 수 (줄바꿈 빼고 공백 포함) | **150자 이하** (목표 100자 안팎) | **170자 이하** |
| 루트에 넣는 수치 (금액·%·배수. "1등", "3일"은 안 셈) | **2개 이하** | **1개 이하**, 0개가 기본 |
| 첫 줄 | 20자 이하 | 20자 이하 |
| 한 줄 | 25자 안팎, 한 호흡에 끊는다 | 같음 |
| 이어쓰기 | 0~1개 (최대 2개), 각 4줄·120자 이하 | 0~1개. 복사해 쓸 문장이나 메뉴 경로만 6줄까지 |

The caps come from the 75 posts: money posts with 1만+ views sit at a median of 4 lines and 95 characters, with p75 at 6 lines and 146 characters. On the AI side, the top posts with 20만+ views ran 11 lines / 164자 ([k__j__min](https://www.threads.com/@k__j__min/post/Dd3EZW7is0t), lines of about 15자), 4 lines / 85자 ([jinjin__love](https://www.threads.com/@jinjin__love/post/DewLniEmbTr)), and 4 lines / 133자 at 4.9만 ([the.ddanjit](https://www.threads.com/@the.ddanjit/post/DfBQXAmE69y)). The long essay-style lists (midor_i777, about 480자) are a different format, a personal diary, and this account doesn't write those. Root-complete still holds: the root says what happened and what you think of it. It doesn't walk through every cause. One reason is enough; the rest goes in a reply or nowhere.

## Voice for both topics

- **One person reacting, not a report.** Write the line you would type to a friend after seeing the news: what happened, then how you feel or what you'd do about it. Even choi.openai (29만 followers, the most article-like account) opens with "🚨속보) 와 미친.. 대구글.." ([DfC9HOlj_Pd](https://www.threads.com/@choi.openai/post/DfC9HOlj_Pd)).
- **Mixed endings.** Don't end every line with "~요". Let at least one line be self-talk ("~네", "~더라", "~임", "~함", "..", ";;"), the way busang.gu mixes them: "6억 대출 받으면 이자만 6.2억입니다… / 배보다 배꼽이 더 큰데 집 왜 사는거야;;;;" (👁36만, [DeJpx7vAaBU](https://www.threads.com/@busang.gu/post/DeJpx7vAaBU)).
- **End on the reaction, not a summary or a question.** Stop at the opinion or the feeling line. Ask a question in at most one post out of three, and when you do, keep it short and plain ("다들 어떻게 봄?", "나만 그래?"). Never open it with "여러분".
- **No fixed signature.** Emoji 0 by default; one is fine when it carries a feeling, not as a stamp. No 🦦 on every post, no `[대괄호]` keywords (that's yoshisam_rich's own mark, not ours).
- **No precision clutter in the root.** Parentheses like "(27일까지)", "(1달러 1,343.5원으로 계산)", "(원/달러, 가격 페이지 표시가 기준)" read as a report. If a basis has to be stated (content-common's price rule), say it in words inside the sentence, or move it to the reply.

## (a) 돈·경제 뉴스

Voice: 해요체 as the base, with one or two self-talk lines mixed in (yoshisam_rich, busang.gu). One number, one twist, one take.

Reference originals (full table in the reference file):
- "찐 하락장은 / SCHD, 코카콜라, 알트리아 / 같은 배당주도 박살 나야해요 / 지금은 성장주만 빠지고 / 배당주는 올라가고 있으니 / 단순히 [조정장]이라 생각🦖" 6줄 77자, 👁3.4만 ♥846 [De1XIA8E4xK](https://www.threads.com/@yoshisam_rich/post/De1XIA8E4xK)
- "이게 왜 진짜?... / 하늘을 나는 테슬라 로드스터 / ??? : 테슬라 풀매수 하면 되나요?" 3줄 47자, 👁8.1천 [Deii0UxH3Fq](https://www.threads.com/@chaem_mii/post/Deii0UxH3Fq)
- "한번 더 강조하는데 / 6억 대출 받으면 이자만 6.2억입니다… / 배보다 배꼽이 더 큰데 집 왜 사는거야;;;;" 👁36만 ♥596 [DeJpx7vAaBU](https://www.threads.com/@busang.gu/post/DeJpx7vAaBU)
- "큰손들이 5년 만에 가장 크게 '하락'에 베팅했다고 합니다." 1줄, 👁8.4만 [De0lMZMEsR7](https://www.threads.com/@ho_ho_ju_ju/post/De0lMZMEsR7)
- "금 16만원 돌파, 금사지말라고 3개월가까이 말하고 있습니다. …" 1줄 69자, 👁96만 [De8RAvvkviS](https://www.threads.com/@invest_safety/post/De8RAvvkviS). Use it for the length only; its repeated "사지마세요" is the investment pushing we don't copy.

### 전→후 1: 2026-10-29 08시 구글 글 (게시된 글 [DfDsYhCE_cH](https://www.threads.com/@haedollar/post/DfDsYhCE_cH), 8줄 270자 수치 9개)

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
후 (6줄 99자, 수치 2개):
```
구글 AI가 1등 한 날
주가는 한때 8% 넘게 빠졌어요

AI 설비에 한 분기 69조를 쓰니까
남는 현금이 마이너스가 됐거든요

요즘 장은 AI 잘 만드는 회사보다
돈 남기는 회사를 사주네
```
What changed: the MS comparison, 41조, and -12조 come out of the root (one reply at most). The headline line, `[대괄호]`, 🦦, and the "여러분" question are gone. It ends on the take, written as self-talk.

### 전→후 2: 환율 글 ([DfCg2XXk2Y-](https://www.threads.com/@haedollar/post/DfCg2XXk2Y-), 9줄 377자, 👁48)

전: "환율 구간별로 달라지는 AI 값 6가지 (원/달러, 가격 페이지 표시가 기준) / 1. 1,300원 — 클로드 Pro 월 28,600원, 챗GPT Plus(29,000원)보다 싸요 / … 6. 1,582원 — … / 챗GPT는 [원화]로, 클로드는 [달러]로 값을 매겨서 생기는 차이예요 / 여러분은 어떤 AI 구독 쓰세요?🦦"

후 (4줄 82자, 수치 1개):
```
환율 1,319원 넘으면
클로드 Pro가 챗GPT Plus보다 비싸져요

챗GPT는 원화, 클로드는 달러로 받아서
오늘 환율이면 이미 클로드가 더 비쌈..
```

### 전→후 3: 앤트로픽 S-1 글 ([DfByo5JE6q_](https://www.threads.com/@haedollar/post/DfByo5JE6q_), 5줄 185자, 루트 👁149, 이어쓰기 👁2~5)

전: "Claude 회사 장부 열어보니 직원 1명이 87억 원을 벌었어요.. / 앤트로픽이 10월 26일 나스닥 상장 서류(S-1)를 냈는데요. / 올해 상반기 매출이 163억 달러로 1년 만에 14배가 됐어요. / 그런데 같은 서류에 순손실 107조 원이 찍혀 있어요. / 11월 16일 주간 상장이 목표라는데, 살지 말지 고민하기 전에 숫자부터 까봤어요 🧵"

후 (4줄 77자, 수치 1개):
```
Claude 만든 회사가 상장 서류를 냈는데
1년 만에 매출이 14배래요

근데 같은 서류에 적자도 찍혀 있음
살지 말지는 숫자 보고 정하는 걸로
```

## (b) 직장인 AI 활용법

Readers are ordinary office workers, not developers. No coding, no "프로그램을 만들게 하세요", no developer persona; use outside work (travel plans, YouTube summaries, household paperwork) is fine. Voice: 반말 self-talk ("~함", "~더라", "~해봐", "~됨"). That's how k__j__min, jinjin__love, the.ddanjit, and jugalnam write, and only 13% of line endings in this group are "~요/~니다". The one 합니다 account, kook0526, earns its replies with "댓글에 저요" DM bait, which we don't copy.

Three shapes did well:
1. **"이렇게 시키지 마" → what to say instead**, saved and shared: "ChatGPT한테 / "잘 써줘" / "자연스럽게 고쳐줘" / 이렇게만 말하지 마세요❌ / 나도 예전에는 이렇게 시켰는데 / 결과물이 항상 비슷하고 AI 티가 났음. …" 👁28만 ♥1천 🔁564 ↗897 [Dd3EZW7is0t](https://www.threads.com/@k__j__min/post/Dd3EZW7is0t)
2. **One scene at work and one question**, which gets replies: "신규직원이 들어왔는데. / 서류를 전부 챗지피티로 작성을 해. / 활용을 잘하는 건 좋은데 / 처음에는 좀 혼자 써보려는 노력이 필요하지 않을까 생각하는 나는 꼰대일까." 4줄 85자, 👁21만 💬114 [DewLniEmbTr](https://www.threads.com/@jinjin__love/post/DewLniEmbTr). Only from a scene the user actually saw.
3. **A money tip in plain talk**: "개인사업자 있는 사람, AI 구독료 10% 그냥 내고 있으면 손해야. / 챗GPT나 클로드 결제 정보에 사업자등록번호를 넣으면 다음 결제부터 부가세 10%가 빠져. / 3만 3천 원 내던 게 3만 원이 되는 식이야." 👁4.9만 ↗125 [DfBQXAmE69y](https://www.threads.com/@the.ddanjit/post/DfBQXAmE69y)

Short reactions count too: "Claude + Aside 알려준 사람 절받으세요 / 진짜 속도가 미쳤네요ㄷㄷ…." 2줄 42자, 👁10만 [DeimnS_AXud](https://www.threads.com/@busang.gu/post/DeimnS_AXud).

### 전→후 1: 직장인AI 1편 ([DfC3rkykwaW](https://www.threads.com/@haedollar/post/DfC3rkykwaW), 20줄 338자, 👁158)

전: "ChatGPT한테 / "이거 확실해?" / 매번 되묻고 있다면 / 설정에 한 번만 적어 두세요 / 설정 → 개인 맞춤 설정 / → '맞춤 설정 활성화' 켜기 / → '맞춤형 지침' 칸 / (폰 앱은 …) / 여기에 이 네 줄 붙여 넣으면 돼요👇 / (네 줄) / 무료 요금제에서도 되고 / 새 채팅마다 같은 말 안 해도 돼요 / 그래도 틀릴 때는 있으니까 / 보고서에 들어갈 숫자는 한 번 더 보세요 / 여러분은 ChatGPT한테 매번 하는 잔소리 뭐 있어요?🦦"

후 (루트 5줄 93자, 수치 0개. 메뉴 경로와 나머지 세 줄은 답글 1개에):
```
ChatGPT한테 "이거 확실해?"
매번 되묻고 있으면 설정에 한 줄 넣어둬

"모르면 지어내지 말고 모른다고 해줘"

새 채팅마다 말 안 해도 되고 무료도 됨
넣는 곳은 답글에
```

### 전→후 2: 시리즈 기획안의 첫 글 초안 (workai_plan 2026-10-29, 15줄 235자)

전: "개발자로 일하다가 알게 된 것 하나 / AI한테 매일 같은 일을 시키지 마세요 / 그 일을 대신 하는 작은 프로그램을 / 한 번만 만들어 달라고 하세요 / … / ChatGPT Plus 한 달 29,000원 / 저는 이 돈을 '만드는 데' 써요🦦 / 여러분은 AI한테 매일 시키는 일 뭐 있어요?" The developer framing and the "make a program" angle are wrong for this audience.

후 (5줄 85자, 수치 0개):
```
ChatGPT한테 매주 같은 설명
처음부터 다시 하고 있으면
'프로젝트' 하나 만들어서 거기 넣어둬

넣어둔 설명이랑 파일은
그 안에서 새 채팅 열어도 그대로 감
```
Check feature names, menus, and which plan has them on the official page right before posting. Products change, and the user doesn't want sources in the post, so the check goes in the work report.

## Bot signals — if any of these is in the draft, rewrite it

1. More lines or characters than the caps above, or more figures than allowed.
2. A headline first line followed by an explanation paragraph ("○○한 날, ○○는 -8%였어요" + "어제 ~했는데 ~했어요.").
3. Every line ends in "~요" or "~니다", with no self-talk line.
4. A closing "여러분은 ~?" or any question that starts with "여러분".
5. `[대괄호]` emphasis, or the same emoji at the end of every post.
6. Parenthetical qualifiers or calculation notes in the root.
7. Report verbs and connectors: "~했는데요", "~라고 합니다" (passing on news is fine once), "~거든요" chained twice, "집계", "기준", "발표에 따르면".
8. A because-chain that explains everything: cause, comparison, and a second comparison in one root.
9. A closing lesson line ("결국 중요한 건 ~", "~를 먼저 보는 장 같아요") that restates the post.
10. Numbered list roots for news (references use lists for diaries and save-posts, not for news).
11. Not a single human touch: no reaction, no self-talk, no "..", "ㅋㅋ", ";;", "ㄷㄷ". Use one where it's real; don't stack them or fake an experience to get one.
12. Same opening template or same ending shape as the previous post (hook-templates' no-repeat rule).

## Self-check before handing off

Count, don't estimate. Save the root to a file and run:

```bash
python3 -c 'import re,sys;t=open(sys.argv[1]).read().strip();L=[l for l in t.splitlines() if l.strip()];print(len(L),"줄",len("".join(L)),"자 | 숫자후보",re.findall(r"\d+(?:[.,]\d+)*",t),"| 첫줄",len(L[0]),"자")' root.txt
```

Then walk the bot-signal list line by line, rewrite until nothing matches, and read it aloud once: if a line sounds like a news anchor, cut it. Put one line in the work report, for example `voice-check: (a) 6줄 99자 수치 2 | 봇 신호 0 | 훅 #없음`, so the next bot and the user can see it was done.

## Not copied from references

- "(댓글에 계속)" and "끝까지 읽어보세요": the root ends the post.
- A "나도 해봤는데" line without a real case from the user. Write it as a tip instead of a story.
- Comment→DM bait ("댓글에 저요", kook0526), 단톡방·무료특강 links (bstory_economy, _hee_r_chan), and flat buy/sell orders ("그냥 외우세요", "금 사지마세요", "따라갈거면 지금 사는 게 맞아요"). We give the number and a take; we never tell people to buy or sell.
