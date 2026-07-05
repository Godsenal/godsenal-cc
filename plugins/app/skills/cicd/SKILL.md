---
name: cicd
description: >-
  gapp 하네스 4단계 — GitHub Actions + EAS로 CI/CD 파이프라인 구성. "main 머지 = CI + OTA(+Supabase
  배포), v* 태그 = 네이티브 빌드 + 스토어 자동제출" 구조를 워크플로 템플릿 4종으로 깔고, eas.json
  프로파일, 시크릿 등록, 채널↔브랜치 링크, 브랜치 보호까지 1회 셋업 체크리스트를 완주시킨다.
  "CI/CD 세팅", "깃헙 액션", "자동배포 파이프라인", "eas workflow" 요청이나 backend 직후 다음 단계로
  이 스킬을 써라. 이후 실제 배포 실행/판단은 deploy가 담당한다.
---

# /gapp:cicd — CI/CD 파이프라인 (GitHub Actions + EAS)

목표 구조 — **"완전 자동, 트리거만 사람"**:

| 이벤트 | 워크플로 | 동작 | 시크릿 |
|---|---|---|---|
| PR → main | `ci.yml` | typecheck + jest + expo-doctor(정보성) | 불필요 |
| push → main (앱 코드) | `eas-update.yml` | `eas update --auto` (OTA) | `EXPO_TOKEN` |
| push → main (`supabase/**`) | `supabase-deploy.yml` | `db push` + `functions deploy` | Supabase 2종 |
| tag `v*` push | `eas-build.yml` | production 빌드 iOS+Android + `--auto-submit` | `EXPO_TOKEN` + 제출 자격증명 |
| 수동 (Run workflow) | `eas-build.yml` | 프로파일/플랫폼 선택 빌드 | 〃 |

이렇게 가르는 이유: OTA는 초단위·무료지만 네이티브를 못 바꾸고, 네이티브 빌드는 20~40분+크레딧.
그래서 **JS 변경은 main 머지로 즉시, 네이티브는 릴리스 태그로만** 빌드한다.

## 1. eas.json 프로파일

`eas init` 후 프로파일 구성 (버전 필드는 최신 EAS CLI 문서 확인):

- `development`: `developmentClient: true`, `distribution: internal`, `channel: development`
- `preview-simulator`: `extends: development` + `ios.simulator: true`
  — **store-assets의 스크린샷 파이프라인이 이 프로파일에 의존한다. 빼먹지 말 것.**
- `preview`: internal 배포용, `channel: preview`
- `production`: `autoIncrement: true`, `channel: production`
- 각 프로파일 `env` 블록에 `EXPO_PUBLIC_*` 주입 (백엔드 있으면 URL/anon key)
- `node` 버전을 프로파일에 고정하고 **같은 값을 워크플로 NODE_VERSION에** 쓴다
- `submit.production`: iOS `appleTeamId`/`ascAppId`(ASC 앱 레코드 생성 후), Android 서비스계정 경로
- `cli.appVersionSource: "remote"` — 빌드 번호를 EAS가 관리

## 2. 워크플로 설치

이 스킬 디렉토리의 `references/` 템플릿 4개를 `.github/workflows/`로 복사 후 치환:

- `ci.yml`, `eas-update.yml`, `eas-build.yml`: `NODE_VERSION` → eas.json과 동일 값
- `supabase-deploy.yml` (백엔드 있을 때만): `SUPABASE_PROJECT_REF`, `EDGE_FUNCTION_NAME` 치환
  (함수 없으면 해당 step 삭제)
- 모노레포/웹 디렉토리가 있으면 `ci.yml`·`eas-update.yml`의 paths-ignore에 추가
- 템플릿 헤더의 `[템플릿]` 주석 줄은 치환 후 삭제
- 가능하면 `actionlint`로 YAML 검증

템플릿이 오래됐을 수 있다 — action 메이저 버전(expo-github-action, setup-node 등)이 의심되면
최신 문서 확인. `expo:expo-cicd-workflows` 스킬이 있으면 EAS 자체 워크플로(.eas/workflows) 방식과
비교 검토해도 좋다 (기본은 GitHub Actions — 레포 보호규칙·시크릿·타 잡과의 결합이 쉬움).

## 3. 1회 셋업 체크리스트 (사람 손 필요한 것 — 하나씩 확인받기)

- [ ] **GitHub 시크릿 등록** (Settings › Secrets and variables › Actions):
  - `EXPO_TOKEN` — expo.dev › Access tokens (robot 토큰 권장)
  - `SUPABASE_ACCESS_TOKEN` — supabase.com › Account › Access Tokens (백엔드 있을 때)
  - `SUPABASE_DB_PASSWORD` — 프로젝트 › Settings › Database (백엔드 있을 때)
  - Variables 탭에 `SUPABASE_PROJECT_ID` (선택 — fallback 하드코딩 대신)
- [ ] **production 채널 ↔ main 브랜치 링크** — 없으면 OTA가 게시돼도 앱에 안 내려간다:
  `eas channel:edit production --branch main` (브랜치 없으면 `eas branch:create main` 먼저)
- [ ] **스토어 제출 자격증명**: iOS는 ASC API key를 EAS에 업로드(`eas credentials`), Android는
  Play 서비스계정 JSON. **준비 전이어도 빌드는 성공하고 제출만 실패**하므로 뒤로 미뤄도 됨 —
  미룬 경우 HARNESS.md에 TODO로 남긴다.
- [ ] **main 브랜치 보호** — CI 통과를 머지 조건으로. 배포 워크플로는 push→main에 바로 반응하므로
  "검증 후 머지"의 실질 게이트는 브랜치 보호다.

## 4. 검증

```bash
npm run typecheck && npm test && npx expo-doctor   # CI와 동일 명령 로컬 확인
```
- 브랜치 하나로 PR → Actions에서 CI 통과 확인
- 사소한 앱 코드 변경을 main 머지 → `eas branch:view main`에 업데이트 게시 확인
- (백엔드) supabase/** 변경 머지 → db push 로그 확인, 스모크 테스트 스크립트 실행
- 첫 네이티브 빌드는 태그 대신 `workflow_dispatch`(submit=false)로 안전하게 리허설 가능

## 5. 마무리

- 새 레포 CLAUDE.md에 "빌드는 EAS로, 배포는 main push=OTA / v* 태그=빌드" 요약 추가.
- `docs/CICD.md`를 레포에 생성(위 트리거 맵 + 시크릿 표 + 체크리스트를 그 프로젝트 값으로).
- HARNESS.md: cicd 체크, 미완 항목(제출 자격증명 등) TODO 기록, 로그.
- 한 줄 보고 후 **`/gapp:landing`을 바로 이어서 실행한다** (이어달리기 규칙 — 스토어 제출에 필요한
  privacy URL을 미리 확보해두는 단계). 이후는 개발 루프: 배포할 일이 생기면 `/gapp:deploy`,
  릴리스 전엔 `/gapp:preflight`.
