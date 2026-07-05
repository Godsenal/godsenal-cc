---
name: preflight
description: >-
  릴리스/제출 직전 종합 점검 게이트 — "놓친 게 없나"를 사람 대신 기계적으로 훑는다. 코드 게이트
  (typecheck/test/expo-doctor/임시코드), 백엔드 게이트(Supabase advisors/RLS/스모크), 설정 게이트
  (버전/권한 문구/시크릿 유출), 스토어 게이트(privacy URL/스크린샷 규격/메타데이터 정합)를 검사해
  PASS/FAIL 표로 보고하고 자잘한 것은 고친다. "릴리스 준비됐나", "제출 전에 점검", "빠진 거 없나
  확인", "preflight", "출시 체크리스트" 요청에 쓰고, deploy(경로 B)와 store-submit이 시작 전에
  자동으로 이 스킬을 거친다.
---

# /gapp:preflight — 릴리스 전 종합 점검 게이트

하네스의 존재 이유가 "놓치는 게 없게"다 — 이 스킬이 그 마지막 그물. **읽기 전용 검사 + 자잘한
수리**만 하고, 결과를 PASS/FAIL/SKIP 표로 보고한다. FAIL이 있으면 배포/제출 스킬은 진행하지 않는다
(유저가 명시적으로 override하면 예외 — 표에 기록).

## 검사 항목

### 1. 코드 게이트
- [ ] `npm run typecheck && npm test -- --ci && npx expo-doctor` — CI와 동일 명령
- [ ] **임시 코드 잔존**: `SHOT_SCREEN`·화면 강제 오버라이드·하드코딩 좌표/딜레이·`console.log`
      덤프·주석처리된 블록이 diff에 남아있지 않은지 (`git diff main` + grep)
- [ ] dev 전용 코드(`DevMenu`, 시드)가 `__DEV__` 게이트 안에 있는지 — 스토어 빌드에 새면 리젝 사유
- [ ] 미커밋 변경 없이 깨끗한 트리인지 (배포는 커밋된 것만 나간다)

### 2. 백엔드 게이트 (supabase/ 있을 때만, 없으면 SKIP)
- [ ] Supabase advisors(security) — RLS 빠진 테이블, 노출 함수 없는지
- [ ] 새 security-definer RPC에 권한 선차단(`my_role() is null` 류)이 있는지 — 반복 실사고 패턴
- [ ] 클라우드 스모크 테스트 통과 (`scripts/cloud-integration-test.mjs` 류)
- [ ] `service_role` 키가 클라이언트 코드/env에 없는지 grep

### 3. 설정 게이트
- [ ] `app.json` `version` — 이번 릴리스에 올려야 하나? (스토어 노출 버전; 빌드번호는 autoIncrement)
- [ ] iOS 권한 문구(`infoPlist`의 `NS*UsageDescription`) — 새로 쓰기 시작한 권한에 문구가 있는지,
      문구가 실제 용도를 설명하는지 (형식적 문구는 리젝 사유)
- [ ] `.env`/시크릿이 커밋 이력에 새지 않았는지 (`git log -p -S` 샘플링 또는 `.gitignore` 확인)
- [ ] production 채널↔브랜치 링크 (`eas channel:view production`)

### 4. 스토어 게이트 (심사 제출 목적일 때만, 아니면 SKIP)
- [ ] privacy/지원 URL이 실제 200인지 (HARNESS.md 기록값 curl)
- [ ] 스크린샷 규격 (`sips -g pixelWidth -g pixelHeight`) + 장수
- [ ] `docs/APPSTORE-METADATA.md` ↔ 실제 앱 정합: 설명에 있는 기능이 다 작동하나, 수집 항목 답안이
      현재 SDK 구성과 맞나 (분석 SDK 추가됐는데 "수집 없음"이면 리젝)
- [ ] 로그인 필수 앱이면 심사용 데모 계정이 실제로 로그인되는지
- [ ] ASC에 처리 완료된 빌드가 있는지 (`eas build:list`)

## 출력

```
✈️ preflight — <앱이름> vX.Y.Z 후보
| 게이트 | 항목 | 결과 | 비고 |
...
결론: READY / NOT READY (FAIL n건 — <요약>)
```

- 자잘한 FAIL(임시코드 제거, 문구 추가 등)은 **고치고 재검사**한다 — 보고만 하고 떠넘기지 않는다.
- 구조적 FAIL(스키마 문제, 계정 문제)은 원인과 해결 경로를 명시.
- READY면 호출한 맥락으로 복귀: deploy가 불렀으면 배포 진행, store-submit이 불렀으면 제출 진행,
  단독 호출이면 "이제 `/gapp:deploy` 또는 `/gapp:store-submit` 가능"을 알리고 바로 이어간다.
