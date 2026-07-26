---
name: analytics
description: >-
  gapp 하네스 5단계 — PostHog 계측(제품분석 + 에러트래킹 + 구조화 로그)을 웹(Next.js)과
  앱(Expo)에 한 벌로 깐다. 광고차단 우회 리버스 프록시, 앱↔웹 person 통일, 서버·워커
  플러시 규율, 소스맵 업로드, 그리고 **PostHog에 실제로 도착했는지 MCP로 질의해 확인**하는
  검증까지 포함한다. "포스트호그 붙여줘", "analytics 붙이자", "에러트래킹", "로그 수집",
  "sentry 대신 뭐 쓰지", "계측" 요청이나 cicd 직후 다음 단계로 이 스킬을 써라.
  PostHog MCP가 붙어 있으면 그걸로 프로젝트 상태를 읽고 검증한다.
---

# /gapp:analytics — PostHog 계측 (분석 + 에러 + 로그)

전제: 앱이 돌아가고 배포 경로가 있다(cicd 완료). 계측은 **배포된 뒤 눈이 되는 단계**다.

목표는 셋을 한 벌로 붙이는 것이다 — 제품분석(무엇을 쓰는가), 에러트래킹(무엇이 깨지는가),
로그(왜 깨졌는가). 셋을 따로 붙이면 사람·세션이 안 이어져서 "이 사용자가 이 에러를 맞았다"를
못 본다. PostHog 하나로 가는 이유가 그거다.

**관통 원칙: 계측이 제품을 막지 않는다.** 키가 없으면 계측만 꺼지고 앱은 그대로 돈다.
계측 설정 실패로 빌드가 깨지거나 화면이 안 뜨면 순서가 뒤바뀐 것이다.

## 0. 프로젝트 확보 (먼저 확인 — 여기서 막힌다)

PostHog MCP가 있으면 `projects-get`으로 기존 프로젝트를 본다.

**무료 플랜은 프로젝트 1개다.** 두 번째를 만들려면 카드 등록이 필요하다 —
에이전트가 대신 결제하지 않는다. 유저에게 알리고 둘 중 하나를 고르게 한다:

- **기존 프로젝트 공유** (기본): 모든 이벤트에 `product: '<앱슬러그>'` 슈퍼 속성을 박고,
  **모든 인사이트를 그 속성으로 거른다.** 이걸 빼면 퍼널·리텐션이 남의 앱 이벤트까지
  세어 숫자가 통째로 틀린다. 나중에 프로젝트를 나눠도 이 속성은 남겨두면 무해하다.
- **유료 전환 후 새 프로젝트**: 유저가 직접 카드 등록.

토큰(`phc_...`)은 쓰기 전용이라 클라이언트 노출이 정상이다. 개인 API 키(`phx_...`)와 헷갈리지 마라 —
소스맵 업로드에만 쓰이고 절대 클라이언트에 넣지 않는다.

## 1. 설정 모듈 — env는 **반드시 지연 평가**

`lib/analytics/config.ts` 하나에 값을 모으되, **상수가 아니라 함수로** 내보낸다.

```ts
export function posthogKey() { return process.env.NEXT_PUBLIC_POSTHOG_KEY ?? '' }
export function posthogEnabled() { return posthogKey().length > 0 }
export const PRODUCT = '<앱슬러그>'   // 앱 쪽 사본과 같은 값이어야 한다
```

*이게 취향 문제가 아니다.* 워커 스크립트는 이렇게 시작한다:

```ts
import { config } from 'dotenv'
config({ path: '.env.local' })        // ← .env를 읽는 시점
import { runIngest } from '../src/...'
```

`import`는 호이스팅된다. 설정 모듈이 **최상단에서** `process.env`를 읽으면 dotenv보다 먼저
읽어 항상 빈 문자열이 된다. 그러면 수집·알림 워커의 계측이 **아무 에러 없이 통째로 꺼진 채**
돈다. 브라우저에서는 잘 되니까 원인을 엉뚱한 데서 찾게 된다. 함수로 감싸면 호출 시점에 읽는다.
`NEXT_PUBLIC_*`는 위치와 무관하게 번들러가 치환하므로 브라우저도 그대로 동작한다.

## 2. 웹 클라이언트 (Next.js App Router)

```bash
pnpm add posthog-js @posthog/react posthog-node
```

**`src/instrumentation-client.ts`** (Next 15.3+ 규약)에서 init 한다. `providers.tsx`의
`useEffect`에서 init 하면 **하이드레이션 구간이 통째로 빈다** — 그 구간 에러를 못 잡는다.

```ts
posthog.init(posthogKey(), {
  api_host: '/ingest',            // 프록시 (3절)
  ui_host: 'https://us.posthog.com',
  defaults: '2026-05-30',
  capture_exceptions: {
    capture_unhandled_errors: true,
    capture_unhandled_rejections: true,
    capture_console_errors: false,  // 켜면 서드파티 경고가 $exception이 되어 진짜 버그를 묻는다
  },
  disable_session_recording: true,  // 5절 참고
  person_profiles: 'identified_only',
  logs: { serviceName: '<앱>-web', environment, captureConsoleLogs: false },
  loaded: (ph) => ph.register({ product: PRODUCT, app_surface: surface() }),
})
export function onRouterTransitionStart(url, type) { /* 라우팅 로그 */ }
```

`providers.tsx`는 init이 아니라 **컨텍스트 제공 + 신원 연결**만 한다 (`<PHProvider client={posthog}>`).

**리셋 함정:** 로그아웃 처리로 `posthog.reset()`을 무조건 부르면 안 된다. 그 effect는 비로그인
방문자의 **모든 페이지 로드**에서 돌기 때문에, 익명 distinct_id가 매번 새로 발급된다. 한 사람이
세 페이지를 보면 방문자 3명으로 잡히고 익명 퍼널이 첫 단계에서 끊긴다.

```ts
if (!userId) { if (posthog._isIdentified()) posthog.reset(); return }
posthog.identify(userId, email ? { email } : undefined)
```

식별자는 **인증 시스템의 user id**를 쓴다. 이메일을 distinct_id로 쓰면 이메일 변경 시 다른
사람이 되어 이력이 끊긴다.

## 3. 리버스 프록시 — 안 하면 조용히 0건이 된다

`us.i.posthog.com`으로 직접 보내면 광고차단기가 막는다. 막혀도 SDK는 조용히 실패해서
"붙였는데 데이터가 없다"로만 보인다. `next.config.ts`:

```ts
async rewrites() {
  return [
    { source: '/ingest/static/:path*', destination: 'https://us-assets.i.posthog.com/static/:path*' },
    { source: '/ingest/:path*',        destination: 'https://us.i.posthog.com/:path*' },
  ]
},
skipTrailingSlashRedirect: true,   // 없으면 /ingest/e/ 로 308 → SDK가 안 따라가 이벤트 증발
```

경로가 둘인 이유: 이벤트는 `us.i`, 지연 로드 번들은 `us-assets.i`로 **호스트가 다르다.**

**미들웨어 matcher에서 `ingest`를 반드시 뺀다.** 안 빼면 이벤트 하나마다 세션 갱신
(Supabase 토큰 검증 등)이 한 번씩 돌아, 분석을 붙인 대가로 인증 호출이 페이지뷰 수만큼 늘어난다.

검증: `curl -o /dev/null -w "%{http_code}" http://localhost:PORT/ingest/static/array.js` → 200.

## 4. 서버·워커 (posthog-node + OTel 로그)

**이벤트/예외**는 `posthog-node`. 서버리스는 언제든 얼어붙으므로 `flushAt: 1, flushInterval: 0`,
`enableExceptionAutocapture: true`.

**서버 예외의 진입점은 `src/instrumentation.ts`의 `onRequestError`**다. 이게 없으면 서버 컴포넌트·
라우트 핸들러 에러는 사용자 화면의 500으로만 남는다 — 브라우저 SDK는 서버 예외를 볼 수 없다.
Edge 런타임에서는 posthog-node가 안 올라가므로 `process.env.NEXT_RUNTIME !== 'nodejs'`면
early return 하고, import는 함수 안에서 동적으로 한다(최상단 import는 미들웨어 번들을 깨뜨린다).

**로그**는 다르다. Node SDK에는 `posthog.logger`가 **없다**. OTLP로 직접 보낸다:

```bash
pnpm add @opentelemetry/api-logs @opentelemetry/sdk-logs \
         @opentelemetry/exporter-logs-otlp-http @opentelemetry/resources
```

`@opentelemetry/sdk-node`는 쓰지 마라 — 자동계측까지 딸린 큰 묶음인데 필요한 건 배치 전송뿐이다.
`LoggerProvider` + `BatchLogRecordProcessor` + `OTLPLogExporter(url: <host>/i/v1/logs`,
`headers: { Authorization: 'Bearer phc_...' })`를 직접 조립한다.

> **PostHog 문서 예제가 낡았다.** `new BatchLogRecordProcessor(exporter)`로 적혀 있는데
> 최신 OTel은 **옵션 객체**를 받는다: `new BatchLogRecordProcessor({ exporter })`.
> 위치 인자로 넘기면 런타임에 exporter가 undefined가 되어 로그가 한 줄도 안 나간다.
> 설치된 패키지의 `.d.ts`를 직접 확인하고 쓴다.

콘솔 출력을 **없애지 않는다.** 원격에만 있는 로그는 워커를 터미널에서 고치는 속도를 떨어뜨린다.

**플러시 규율 (일회성 스크립트의 필수 조건):**

```ts
void main()
  .catch((err) => { captureServerException(err, { script: 'ingest' }); process.exitCode = 1 })
  .finally(async () => { await Promise.all([closeDb(), shutdownPostHog(), shutdownServerLogs()]) })
```

`await` 없이 끝내면 프로세스가 먼저 죽어 **하필 알고 싶은 그 마지막 에러가 증발한다.**
`onRequestError`에서도 응답 후 인스턴스가 얼어붙으므로 같은 이유로 flush 한다.

**크론 워커는 실행 결과를 매번 이벤트로 남긴다.** 수집이 0으로 떨어진 날을 나중에 찾을 수
있어야 한다 — 아무도 안 볼 때 실패하고, 사용자는 신고하지 않는다.

## 5. 앱 (Expo) — 웹뷰 껍데기인지 먼저 판단

```bash
npx expo install posthog-react-native expo-file-system expo-application expo-device expo-localization
```

`expo-localization`은 **config plugin 등록이 필요하다** (`app.json`의 `plugins`). 빠지면 빌드가 깨진다.

**앱이 웹뷰 껍데기라면** 화면 조회·터치 계측을 반드시 끈다:

```tsx
<PostHogProvider client={posthog} autocapture={{ captureScreens: false, captureTouches: false }}>
  <PostHogErrorBoundary><App /></PostHogErrorBoundary>
</PostHogProvider>
```

웹뷰 안의 행동은 `posthog-js`가 이미 잡는다. 여기서 또 잡으면 같은 클릭이 두 번 센다.
앱은 **앱만 아는 것**만 보낸다: 생명주기, 푸시 권한 결과, JS 크래시,
그리고 **웹뷰 로드 실패**(`onError`/`onHttpError`) — 이건 웹 코드가 돌기 전이라
`posthog-js`가 절대 볼 수 없는데, 못 보면 "앱이 흰 화면이에요"의 원인을 영영 모른다.

**앱↔웹 person 통일 (웹뷰 앱의 필수 작업):** 세션은 웹만 갖고 있으므로 앱은 사용자가 누군지
모른다. 그대로 두면 한 사람이 두 person으로 갈려 앱 사용자 수가 두 배로 보이고, 앱 크래시가
그 사용자에게 안 붙는다. 브릿지에 `identifyAnalytics(userId | null)` 메서드를 하나 추가해
웹이 로그인/로그아웃 시 앱에 알린다. 브릿지 프로토콜 사본이 둘이면 **양쪽 + injected + handlers를
함께 고치고 버전을 올린다.**

**콜드 스타트 푸시 중복 주의:** 앱이 꺼진 상태에서 푸시로 들어오면 웹뷰가 아직 없어 브릿지
이벤트를 못 쏜다. 그 경로만 앱이 직접 세고(`cold_start: true`), 웜 경로는 웹이 센다.
양쪽 다 세면 두 배가 되고, 양쪽 다 안 세면 콜드 스타트가 통째로 누락된다.

**앱 토큰은 웹과 같은 프로젝트 토큰**을 쓴다. 다르면 앱 크래시와 그 사용자의 웹뷰 행동을 못 잇는다.

## 6. 세션 리플레이 — 기본은 끄고 물어본다

민감정보(소득·자산·주민번호성 입력·건강)를 다루는 화면이 하나라도 있으면 **끄고 시작한다.**
유저에게 물어라. 켤 거면 마스킹 설정(`maskAllInputs`, 민감 화면 텍스트 마스킹)을
**먼저 잡고** 켠다. 나중에 지우는 것보다 안 찍는 게 싸다.

## 7. 소스맵 — 없으면 에러트래킹이 무용지물

`t.js:1:24601`로만 남는 스택트레이스는 없는 것과 같다. `@posthog/nextjs-config`의
`withPostHogConfig`를 쓰되 **토큰이 있을 때만 감싼다:**

```ts
export default POSTHOG_CLI_TOKEN && POSTHOG_PROJECT_ID
  ? withPostHogConfig(nextConfig, { personalApiKey: ..., projectId: ...,
      sourcemaps: { enabled: true, deleteAfterUpload: true } })
  : nextConfig
```

항상 감싸면 토큰 없는 로컬·CI 빌드가 CLI 인증 실패로 통째로 깨진다.
`deleteAfterUpload`를 빼면 소스맵이 배포물에 남아 누구나 원본 코드를 받아볼 수 있다.
CI 시크릿(`POSTHOG_CLI_TOKEN`, `POSTHOG_PROJECT_ID`)은 `/gapp:cicd`가 깐 워크플로에 추가한다.

**키를 브라우저 자동화로 발급할 때 (실제로 물린 것들):**

- 스코프는 `error_tracking:write` + `organization:read` 둘이면 된다. 그리고
  `Organization & project access` 를 **`Projects` → 해당 프로젝트**로 좁혀야 한다. 이걸 안 고르면
  `Create key` 버튼이 **비활성인 채로 이유를 안 알려준다** — 라벨·스코프를 다 채워놓고 왜 안 눌리는지
  한참 찾게 된다. 검증 메시지도 안 뜬다.
- 스코프 목록은 수십 줄이다. 검색창(`Search scopes...`)으로 한 행만 남긴 뒤 클릭한다. 전체 목록에서
  ref나 좌표로 찍으면 스크롤 위치에 따라 빗나가고 **조용히 아무 일도 안 일어난다.** 누른 뒤
  `.LemonSegmentedButton__option--selected` 로 실제 선택값을 확인한다 — 스크린샷으로 눈으로도 본다.
- 그 검색창에 `fillInput` 은 기존 값을 **덮지 않고 이어붙인다.** X 버튼으로 비우고 `typeText` 한다.
- 회사/개인 계정이 갈려 있으면 브라우저가 엉뚱한 org로 붙는다 → `gbase:ego-profile`.
- 발급 화면은 **재인증**을 요구한다. 비밀번호·OAuth는 유저 몫이므로 그 지점에서 넘긴다.
- 키는 **생성 직후 한 번만** 보인다. 읽는 즉시 `.env.local` 에 쓰고 로그·채팅에 값을 남기지 않는다.

## 8. 이벤트 택소노미 — 문자열을 직접 쓰지 않는다

`lib/analytics/events.ts`에 상수로 모은다. 호출부에서 문자열을 쓰면 `alert_saved`와
`alert_save`가 동시에 생기고, PostHog에서는 **서로 다른 이벤트라 퍼널이 조용히 반토막 난다.**
오타는 대시보드를 만들 때가 되어서야 드러난다. 이름은 `명사_과거분사`.

**속성에 민감값을 넣지 마라.** "무엇을 걸렀는가"가 아니라 "몇 개를 걸렀는가"를 센다.
소득 구간이 이벤트 속성으로 나가면 그건 그 사람의 재정 상태다.

세는 건 이 앱의 **핵심 전환 경로**다 — 그 제품이 존재하는 이유에 해당하는 행동을 반드시 하나
포함시킨다. 그게 안 쓰이면 제품 가설이 틀린 것이고, 세지 않으면 그걸 알 수 없다.

## 9. React 렌더 에러 — `capture_exceptions`로는 못 잡는다

React가 렌더 에러를 먼저 붙잡아 에러 경계로 넘기므로 `window.onerror`까지 안 올라온다.
`app/global-error.tsx`를 만들어 `posthog.captureException`을 부른다. 이게 없으면
"화면이 하얗게 됐어요"가 **한 건도 안 남는다.** `global-error`는 루트 레이아웃까지 대체하므로
`html`/`body`를 직접 그려야 하고, 디자인 토큰이 없다고 가정하고 최소한으로 만든다.

## 10. 검증 — "빌드가 됐다"는 검증이 아니다

계측은 조용히 실패하는 게 정상 동작처럼 보인다. **PostHog에 실제로 도착했는지 질의해서
확인한다.** MCP가 있으면 다섯 경로를 하나씩:

| 경로 | 확인 방법 |
|---|---|
| 웹 이벤트 + 슈퍼 속성 | `execute-sql`: `SELECT event, properties.product, properties.app_surface FROM events WHERE timestamp > now() - INTERVAL 20 MINUTE` |
| 웹 예외 | 브라우저에서 `setTimeout(() => { throw new Error('verify') })` → `$exception` 행 확인 |
| 서버 이벤트 + 예외 | 임시 스크립트로 `captureServerEvent`/`captureServerException` → `app_surface = 'server'` 행 확인 |
| 서버 로그 | `query-logs` with `serviceNames: ['<앱>-server']` |
| 브라우저 로그 | `query-logs` with `serviceNames: ['<앱>-web']` — `posthogDistinctId`/`sessionId`가 붙는지도 본다 |

**모든 행에 `product` 속성이 붙어 있는지 반드시 확인한다** (프로젝트 공유 중이면 이게 생명줄).
임시 검증 스크립트는 확인 후 지운다.

전 경로 통과 후: `pnpm exec tsc --noEmit` · 테스트 · lint · `next build` · `npx tsc --noEmit`(앱).

## 11. 마무리

- 새 레포 CLAUDE.md / AGENTS.md에 함정 셋을 적는다: **env 지연 평가**, **프록시+미들웨어 제외**,
  **스크립트 flush 규율**. 다음 사람이 되돌리려 드는 자리들이다.
- `.env.example`에 `NEXT_PUBLIC_POSTHOG_KEY`/`HOST`, 앱의 `EXPO_PUBLIC_POSTHOG_KEY`/`HOST`,
  소스맵용 `POSTHOG_CLI_TOKEN`/`POSTHOG_PROJECT_ID`를 주석과 함께 추가.
- 프로젝트를 공유 중이면 **"모든 인사이트는 `product` 로 거를 것"** 을 문서에 남긴다.
- HARNESS.md: analytics 체크, 프로젝트 id/토큰 위치·공유 여부·리플레이 on/off 결정 기록, 로그.
- 한 줄 보고 후 **`/gapp:landing`을 바로 이어서 실행한다** (이어달리기 규칙).
