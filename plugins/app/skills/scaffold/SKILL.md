---
name: scaffold
description: >-
  gapp 하네스 1단계 — Expo 앱 환경세팅. 반드시 그 시점 최신 SDK를 조회해서 프로젝트를 생성하고,
  TypeScript strict + jest + typecheck + 부트스트랩 순서 + env 규약 + DevMenu 패턴 같은
  검증된 컨벤션을 깔고, 새 레포의 CLAUDE.md("버전 고정 문서만 봐라" 규칙 포함)까지 생성한다.
  "환경세팅", "프로젝트 생성", "expo 세팅", "스캐폴드", "보일러플레이트" 요청이나 kickoff 직후
  다음 단계로 이 스킬을 써라. 전제: docs/HARNESS.md가 있으면 그 결정사항을 따른다.
---

# /gapp:scaffold — Expo 환경세팅

kickoff에서 확정한 결정(HARNESS.md)을 코드로 만든다. HARNESS.md가 없으면 최소 결정(앱이름/번들ID/
백엔드 유무)만 즉석에서 묻고 진행하되, 끝나고 HARNESS.md 소급 생성을 권한다.

## 0. 최신 버전 조회 — 기억 금지

**Expo는 SDK마다 API가 크게 바뀐다. 학습된 기억으로 코드를 쓰면 반드시 깨진다.** 시작 전에:

1. https://docs.expo.dev/versions/latest/ 를 WebFetch → 현재 SDK 번호, RN/React 버전 확인
2. HARNESS.md의 "조회일"이 오래됐으면 갱신
3. **이후 이 프로젝트의 모든 Expo/RN 코드는 `https://docs.expo.dev/versions/v<N>.0.0/` 버전 고정
   문서를 근거로 쓴다** — 이 규칙을 새 레포 CLAUDE.md 최상단에 박는다 (아래 템플릿 참고)

## 1. 프로젝트 생성

```bash
npx create-expo-app@latest <app-name> --template blank-typescript   # 템플릿 목록은 최신 문서에서 확인
cd <app-name> && git init  # create-expo-app이 이미 했으면 생략
```

`app.json` 필수 세팅: `name`/`slug`, `ios.bundleIdentifier`·`android.package`(HARNESS.md 번들ID),
`scheme`(딥링크), `runtimeVersion: { "policy": "fingerprint" }` (OTA 안전판정의 전제 — deploy가
이 정책에 의존), `updates.url`은 EAS 프로젝트 생성 후 자동 주입.

## 2. 검증된 컨벤션 이식 (petstagram에서 배운 것들)

### 부트스트랩 순서 (어기면 런타임에서만 터짐)
`index.ts`(엔트리) **최상단**에서, 다른 어떤 import보다 먼저:
```ts
import 'react-native-get-random-values';  // crypto 폴리필 — uuid/supabase-js 전제
import 'react-native-gesture-handler';    // 제스처 — 최상단 아니면 조용히 오동작
```
(해당 패키지를 쓰는 경우에만. 단 supabase를 쓸 계획이면 처음부터 넣어라.)

### env 규약
- 클라이언트 노출 설정은 전부 `EXPO_PUBLIC_*`. `.env` + `.env.example`(키만, 값 비움) 커밋.
- **설정 없다고 throw 금지**: 클라이언트 초기화는 placeholder 폴백 + `hasConfig` 게이트로.
  잘못 빌드돼도 화이트스크린 대신 기능만 꺼지게.
- EAS 빌드엔 `eas.json`의 프로파일별 `env` 블록으로 주입 (cicd 단계에서).

### 테스트: pure-core + thin-IO
- jest-expo 프리셋 + `npm test` / `npm run test:watch` / `npm run typecheck`(`tsc --noEmit`) 스크립트.
- **로직은 순수 함수로 뽑아 `*.test.ts`와 함께** (`lib/`, `utils/`), 컴포넌트/IO는 얇게.
  날짜·타임존, 그룹핑, 권한 판정 같은 것은 절대 컴포넌트 인라인으로 쓰지 않는다.
- tsconfig `strict: true`.

### DevMenu 패턴 (QA 필수)
`__DEV__` 게이트 플로팅 개발 패널을 처음부터 만든다. 규칙:
> **손으로 재현하기 힘든 상태 의존 UI(원타임 코치마크, 온보딩, "처음 N회" 힌트, 시간/카운트 게이트
> 화면)는 같은 변경 안에 DevMenu 리셋 액션을 함께 넣는다.** 원타임 플래그는 한 레지스트리
> (`lib/coachMarks.ts` 식: `COACH_KEYS` + `resetAllCoachMarks()`)에 모아 자동 리셋되게.

또 하나: 시뮬레이터엔 카메라가 없고 스토어 스크린샷엔 데모 데이터가 필요하다 →
**시드 데이터 액션**(`seedDemoEntries()` 식: 번들 샘플 에셋을 실데이터처럼 주입)을 DevMenu에
넣어두면 store-assets 단계가 그대로 쓴다.

### 디자인 시스템 자리 잡기
`theme/tokens.ts` 파일만 골격으로 생성(색/타이포/스페이싱 + `withOpacity(color, a)` 헬퍼 — 수동
rgba 복사 금지 규칙). 실제 값 채우기는 design 단계. **인라인 hex 금지** 규칙을 CLAUDE.md에.

## 3. dev client vs Expo Go 판정

HARNESS.md의 "네이티브 기능" 결정으로 판단:
- **Expo Go로 충분**(순수 JS/기본 모듈만): `npm start` 안내로 끝.
- **dev client 필요**(Apple Sign-In, 위젯, 커스텀 네이티브 모듈): 로컬 iOS 빌드는 Xcode 버전이
  SDK 요구와 맞아야 한다(안 맞으면 빌드 자체가 실패 — 확인: 최신 문서의 iOS 요구사항).
  **로컬이 안 되면 EAS로**: `eas build --profile development` (프로파일은 cicd에서 정식 세팅,
  여기선 `eas init` + 최소 development 프로파일만).

## 4. 새 레포 CLAUDE.md 생성

아래 뼈대로 생성 (프로젝트 사정에 맞게 채움):

```markdown
# CLAUDE.md

## Critical: Expo SDK <N>
이 앱은 Expo SDK <N> (RN <x>, React <y>). Expo API는 SDK마다 크게 바뀐다.
**Expo/RN 코드를 쓰기 전에 반드시 https://docs.expo.dev/versions/v<N>.0.0/ 버전 고정 문서를 읽어라.**
기억에 의존하지 마라.

(한국어 앱이면) 소스 주석·커밋 메시지는 한국어. 기존 파일 수정 시 컨벤션을 따르라.

## Commands
npm start / npm run ios / npm test / npm run test:watch / npm run typecheck
npx jest <file> / npx jest -t "<name>"

## Conventions
- 로직은 순수 함수 + .test.ts (pure-core + thin-IO). 컴포넌트 인라인 로직 금지.
- theme/tokens.ts가 색/타이포/스페이싱 단일 소스. 인라인 hex 금지. 투명도는 withOpacity().
- 상태 의존 UI(코치마크/온보딩/원타임)는 DevMenu 리셋 액션과 같은 변경으로.
- env는 EXPO_PUBLIC_*, 설정 누락 시 throw 금지(placeholder + 게이트).
- (백엔드 있으면) 마이그레이션은 append-only — 기존 항목 수정/삭제 금지.

## Architecture
<앱 구조 설명 — 스캐폴드 후 실제 구조 반영>
```

## 5. 검증 + 마무리

- `npm run typecheck && npm test` 통과 확인. iOS 시뮬레이터(또는 웹)로 첫 화면 렌더 확인.
- **HARNESS.md 업데이트**: scaffold 체크, SDK 버전 확정 기록, 로그 한 줄.
- 생성된 것을 한 줄 보고하고 **`/gapp:design`을 바로 이어서 실행한다** (이어달리기 규칙 — 멈추고
  다음 명령을 기다리지 않는다).
