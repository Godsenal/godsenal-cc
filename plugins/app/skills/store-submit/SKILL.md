---
name: store-submit
description: >-
  gapp 하네스 6단계 — Claude in Chrome으로 App Store Connect 웹을 자동화해 심사 제출까지 진행.
  버전 생성, 메타데이터 폼 입력(React setter 주입), 스크린샷 업로드(ngrok 터널 + DataTransfer 주입
  — 네이티브 파일 대화상자는 못 쓴다), 개인정보/연령등급 설문 위저드, 빌드 선택, 최종 Submit for
  Review까지. "심사 제출", "앱스토어 제출", "ASC 올려줘", "스토어 등록", "submit for review",
  "스크린샷 업로드" 요청에 이 스킬을 써라. 전제: store-assets 산출물(스크린샷+메타데이터 문서)과
  EAS가 업로드한 빌드. 로그인은 반드시 유저가 직접 한다.
---

# /gapp:store-submit — ASC 웹 자동화 제출

App Store Connect에는 쓸만한 제출 API가 없어 웹 자동화가 실전 해법이다. 이 스킬은 실제 v1.0 제출에서
확립된 요령의 집대성이다. **Claude in Chrome**(`mcp__claude-in-chrome__*`)으로 진행한다.

## 출력 언어

사용자와의 대화 — 진행 보고, 요약, 체크리스트/판정 표, `AskUserQuestion`의 질문·헤더·옵션·설명 — 은 **한국어**로 쓴다. 하위 에이전트를 띄울 때도 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·환경변수·워크플로 YAML·스킬/툴 이름, 고정 라벨과 상태 키워드(`PASS`/`FAIL`/`SKIP`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름·PR 제목/본문 — 이건 대상 레포의 기존 관례를 따른다.

**앱 산출물은 이 규칙이 아니라 `kickoff`에서 정한 앱 언어(`docs/HARNESS.md`)를 따른다.** 앱 UI 문구, 랜딩 카피, 개인정보/지원 페이지, 스토어 메타데이터·스크린샷 문구는 전부 앱 언어로 — 영어 앱에 한국어 스토어 메타데이터를 넣지 않는다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## 안전 규칙 (예외 없음)

- **Apple 로그인/2FA는 유저가 직접.** 자격증명 입력 절대 금지 — 로그인 화면이 나오면 멈추고 요청.
- **최종 "심사를 위해 제출(Submit for Review)" 클릭은 유저 확인 게이트를 거친다** — 제출 요약
  (버전/빌드/가격/지역)을 보여주고 명시적 승인 후 클릭. 그 전까지의 저장은 되돌릴 수 있으니 자동 진행.
- 진행 중 페이지 이탈로 폼이 날아갈 수 있다 — 섹션마다 저장 버튼을 누르고 넘어간다.

## 0. 사전 확인

- **`/gapp:preflight`를 스토어 게이트 포함으로 먼저 돌린다** — NOT READY면 FAIL부터 해소.
- 스크린샷 + `docs/APPSTORE-METADATA.md` 준비됨 (없으면 `/gapp:store-assets` 먼저)
- 처리 완료된 빌드가 ASC에 있음 (`eas build:list` / TestFlight 탭 — 업로드 후 처리 수십 분 걸릴 수 있음)
- **ASC 앱 레코드**: 이미 있는지 먼저 확인하고 없을 때만 생성 (번들ID로 검색). 있는 걸 또 만들지 말 것.
- ngrok 설치·인증 확인 (`which ngrok`) — 스크린샷 업로드에 필요

## 1. 스크린샷 업로드 — 유일하게 되는 방법

**`파일 선택` 네이티브 대화상자는 못 쓴다** (OS 키스트로크 권한 없음, 브라우저는 computer-use read
티어). **localhost 직접 fetch도 Chrome Local Network Access 정책이 차단한다** (요청 자체가 안 나감,
PNA 헤더로도 안 풀림). 검증된 유일 경로:

1. 스크린샷 디렉토리에서 로컬 http 서버 + **ngrok 터널**:
   ```bash
   python3 -m http.server 8899 --directory appstore-screenshots &
   ngrok http 8899   # 터널 URL 확보
   ```
2. ASC 페이지 JS(javascript_tool)에서:
   ```js
   const r = await fetch('<터널URL>/01-feed.png', {headers:{'ngrok-skip-browser-warning':'1'}});
   const blob = await r.blob();
   const dt = new DataTransfer();
   dt.items.add(new File([blob], '01-feed.png', {type:'image/png'}));
   input.files = dt.files;
   input.dispatchEvent(new Event('change', {bubbles:true}));
   ```
3. **한 장씩 순차 업로드** — 여러 장 동시 주입하면 완료 순서로 뒤섞인다. 업로드 완료를 확인하고 다음 장.
4. **input 탐색은 섹션 텍스트 기준** — 6.9"/13" 섹션이 접혀 있으면 펼친 뒤 섹션 텍스트로 찾는다
   (접힘에 따라 input 인덱스가 바뀜).
5. **6.9" 스크린샷(1320×2868)은 기본 드롭존에서 조용히 거부된다** → **미디어 관리(media-manager)**
   페이지의 6.9 섹션에 넣어야 한다. 업로드가 소리 없이 실패하면 이걸 의심하라.

## 2. 메타데이터 폼 입력 (React 폼)

ASC는 React 폼이라 value 직접 대입이 저장 안 된다:
- 텍스트: **prototype value setter + input/change 이벤트 디스패치**
  ```js
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
  setter.call(el, '값'); el.dispatchEvent(new Event('input',{bubbles:true}));
  ```
  (textarea는 HTMLTextAreaElement prototype)
- 체크박스/라디오: `.click()`
- **저장 후 값이 되돌아오는 필드가 있다** (예: 데모계정 필요 토글) — 저장 → 새로고침 → 값 검증 →
  틀리면 다시 토글→저장. **모든 섹션은 저장 후 재검증이 원칙.**
- 입력 내용은 전부 `docs/APPSTORE-METADATA.md`에서 — 즉석 창작 금지.

## 3. 설문 위저드 (개인정보 / 연령등급)

여러 페이지짜리 위저드는 페이지 내 **async 루프**로 자동화한다:
- window에 상태 저장, fire-and-forget으로 루프 시작 후 **폴링으로 진행 확인**.
  javascript_tool은 **45초 CDP 타임아웃**이라 await로 오래 기다리면 안 된다.
- **루프 두 개를 동시에 돌리지 말 것** — 이전 루프가 죽은 줄 알고 새로 띄우면 경합한다.
  반드시 새로고침 후 최종 저장 상태로 검증.
- 연령등급 신설문(7단계)은 라디오 값이 `false`/`NONE` 계열 — 그룹별 해당 값 클릭.
- 답안은 metadata 문서의 초안 기준, 애매한 항목은 유저에게 확인.

## 4. 나머지 섹션 체크리스트

- [ ] 빌드 선택 (버전 페이지에서 처리 완료된 빌드 연결)
- [ ] 수출 규정(암호화) — HTTPS만 쓰면 통상 면제 문구. `app.json`에
      `ios.infoPlist.ITSAppUsesNonExemptEncryption: false` 박아두면 다음부터 안 물어봄 (다음 빌드에 반영)
- [ ] 심사 정보: 연락처, 데모 계정(로그인 필수 앱), 메모
- [ ] 가격/판매 지역, 출시 방식(자동/수동 — 유저에게 확인)
- [ ] 앱 개인정보 라벨 게시(publish) 버튼까지 눌렀는지

## 5. 최종 제출

1. 페이지 상단 경고/누락 항목이 없는지 스캔 — 있으면 해결.
2. **제출 요약을 유저에게 보고**: 버전, 빌드 번호, 스크린샷 수, 가격, 지역, 출시 방식.
3. 유저 승인 → "심사를 위해 제출" 클릭 → 상태가 "심사 대기 중"으로 바뀌는 것 확인.
4. HARNESS.md: store-submit 체크 + 로그에 "vX.Y 빌드 N 제출, <날짜>, 승인 시 <자동/수동> 출시".
5. 보고: 심사는 통상 1~3일, 리젝 시 Resolution Center 확인, TestFlight는 계속 사용 가능.

## 트러블슈팅

- 업로드가 조용히 실패 → 해상도가 그 드롭존 규격과 다름 (1단계 5번). media-manager로.
- 폼 저장이 안 됨 → setter 주입 안 하고 value 대입했는지 확인 (2단계).
- 위저드가 멈춤 → 동시 루프 경합 의심. 새로고침 후 저장 상태 검증하고 하나만 재시작.
- 계속 실패하는 스텝은 3회 이상 반복하지 말고 상황을 정리해 유저에게 (해당 스텝만 수동 처리 요청).
