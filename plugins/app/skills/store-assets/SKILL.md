---
name: store-assets
description: >-
  gapp 하네스 5단계 — App Store 제출용 애셋·메타데이터 준비. iOS 시뮬레이터로 스토어 규격 스크린샷을
  찍는 검증된 파이프라인(preview-simulator 빌드 + 데모 시드 + 화면 강제 + dev FAB 제거)과 스토어
  메타데이터(이름/부제/설명/키워드/개인정보 URL) 작성을 담당한다. "스크린샷 찍자", "스토어 스크린샷",
  "앱스토어 이미지", "스토어 설명 쓰자", "메타데이터 준비" 요청이나 첫 심사 제출 준비 때 이 스킬을
  써라. 실제 ASC 업로드/제출은 store-submit이 담당.
---

# /gapp:store-assets — 스크린샷 + 스토어 메타데이터

산출물: ① 규격 맞는 스크린샷 PNG 세트(`appstore-screenshots/`) ② `docs/APPSTORE-METADATA.md`
(제출 폼에 그대로 붙여넣을 전체 메타데이터). 실기기·로컬 네이티브 빌드 없이 시뮬레이터로 끝낸다.

## 출력 언어

사용자와의 대화 — 진행 보고, 요약, 체크리스트/판정 표, `AskUserQuestion`의 질문·헤더·옵션·설명 — 은 **한국어**로 쓴다. 하위 에이전트를 띄울 때도 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·환경변수·워크플로 YAML·스킬/툴 이름, 고정 라벨과 상태 키워드(`PASS`/`FAIL`/`SKIP`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름·PR 제목/본문 — 이건 대상 레포의 기존 관례를 따른다.

**앱 산출물은 이 규칙이 아니라 `kickoff`에서 정한 앱 언어(`docs/HARNESS.md`)를 따른다.** 앱 UI 문구, 랜딩 카피, 개인정보/지원 페이지, 스토어 메타데이터·스크린샷 문구는 전부 앱 언어로 — 영어 앱에 한국어 스토어 메타데이터를 넣지 않는다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## 규격 (제출 직전 최신 규격 재확인 — Apple이 바꾼다)

- iPhone 6.9" (16 Pro Max급): **1320×2868** PNG — 필수
- iPad 13": **2064×2752** — iPad 지원 앱만
- 각 3~10장. 첫 2~3장이 검색 결과에 노출되므로 코어 루프를 앞에.

## 1. 스크린샷 파이프라인

### 빌드 → 설치
```bash
eas build -p ios --profile preview-simulator   # cicd가 만든 시뮬레이터용 dev-client 프로파일
# 완료 후 .tar.gz 다운로드 → tar -xzf → 설치:
xcrun simctl boot "iPhone 16 Pro Max"           # 6.9" 기기
xcrun simctl install <udid> <extracted>.app
```
프로파일이 없으면 eas.json에 `preview-simulator`(extends development + `ios.simulator: true`) 추가.

### 데모 데이터 (시뮬레이터엔 카메라·실데이터가 없다)
- 샘플 에셋(`assets/sample/*`) + 시드 함수(scaffold 단계의 DevMenu "시드 데이터" 액션)를 사용해
  실사용처럼 보이는 상태를 만든다. 없으면 지금 만든다 — 번들 에셋을 앱 데이터 디렉토리로 복사해
  진짜 데이터처럼 주입하는 방식.
- 이미지 생성 스킬(nanobanana 등)이 있으면 샘플 사진을 앱 컨셉에 맞게 생성해도 좋다.

### 화면 강제 (탭 없이 화면 전환)
임시로 `SHOT_SCREEN` 상수 + 렌더 오버라이드를 앱 루트에 넣고, 값만 바꿔 Fast Refresh로
feed/detail/settings/온보딩 등 원하는 화면을 띄운다. **캡처 끝나면 반드시 원복.**

### dev FAB 제거 (중요 — 모든 샷을 오염시킨다)
dev-client의 플로팅 기어 버튼 끄기:
```bash
xcrun simctl spawn <udid> defaults write <bundle-id> EXDevMenuShowFloatingActionButton -bool false
```
후 앱 재실행(새 프로세스가 pref를 읽음).

### 캡처
```bash
xcrun simctl io <udid> screenshot appstore-screenshots/01-feed.png
```
상태바가 지저분하면 `xcrun simctl status_bar <udid> override --time "9:41" --batteryLevel 100 ...`.

### 알려진 제약 (이 맥 기준 — 다른 환경이면 먼저 시도해보고 판단)
- **시뮬레이터 프로그램적 탭이 안 될 수 있다** (idb 파이썬 비호환, AX 권한 없음). 그 경우 dev 번들
  로드에 수동 탭 2번(딥링크 "열기", dev-menu "Continue")이 필요 — 유저에게 정확히 요청하라.
  그 외 시드·화면전환·캡처는 전부 코드+`simctl`로 자동.
- dev 런처가 Metro를 못 찾으면 (LAN IP 변동) localhost 직결:
  `xcrun simctl openurl <udid> "<scheme>://expo-development-client/?url=http://localhost:8081"`
- iPad 13" 캔버스가 안 맞으면 sips로 보정:
  `sips --resampleHeight 2752 in.png` + `--padToHeightWidth 2752 2064 --padColor <배경hex>`
  (패딩 색은 앱 배경 토큰과 동일하게).

## 2. 스토어 메타데이터 — `docs/APPSTORE-METADATA.md`

제출 폼에 복붙 가능한 완성 문서로 작성. HARNESS.md·DESIGN.md 톤을 따르고 유저 확정을 받는다:

- **이름**(30자) / **부제**(30자) / **키워드**(100자, 쉼표 구분 — 이름·부제와 중복 금지)
- **설명** / **프로모션 텍스트**(170자) / **새로운 기능**(업데이트 시)
- **개인정보처리방침 URL** (필수 — 없으면 마케팅 사이트에 페이지부터. 정적 페이지면 충분)
- **지원 URL** / 마케팅 URL / 지원 이메일 (개인 이메일 노출 주의 — 전용 주소 권장)
- **개인정보 수집 설문 답안 초안** — 실제 SDK가 수집하는 것 기준 (Supabase면: 이메일(로그인 시),
  사용자 콘텐츠, 식별자. 분석 SDK 유무 확인). App Tracking은 광고 안 하면 "아니오".
- **연령 등급 설문 답안 초안** / **심사 메모** (데모 계정 필요 여부 — 로그인 필수 앱이면 준비)
- 카테고리 / 가격 / 판매 지역

## 3. 마무리

- 스크린샷 규격 검증: `sips -g pixelWidth -g pixelHeight appstore-screenshots/*.png`
- SHOT_SCREEN 등 임시 코드 원복 확인 (git diff가 깨끗해야 함)
- HARNESS.md: store-assets 체크, 로그.
- 한 줄 보고 후 **`/gapp:store-submit`을 바로 이어서 실행한다** (이어달리기 규칙 — 그쪽이 시작하며
  preflight 게이트를 돌린다).
