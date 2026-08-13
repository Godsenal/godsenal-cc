---
name: deploy
description: >-
  Expo + EAS 앱의 배포 런북 — 코드 변경을 유저에게 내보내는 두 경로(OTA 코드 업데이트 vs 네이티브
  빌드+스토어 출시) 중 무엇이 맞는지 자동 판정하고, 해당 경로를 실행하고, 사람이 직접 해야 할 일
  (Apple 심사 제출 등)을 알려준다. "배포", "앱 출시", "스토어 올려", "릴리스", "deploy", "release",
  "OTA 내보내", "업데이트 배포", "TestFlight 올려", "태그 따서 배포", "유저한테 반영" 같은 말이
  나오면 반드시 이 스킬을 써라. 변경이 JS만인지 네이티브까지인지 애매할 때도 먼저 켜라.
  전제: cicd가 깔아둔 파이프라인(main push=OTA, v* 태그=빌드). 심사 제출 자동화는
  store-submit이 담당.
---

# /gapp:deploy — OTA vs 네이티브 빌드 배포 런북

배포 경로가 **두 개**고, 트리거·속도·"사람이 할 일"이 다르다. 핵심은 **"지금 이 변경엔 어느 경로가
맞는가"를 먼저 판정**하고 그 경로만 정확히 밟는 것.

**운영 방식은 "최대 자동화"다.** 열린 질문("어떻게 할까요?")으로 되묻지 말고 0~2단계(상태 점검·변경
판정·경로 결정)를 알아서 끝까지 수행한 뒤 결론과 실행 계획을 제시한다. 유저를 멈춰 세우는 지점은
**딱 하나** — 실제 배포를 트리거하는 명령(`git push origin main` / `git push origin v*` / 직접
`eas update`·`eas build`)을 날리기 **직전의 단일 확인 게이트**뿐. 그 외 읽기 전용 조사
(`eas ... view/list`, `git diff`, 태그 계산)는 확인 없이 진행.

## 출력 언어

사용자와의 대화 — 진행 보고, 요약, 체크리스트/판정 표, `AskUserQuestion`의 질문·헤더·옵션·설명 — 은 **한국어**로 쓴다. 하위 에이전트를 띄울 때도 결과가 사용자에게 그대로 노출되는 텍스트는 한국어로 돌려달라고 프롬프트에 적는다.

영어 그대로 두는 것: 코드·식별자·파일 경로·명령어·환경변수·워크플로 YAML·스킬/툴 이름, 고정 라벨과 상태 키워드(`PASS`/`FAIL`/`SKIP`, `✅`/`⚠️`), 그리고 커밋 메시지·브랜치 이름·PR 제목/본문 — 이건 대상 레포의 기존 관례를 따른다.

**앱 산출물은 이 규칙이 아니라 `kickoff`에서 정한 앱 언어(`docs/HARNESS.md`)를 따른다.** 앱 UI 문구, 랜딩 카피, 개인정보/지원 페이지, 스토어 메타데이터·스크린샷 문구는 전부 앱 언어로 — 영어 앱에 한국어 스토어 메타데이터를 넣지 않는다.

사용자가 다른 언어로 요청하면 그 언어를 따른다.

## 두 경로 한눈에

| 경로 | 트리거 | 무엇이 나가나 | 심사 |
|---|---|---|---|
| **A. OTA** | `main` push → eas-update.yml (`eas update --auto`) | JS/설정 번들이 이미 설치된 production 빌드에 다음 실행 때 반영 | 없음 |
| **B. 네이티브 빌드+출시** | `v*` 태그 push → eas-build.yml (빌드+`--auto-submit`) | 새 바이너리를 App Store Connect/Play에 업로드 | **있음(수동)** |

OTA는 몇 초·공짜지만 네이티브를 못 바꾼다. 빌드는 20~40분+크레딧이 들고 스토어를 거친다.

> CI 파이프라인이 없는 프로젝트면(워크플로 부재) 같은 판정 후 `eas update` / `eas build`를 직접
> 실행하는 걸로 대체하고, `/gapp:cicd` 세팅을 권한다.

## 0단계 — 배관 점검

```bash
eas channel:view production   # Branch: main 이어야 정상
```
production 채널이 main 브랜치를 가리켜야 OTA가 도달한다. 아니면
`eas branch:create main`(없을 때) → `eas channel:edit production --branch main`.
eas-cli outdated 경고는 무시 가능.

## 1단계 — 변경의 성격 판정 (OTA 가능한가?)

`app.json`의 `runtimeVersion.policy`가 `fingerprint`면, 네이티브 지문이 바뀐 변경은 OTA가 게시돼도
**옛 빌드엔 안 붙는다**. 마지막 production 빌드 커밋 이후 diff에서 아래 중 **하나라도** 걸리면
→ **네이티브 변경 = 빌드 필요**:

- `package.json`에 **네이티브 모듈** 추가/제거/버전업 (순수 JS 라이브러리는 무관)
- `app.json`/`app.config.*`의 네이티브 필드 — `plugins`, `ios`/`android`, `scheme`,
  `bundleIdentifier`, permissions/entitlements, 위젯·타깃 설정 등
- `ios/`, `android/`, `targets/` 네이티브 소스 변경
- Expo SDK / `react-native` 버전 변경

전부 `.ts/.tsx/.js`/이미지·JSON 에셋뿐이면 → **OTA로 충분**.

```bash
eas build:list --platform ios --limit 5 --non-interactive   # 직전 production 빌드 커밋 확인
git diff --stat <그_커밋>..HEAD                              # 이후 바뀐 파일
```

**애매하면 네이티브 변경으로 간주.** 잘못 OTA로 내보내면 새 JS와 옛 네이티브가 어긋나 크래시할 수
있다. 불필요한 빌드는 시간만 쓴다. 안전한 쪽 = 빌드.

## 2단계 — 경로 자동 결정 (묻지 않는다)

```bash
eas build:list --profile production --limit 3 --non-interactive
```
- production 빌드 **0개** → **경로 B**. OTA는 받을 대상이 없다. 첫 배포는 예외 없이 빌드.
- 네이티브 변경 판정 → **경로 B**.
- JS/에셋만 + production 빌드 존재 → **경로 A**.

정한 경로와 근거(무슨 파일이 바뀌어서)를 한 줄로 명시하고 3단계로. diff만으로 정말 못 가르는
극소수 경우에만 유저에게 묻는다.

## 3단계-A — OTA

main에 머지/푸시하면 워크플로가 자동으로 게시한다. **확인 게이트**: "무엇을 고쳤고 유저에게 어떻게
반영되는지" 한 줄 보여주고 확인받은 뒤 `git push origin main`.
푸시 후: Actions 성공 확인 → `eas branch:view main`에 업데이트 게시 확인.
반영 시점: 유저가 앱을 **다음에 열 때**(정확히는 그다음 실행) 적용됨을 보고에 명시.

## 3단계-B — 네이티브 빌드 + 출시

0. **`/gapp:preflight`를 먼저 돌린다** (코드·백엔드·설정 게이트 — 스토어 게이트는 심사 제출
   목적일 때만). FAIL이 있으면 고치거나 유저 판단을 받은 뒤 진행.
1. 버전 확인: `app.json`의 `version` 올릴지 판단(스토어 노출 버전). 빌드 번호는
   `autoIncrement`가 처리.
2. 태그 계산: 기존 태그 확인(`git tag -l 'v*'`) 후 다음 semver.
3. **확인 게이트**: "vX.Y.Z 태그 → production 빌드 iOS+Android + 스토어 업로드, 20~40분,
   크레딧 소모" 한 줄 확인 후:
   ```bash
   git tag vX.Y.Z && git push origin vX.Y.Z
   ```
4. 진행 확인: `eas build:list` 또는 EAS 대시보드.
5. **EAS는 빌드+업로드까지만 자동이다. App Store 심사 제출(Submit for Review)은 스토어에서
   따로 해야 한다** — 수동으로 하거나 `/gapp:store-submit`(Claude Chrome 자동화)을 안내.
   TestFlight 내부 테스트는 업로드 직후 심사 없이 바로 가능 — 실기기 확인은 여기서 먼저.
6. Android 제출 자격증명 미설정이면 iOS만 나간다는 걸 명시.

## 마무리 — 보고

**경로 / 실행한 명령 / 지금 상태 / 유저의 다음 할 일**을 짧은 목록으로. 특히 "사람이 직접 해야
하는 것"(심사 제출, 미설정 플랫폼)을 빠뜨리지 말 것. HARNESS.md 로그에 배포 기록 한 줄.

## 자주 나오는 실수 (피할 것)

- **네이티브 바뀐 걸 OTA로** → 옛 빌드에 안 닿거나 크래시. 1단계 판정 생략 금지.
- **채널 링크 확인 없이 OTA** → 엉뚱한 브랜치를 봐서 유저에게 안 닿음. 0단계 필수.
- **첫 출시 전에 OTA부터** → 받을 빌드가 없다. 첫 배포는 항상 경로 B.
- **태그 배포 후 "끝났다"고 보고** → 심사 제출이 남았다. 반드시 전달.
- **모든 플랫폼이 나갔다고 가정** → 제출 자격증명 세팅 상태를 확인하고 정확히 보고.
