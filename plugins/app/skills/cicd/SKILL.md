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
| push/PR → main | `ci.yml` | typecheck + jest + expo-doctor(정보성) | 불필요 |
| push → main (앱 코드) | `eas-update.yml` | `eas update --auto` (OTA) | `EXPO_TOKEN` |
| push → main (`supabase/**`) | `supabase-deploy.yml` | `db push` + `functions deploy` | Supabase 2종 |
| tag `v*` push | `eas-build.yml` | production 빌드 iOS+Android + `--auto-submit` | `EXPO_TOKEN` + 제출 자격증명 |
| 수동 (Run workflow) | `eas-build.yml` | 프로파일/플랫폼 선택 빌드 | 〃 |

이렇게 가르는 이유: OTA는 초단위·무료지만 네이티브를 못 바꾸고, 네이티브 빌드는 20~40분+크레딧.
그래서 **JS 변경은 main 푸시로 즉시, 네이티브는 릴리스 태그로만** 빌드한다.

**기본 흐름은 직푸시**: 작업 → 버전업 → `git push origin main`이면 Actions가 CI+OTA를 자동 처리한다.
직푸시해도 `ci.yml`은 그대로 돈다(§2, push·PR 둘 다 트리거). PR·브랜치는 강제가 아니라, 팀이 붙거나
회귀 위험이 클 때 켜는 선택지다(§3 브랜치 보호). 검증용으로 PR을 일부러 만들 필요 없다.

## 1. eas.json 프로파일

`eas init` 후 프로파일 구성 (버전 필드는 최신 EAS CLI 문서 확인):

- `development`: `developmentClient: true`, `distribution: internal`, `channel: development`
- `preview-simulator`: `extends: development` + `ios.simulator: true`
  — **store-assets의 스크린샷 파이프라인이 이 프로파일에 의존한다. 빼먹지 말 것.**
- `preview`: internal 배포용, `channel: preview`
- `production`: `autoIncrement: true`, `channel: production`
- 각 프로파일 `env` 블록에 `EXPO_PUBLIC_*` 주입 (백엔드 있으면 URL/anon key)
- 각 프로파일 `env`에 `APP_VARIANT`(development/preview/production) 주입 — scaffold의 `app.config.js`와
  짝을 이뤄 변형별 번들 ID 공존을 만든다. `preview-simulator`는 development 상속으로 자동 해결
- `node` 버전을 프로파일에 고정하고 **같은 값을 워크플로 NODE_VERSION에** 쓴다
- `submit.production`: iOS `appleTeamId`/`ascAppId`(ASC 앱 레코드 생성 후), Android 서비스계정 경로
- `cli.appVersionSource: "remote"` — 빌드 번호를 EAS가 관리

## 2. 워크플로 설치

이 스킬 디렉토리의 `references/` 워크플로 4개를 `.github/workflows/`로,
`check-ota-compat.mjs`는 `scripts/`로 복사 후 치환:

- `ci.yml`, `eas-update.yml`, `eas-build.yml`: `NODE_VERSION` → eas.json과 동일 값
- `supabase-deploy.yml` (백엔드 있을 때만): `SUPABASE_PROJECT_REF`, `EDGE_FUNCTION_NAME` 치환
  (함수 없으면 해당 step 삭제)
- 모노레포/웹 디렉토리가 있으면 `ci.yml`·`eas-update.yml`의 paths-ignore에 추가
- 템플릿 헤더의 `[템플릿]` 주석 줄은 치환 후 삭제
- `eas-update.yml`은 OTA를 러너에서 로컬 평가하므로 eas.json env가 안 먹는다 → 템플릿이 job에
  `env.APP_VARIANT: production`을 박아둔다(fingerprint 런타임 버전이 프로덕션 빌드와 일치해야 업데이트
  적용). 변형/번들ID 규칙을 바꿨으면 이 값도 같이 확인
- `check-ota-compat.mjs`는 치환값 없음 — 그대로 복사(§2.5가 이걸 쓴다)
- 가능하면 `actionlint`로 YAML 검증

템플릿이 오래됐을 수 있다 — action 메이저 버전(expo-github-action, setup-node 등)이 의심되면
최신 문서 확인. `expo:expo-cicd-workflows` 스킬이 있으면 EAS 자체 워크플로(.eas/workflows) 방식과
비교 검토해도 좋다 (기본은 GitHub Actions — 레포 보호규칙·시크릿·타 잡과의 결합이 쉬움).

## 2.5. 네이티브 변경과 OTA — 지문이 갈리면 기존 유저가 끊긴다

`runtimeVersion: fingerprint`(scaffold 기본)에서는 **네이티브에 영향을 주는 변경이 main에 들어가는
순간 그 이후 모든 OTA가 현재 스토어 유저를 건너뛴다.** 새 빌드가 심사를 통과하고 유저가 앱을
업데이트할 때까지. 조용히 일어나는 게 진짜 문제다 — 모르면 그 구간에 머지한 픽스가 전부 유실된다.

`scripts/check-ota-compat.mjs`가 현재 지문을 최신 production 빌드의 `runtimeVersion`과 비교해
두 군데서 알려준다: **PR**(`ci.yml`의 `OTA 호환 (정보성)`)과 **머지 후**(`eas-update.yml` 게시 직전).
직푸시 흐름이면 후자만 돈다.

**둘 다 게이트가 아니라 알림이다(항상 exit 0).** 일부러 실패시키지 말 것 — PR을 상주 감시하며 CI
실패를 자동으로 고치는 에이전트가 붙어 있으면 정당한 네이티브 변경을 되돌려버린다. 판단은 사람이:

1. **지금 릴리스할 게 아니면 머지를 미룬다.** PR을 열어둔 채 두면 그동안 다른 JS 변경은 계속 OTA로
   나간다. 릴리스하기로 한 날 머지하고 곧바로 `v*` 태그를 민다.
2. **릴리스할 거면 창을 짧게.** 머지 → 태그 → 빌드/제출을 붙여서. 머지만 해놓고 방치하면 그 사이
   픽스가 전부 기존 유저에게 유실된다.
3. **창 안에 긴급 픽스가 필요하면 백포트.** 스토어에 나가 있는 커밋에서 브랜치를 따 픽스만
   cherry-pick하고, `eas-update.yml`을 **Run workflow**로 실행하며 `ref`에 그 브랜치를 넣는다.
   구 지문 업데이트가 EAS 브랜치 `main`에 하나 더 얹히고, 클라이언트는 자기 런타임에 맞는 최신을
   받으므로 두 런타임이 공존한다. 로컬에서 직접 `eas update` 하지 말 것(env 주입이 빠진다).

지문을 바꾸는 것들: `app.json`/`app.config.js`, `package.json` 의존성, config plugin, 네이티브 타깃
소스, `eas.json`, 아이콘·스플래시 에셋.

> 자율 에이전트(loop/워커)가 이 레포에 붙어 있다면 **그 지침에도 같은 규칙을 명시**해야 한다 —
> "머지 = 배포"를 가정하고 네이티브 변경을 그냥 구현해 PR을 올린다. 릴리스 타이밍은 사람 판단이다.

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
- [ ] **main 브랜치 보호 (선택 — 기본은 끄고 직푸시)** — 혼자 빠르게 갈 땐 보호 없이
  `git push origin main`이 기본 흐름이다. 팀이 붙거나 회귀 위험이 커지면 그때 켜서 PR+CI 통과를
  머지 조건으로 걸어라 — 배포 워크플로는 push→main에 바로 반응하므로 이때 실질 게이트가 된다.

## 4. 검증

```bash
npm run typecheck && npm test && npx expo-doctor   # CI와 동일 명령 로컬 확인
```
- main에 직푸시 → Actions에서 CI 통과 확인 (검증용 PR 따로 만들 필요 없다; 원하면 PR로도 가능)
- 사소한 앱 코드 변경을 main 푸시 → `eas branch:view main`에 업데이트 게시 확인
- (백엔드) supabase/** 변경 머지 → db push 로그 확인, 스모크 테스트 스크립트 실행
- 첫 네이티브 빌드는 태그 대신 `workflow_dispatch`(submit=false)로 안전하게 리허설 가능

## 5. 마무리

- 새 레포 CLAUDE.md에 "빌드는 EAS로, 배포는 main push=OTA / v* 태그=빌드" 요약 추가.
- `docs/CICD.md`를 레포에 생성(위 트리거 맵 + 시크릿 표 + 체크리스트를 그 프로젝트 값으로).
- HARNESS.md: cicd 체크, 미완 항목(제출 자격증명 등) TODO 기록, 로그.
- 한 줄 보고 후 **`/gapp:analytics`를 바로 이어서 실행한다** (이어달리기 규칙 — 배포 경로가
  생겼으니 이제 배포된 것을 볼 눈을 붙일 차례다). 이후는 개발 루프: 배포할 일이 생기면
  `/gapp:deploy`, 릴리스 전엔 `/gapp:preflight`.
