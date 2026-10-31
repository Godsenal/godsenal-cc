---
name: jev
description: >-
  Puts TypeSafe's Jev (a System One decision model: Choice, Score, Noul, Box answers with
  calibrated probabilities, about $0.04 per million input tokens, no text generation) into the
  user's bots and apps where a cheap, typed judgment beats a regex, a keyword list, or an LLM
  prompt that returns JSON — classification, routing, filtering, quality gates, dedupe,
  self-checks, picking the best candidate or substring. Holds the bot-by-bot use-case map, the
  `jev` CLI for shell and headless runs, the key and data rules, and how to wire one in. Use when
  building or changing a bot or app step that classifies, routes, scores, filters, checks, or
  picks; when asked about Jev, TypeSafe, or "where could Jev help"; or before adding an LLM call
  whose output is one of a fixed set of answers.
---

# Jev (TypeSafe System One)

## 출력 언어

사용자에게 보이는 텍스트는 **한국어**로 쓴다 — 진행 보고, 요약, 리포트 표의 설명 칸까지. 영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·스킬/툴 이름, 질문 키와 옵션 키, 커밋 메시지·브랜치 이름(레포 관례를 따른다). PR 제목·본문은 기본 한국어. 사용자가 다른 언어로 요청하면 그 언어를 따른다.

## 무엇이고 무엇이 아닌가

Jev는 `state`(텍스트·JSON·이미지)와 타입이 정해진 질문들을 받아 구조화된 답을 돌려준다. 글을 쓰지 않고, 코딩 에이전트의 모델을 대신하지도 않는다. 우리 봇에서는 **Claude가 하던 "고르기·매기기·참거짓 판정"을 떼어 내는 용도**로 쓴다.

| 질문 | 답 | 쓰는 곳 |
| - | - | - |
| `choice` | 옵션 하나 + 옵션별 확률 + `confidence` | 분류, 라우팅, 후보 중 최선 고르기, 긴 글에서 줄 id 고르기 |
| `score` | 순서 있는 루브릭 단계 + 확률 + `confidence` | 품질·긴급도·위험도 |
| `noul` | "참일 확률" 0–1 | 게이트(스팸인가, 출처가 주장을 뒷받침하는가) |
| `box` | 이미지 안 위치(0–1 비율) | 크롭·피사체 찾기. `jev-preview` 모델 + `TypeSafe-Danger-Zone-Images: true` 헤더가 필요하다 |

API 형식과 질문 작성법은 외워 쓰지 말고 매번 `https://docs.typesafe.ai/llms.txt`(페이지 경로 + `.md`)에서 확인한다. bots 머신에는 공식 스킬 `typesafe@typesafe-ai`가 깔려 있으니 코드를 짤 때는 그것도 같이 쓴다.

## 호출

- 쉘·headless 봇: `jev` CLI(dotfiles가 bots 머신의 `~/.local/bin/jev`에 설치한다). 사용법은 `jev --help`.
  ```bash
  echo "$comment" | jev noul "이 댓글은 종목 추천·리딩방 홍보 스팸이다"
  jev choice "이 공고의 직무" backend="서버·API" frontend="웹 UI" data="데이터·ML" --state @posting.txt
  jev ask request.json        # 질문 여러 개를 한 요청에 (항상 이쪽이 싸고 빠르다)
  ```
- 앱 코드: `@typesafe-ai/sdk`(Node 22+) 또는 `typesafe-sdk`(Python). 둘 다 `TYPESAFE_API_KEY`를 읽는다.
- 키는 `TYPESAFE_API_KEY` 환경변수로만 받는다. 이 Mac mini에서는 `~/.zshrc.local`에 둔다. 값을 파일·로그·PR·커밋에 남기지 않는다. 키가 없으면 `jev`는 exit 3으로 끝난다. 이때 봇은 하던 방식(기존 규칙이나 LLM)으로 돌아가고, 리포트에 `결정 필요: TYPESAFE_API_KEY 없음` 한 줄을 남긴다.

## 넣는 방법 (실수 방지)

- **판정은 Jev, 행동은 코드.** 임계값과 분기는 코드에 두고, 질문 문구와 임계값 상수는 파일 한 곳에 모은다(리뷰할 건 그것뿐이다).
- 들어가는 자리를 먼저 정한다. 기존 정규식·LLM 판정과 나란히 돌려 **불일치 샘플 20–50개**를 사람이 보기 전까지는 바꿔 끼우지 않는다. 숫자 없이 "더 낫다"고 보고하지 않는다.
- `confidence`가 낮으면 기존 경로(Claude·사람 검토)로 넘긴다(confidence-gated routing). 가장 높은 옵션만 필요하면 임계값 없이 argmax로 끝낸다.
- 한 state에 묻는 질문은 한 요청에 묶는다. 투기적인 질문(speculative fan-out)을 같이 넣어도 된다.
- 외부로 나가는 데이터다. **회사(meraki) 코드·고객 데이터·개인정보는 보내지 않는다.** 개인 봇의 공개 글·공고·자기 초안만 보낸다.

## 봇별 유즈케이스 (효과 큰 순)

1. **kr-it-jobs 크롤러**: 공고마다 도는 판정이라 호출량과 효과가 가장 크다.
   - `apps/crawler/src/classify.ts`의 Haiku "분류기"를 직무 16개 `choice`와 하이라이트 태그별 `noul`로 바꾼다. JSON 파싱이 없어지고, confidence가 낮을 때만 Haiku로 보낸다.
   - `packages/core/src/normalize.ts`의 `CATEGORY_RULES` 정규식은 `other`로 떨어진 공고만 Jev로 재분류한다.
   - `apps/crawler/src/funding/extract.ts`의 "한국 기업 투자유치 확정인가"는 `noul`, 라운드는 `choice`로 판정한다. 금액·회사명 추출은 생성이라 Haiku가 계속 맡는다.
2. **gshorts 댓글·답변 봇(comment-boost, 지식iN, X 인용)**:
   - 대상 고르기 전 필터: **들어가 있음**(2026-11-01) — gshorts `comment-guide/scripts/jev_prefilter.py`(스팸 `noul` + 끼어들 만함 `score`). 답글 제한 `noul`, "우리 블로그 글로 답할 수 있는 질문인가" `score`는 아직 없다.
   - 쓴 뒤 게이트: "답변이 블로그 글 내용과 어긋나지 않는다" `noul`, x-voice·threads-voice의 봇 신호 체크리스트를 항목별 `noul`로 검사한다. 글자·줄 수는 코드로 센다.
3. **gshorts 콘텐츠 제작**:
   - 레퍼런스 글 여러 개를 `score`(성과 신호·형식 적합도)로 순위를 매긴다.
   - hook-templates 25개 중 이 주제에 맞는 것을 `choice`로 고른다.
   - 자막·대본 줄 중 첫 줄 후보를 `choice`로 고른다. Jev는 "긴 글에서 가장 좋은 부분 문자열 고르기"에 특히 강하다.
   - 숏츠 크롭 초점: **들어가 있음**(2026-11-01) — gshorts `foreign-clip-short/scripts/jev_focus.py`(얼굴 `box` + 사람 있음 `noul`, preview). 카드뉴스 크롭은 아직 없다.
4. **Grok Bot 메시지 라우팅(리마인더·여행·채용 등)**: 들어온 요청을 어느 봇/핸들러로 보낼지 `choice`, 급한지 `score`. 애매하면(confidence 낮음) 지금처럼 Claude에 넘긴다.
5. **gbase 하네스**(개인 레포만):
   - `go`/`branch-pr`의 risk tier는 `choice`로 2차 의견을 받는다.
   - review skeptic 전에 finding을 `noul`로 1차로 거른다.
   - `gbase-run`이 보고 줄(`결정 필요:`·`교훈:`)을 정규식으로 못 찾았을 때만 보조로 쓴다.
6. **BestFrame·솜이랑·귤까기**: 온디바이스 앱이라 키를 앱에 넣을 수 없다. 서버 프록시가 생길 때 검토한다.
   - BestFrame `RankingEngine.swift`의 품질 점수는 이미지 `score`, `PhotoClustering.swift`의 같은 장면 여부는 `noul`로 바꿀 수 있다.
   - 재미용("방 분위기에 맞춰 장식 바꾸기" 류)은 우선순위가 낮다.
