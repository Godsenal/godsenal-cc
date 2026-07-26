---
name: ego-profile
description: >-
  ego-browser에서 **다른 계정/프로필로** 작업해야 할 때 쓴다. task space는 기본 프로필로 열리므로
  회사↔개인 계정이 갈린 서비스(PostHog, GitHub, Google, AWS 등)에서 "권한이 없다 / 조직이 안 보인다 /
  프로젝트가 목록에 없다"가 나온다. 이때 로그아웃·재로그인으로 헤매지 말고 여기 적힌
  `listProfiles()` + `newTaskSpace(name, profileId)` 를 쓴다. "다른 계정으로", "회사 계정 말고",
  "프로필 바꿔서", "계정 전환" 같은 말이 나오거나, ego에서 예상과 다른 계정으로 붙었을 때 이 스킬을 읽어라.
---

# ego-browser 계정/프로필 전환

## 결론부터

```js
cliLog(JSON.stringify(await listProfiles()))          // 1. 프로필 목록
const task = await newTaskSpace('작업이름', 'Profile 7')  // 2. 프로필 지정해서 space 생성
```

`newTaskSpace(name, profileId)` — **위치 인자 두 개**다. 옵션 객체가 아니다.
(내부 시그니처: `ego.createTaskSpace(name, profileId?)`)

## 반드시 먼저 할 것: 어느 계정인지 확인

`snapshotText()` 로 화면을 읽기 전에, **로그인 계정을 API로 확정한다.** 화면만 보면 로그인된 것처럼
보여서 한참 진행한 뒤에야 "이 조직에 그 프로젝트가 없다"로 드러난다.

```js
const d = JSON.parse(await js(String.raw`(async () => {
  const r = await fetch('/api/users/@me/', { headers: { accept: 'application/json' } })
  return JSON.stringify(await r.json())
})()`))
cliLog(d.email + ' | ' + (d.organizations ?? []).map(o => o.name).join(', '))
```

엔드포인트는 서비스마다 다르다 — PostHog `/api/users/@me/`, GitHub `/api/v3/user` 또는
`gh api user`, Google `myaccount.google.com`. **없으면 화면에서 계정 이메일을 직접 읽어 확인한다.**

## 하지 말 것 (실제로 낭비한 경로)

| 시도 | 왜 안 되는가 |
|---|---|
| 기존 task space에서 로그아웃 → 재로그인 | 유저 비밀번호가 필요하다. 에이전트가 할 일이 아니다 |
| `import --browser chrome --profile "X"` 후 그냥 진행 | import는 **성공한다**. 하지만 task space는 여전히 **기본 프로필**로 열려 계정이 그대로다 |
| task space를 지우고 새로 만들기 | 프로필을 안 넘기면 역시 기본 프로필이다 |
| `newTaskSpace(name, { profileId })` | 옵션 객체를 받지 않는다. 조용히 기본 프로필로 만들어진다 |

**핵심 오해:** "task space는 유저의 로그인 상태를 물려받는다"를 "프로필을 바꿀 수 없다"로 읽으면 안 된다.
물려받는 건 **기본 프로필**이고, 프로필은 인자로 고를 수 있다.

## 원하는 프로필이 ego에 없을 때

`listProfiles()` 에 없으면 그때 import 한다. 그리고 **import 후 새 space를 만들 때 그 프로필 id를 넘긴다.**

```bash
ego-browser import list                                   # 어떤 브라우저/프로필이 있는지
ego-browser import --browser chrome --profile "Profile 2" # 가져오기
```

`import list` 의 `dir_name`(예: `Profile 2`)과 ego 내부 `listProfiles()` 의 `id`(예: `Profile 7`)는
**다르다.** import 결과의 `new_profile_dirs` 또는 import 직후 `listProfiles()` 로 새로 생긴 id를 확인한다.

import는 **복사**다 — ego 안에서 계정을 바꿔도 유저의 실제 Chrome 세션은 건드리지 않는다.
(반대로 말하면, 유저가 그 프로필에서 로그아웃해도 ego 쪽 사본은 남는다.)

## 남는 벽: 재인증은 유저 몫

계정이 맞아도 민감 설정 화면(API 키, 결제, 보안)은 **재인증**을 요구하는 서비스가 많다.
비밀번호 입력·OAuth 완료는 에이전트가 하지 않는다. `handOffTaskSpace(task.id)` 로 넘기고,
무엇을 눌러야 하는지 한 줄로 알려준 뒤 유저의 "계속"을 기다린다. 그 다음 `takeOverTaskSpace(task.id)`.

## 문서에 없는 헬퍼

`listProfiles()` 와 `newTaskSpace()` 는 ego-browser SKILL.md의 헬퍼 목록에 **없다.** 런타임에는 있다.
비슷하게 막히면 전역을 훑어 확인한다:

```js
cliLog(Object.getOwnPropertyNames(globalThis).filter(n => typeof globalThis[n] === 'function').sort().join('\n'))
```

`help(name)` 은 일부 헬퍼만 커버한다(`listProfiles`/`newTaskSpace` 는 `Unknown helper`).
**시그니처는 일부러 틀리게 호출해 에러 메시지에서 얻는 게 가장 빠르다** — 이 스킬의 정답도
`newTaskSpace({...})` 를 넘겼을 때 나온 에러가 알려줬다.
