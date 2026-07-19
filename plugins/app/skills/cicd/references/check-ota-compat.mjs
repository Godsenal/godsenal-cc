#!/usr/bin/env node
/**
 * OTA 호환 점검 — 지금 트리의 네이티브 지문이 "스토어에 나가 있는 빌드"와 같은지 본다.
 * [템플릿] 그대로 `scripts/check-ota-compat.mjs`로 복사. 치환할 값 없음.
 *
 * runtimeVersion 정책이 fingerprint면, 네이티브에 영향을 주는 변경(app.json·의존성·config plugin·
 * targets/*.swift·아이콘/스플래시 등)이 들어가는 순간 지문이 갈린다. 갈린 뒤 main에서 나가는 OTA는
 * 기존 스토어 유저에게 **영원히** 안 내려간다 — 새 네이티브 빌드가 심사를 통과하고 그 유저가 앱을
 * 업데이트할 때까지. 문제는 이게 조용히 일어난다는 것이다: 알림이 없으면 그 구간에 머지된 픽스가
 * 통째로 기존 유저에게 유실된 줄도 모른 채 계속 쌓는다.
 *
 * 그래서 "지금 지문 == 최신 production 빌드의 runtimeVersion" 인지만 확인해 GitHub step summary에 적는다.
 *
 * **게이트가 아니라 알림이다 — 항상 exit 0.** 실패로 만들면 자동화 에이전트(예: PR을 상주 감시하며
 * CI 실패를 고치는 워커)가 정당한 네이티브 변경을 되돌리는 엉뚱한 수정을 낼 수 있다. 판단은 사람 몫.
 *
 * 로컬: node scripts/check-ota-compat.mjs   (EXPO_TOKEN 없으면 `eas login` 세션을 쓴다)
 */

import { execFileSync } from 'node:child_process';
import { appendFileSync } from 'node:fs';

// 지문은 플랫폼별로 나오지만 네이티브 변경은 대개 양쪽을 같이 건드린다 — iOS를 대표로 본다.
const PLATFORM = 'ios';

// app.config.js가 APP_VARIANT로 번들 ID·스킴을 분기하면 그 값이 지문에 들어간다. 프로덕션 빌드와
// 비교하는 게 목적이므로 여기서 못 박는다(워크플로에서 빠뜨려도 틀린 지문을 비교하지 않도록).
const env = { ...process.env, APP_VARIANT: 'production' };

/** stdout만 캡처하고 진행 로그(stderr)는 그대로 흘린다. --json 계열은 stdout이 순수 JSON이다. */
function capture(args) {
  return execFileSync('npx', args, {
    encoding: 'utf8',
    env,
    maxBuffer: 128 * 1024 * 1024, // fingerprint:generate는 소스 목록까지 뱉어서 수십 MB가 될 수 있다.
    stdio: ['ignore', 'pipe', 'inherit'],
  });
}

function report(lines) {
  const body = lines.join('\n');
  console.log(body);
  if (process.env.GITHUB_STEP_SUMMARY) appendFileSync(process.env.GITHUB_STEP_SUMMARY, `${body}\n`);
}

const localHash = JSON.parse(
  capture(['expo-updates', 'fingerprint:generate', '--platform', PLATFORM]),
).hash;

const builds = JSON.parse(
  capture([
    'eas', 'build:list',
    '--platform', PLATFORM,
    '--profile', 'production',
    '--status', 'finished',
    '--limit', '1',
    '--non-interactive', '--json',
  ]),
);

const shipped = builds[0];
if (!shipped) {
  report(['ℹ️ 비교할 production 빌드가 없다 — 점검 건너뜀.']);
  process.exit(0);
}

if (localHash === shipped.runtimeVersion) {
  report([
    `✅ **OTA 호환** — 이 변경은 스토어 빌드 \`v${shipped.appVersion}\`에 그대로 내려간다.`,
    '',
    `지문 \`${localHash}\``,
  ]);
} else {
  report([
    '### ⚠️ 네이티브 지문이 갈렸다 — OTA가 기존 유저에게 안 내려간다',
    '',
    `| | 지문 |`,
    `|---|---|`,
    `| 이 변경 | \`${localHash}\` |`,
    `| 스토어 빌드 \`v${shipped.appVersion}\` | \`${shipped.runtimeVersion}\` |`,
    '',
    '이대로 main에 들어가면 **이후 모든 OTA가 현재 스토어 유저를 건너뛴다.** 새 네이티브 빌드가',
    '심사를 통과하고 유저가 앱을 업데이트할 때까지.',
    '',
    '판단할 것:',
    '- **지금 릴리스할 게 아니면** 이 변경은 머지를 미룬다(PR을 열어둔 채 대기 → 릴리스 직전에 머지).',
    '  그동안 다른 JS 변경은 계속 OTA로 나간다.',
    '- **릴리스할 거면** 머지 직후 바로 `v*` 태그를 밀어 빌드·제출까지 이어간다. 창을 짧게.',
    '- 그 창 안에 긴급 픽스가 필요하면 `eas-update.yml`의 수동 실행(`ref`에 스토어 빌드 커밋 기준',
    '  백포트 브랜치)으로 구 런타임 앞으로 따로 게시할 수 있다.',
    '',
    `무엇이 지문을 바꿨는지: \`npx eas fingerprint:compare --build-id ${shipped.id}\``,
  ]);
}
