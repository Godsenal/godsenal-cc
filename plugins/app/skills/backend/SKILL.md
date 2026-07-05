---
name: backend
description: >-
  gapp 하네스 3단계 — Supabase 백엔드 세팅. 프로젝트 생성부터 검증된 보안모델(RLS + security-definer
  RPC, private storage + signed URL, service_role은 Edge Function에만), append-only 마이그레이션 규율,
  로컬-우선(익명 세션→승격) 아키텍처, 오프라인 쓰기 재시도 큐, 클라우드 통합 스모크 테스트까지 깐다.
  "백엔드 세팅", "supabase 붙이자", "DB 스키마", "서버 만들자", "동기화" 요청이나 design 직후
  다음 단계로 이 스킬을 써라. 서버가 필요 없는 앱이면 HARNESS.md에 N/A 표기하고 건너뛴다.
---

# /gapp:backend — Supabase 백엔드 (보안모델 포함)

전제: HARNESS.md에서 백엔드 필요 판정이 났다. 아니라면 N/A 체크만 하고 종료.
Supabase MCP가 연결돼 있으면 그걸 쓰고(스키마 조회 `list_tables`, 배포 후 `get_advisors`),
없으면 CLI로. `supabase` 공식 스킬이 설치돼 있으면 함께 로드.

## 1. 프로젝트 + 로컬 구조

1. Supabase 프로젝트 생성 (조직/리전은 유저 확인 — 비용 발생 지점).
2. 레포 구조 확립:
   ```
   supabase/
     schema.sql            # 사람이 읽는 캐노니컬 스키마 (전체 그림)
     migrations/000N_*.sql # 실제 적용되는 append-only 마이그레이션
     functions/<name>/     # Edge Functions (service_role은 여기만)
   ```
   **규율: `schema.sql`이 진실의 원장, migrations는 append-only(기존 파일 수정·삭제 금지).**
   둘을 개념적으로 항상 동기화. 로컬 SQLite 캐시를 쓰면 그쪽 마이그레이션도 같은 규율
   (단조증가 배열 + `PRAGMA user_version` 게이트, append-only).
3. 클라이언트: `lib/supabase.ts` — `EXPO_PUBLIC_SUPABASE_URL`/`ANON_KEY`, **설정 누락 시 throw 금지**
   (placeholder 클라이언트 + `hasSupabaseConfig` 게이트). anon key는 클라이언트 노출이 설계상 정상
   — 데이터는 RLS가 지킨다.

## 2. 아키텍처 결정: 로컬-우선, 클라우드-캐노니컬 (기본 권장)

로그인 마찰 없이 시작하고 공유 기능에서만 계정을 요구하는 패턴. 유저와 채택 여부 확인:

- **읽기는 100% 로컬**(SQLite 캐시) → 오프라인 동작, 즉시 렌더. 클라우드가 공유 데이터의 진실.
- **익명 유저는 완전 로컬로 동작** — `signInAnonymously()`로 익명 세션만 확보, owner류 컬럼은
  `'local'` placeholder. 실 로그인(Apple 등) 시 로컬 데이터를 클라우드로 승격(sync-up).
- **동기화**: 앱 열림/재연결 시 `updated_at > last_synced_at` 증분 pull(커서는 로컬 `sync_state`),
  실시간은 Realtime 구독. **소프트 삭제만**(`deleted_at` 톰스톤, 캐시에서 hard-delete 금지, 조회는
  `deleted_at IS NULL` 필터).
- **동기화 코어는 순수 함수로**(pure reconcile + thin SQLite IO) 유닛테스트를 붙인다.
- **오프라인 쓰기 유실 방지**: 클라우드 쓰기 RPC 실패 시 `pending_ops` 테이블에 적재 →
  동기화/새로고침 직전에 flush(동시실행 가드). 새 쓰기 경로마다 같은 패턴.

단순 CRUD 온라인 전용 앱이면 이 레이어 없이 supabase-js 직행도 유효 — 결정을 HARNESS.md에 기록.

## 3. 보안모델 (실사고 기반 규칙 — 그대로 적용)

1. **쓰기 중 권한이 걸린 것은 전부 `security definer` RPC로만.** 멤버십/역할 변경, 소유권 이전,
   삭제 등에 직접 INSERT/UPDATE RLS 정책을 열지 않는다. 클라이언트가 `id`/타임스탬프/외래키를
   임의로 못 바꾸게 하는 유일한 방법.
2. **모든 security-definer RPC 첫 줄에 권한 선차단** — 예: `if my_role(...) is null then raise`.
   *이걸 빼먹는 게 반복 실사고 패턴이다* — 새 RPC 추가 시마다 체크.
3. **RLS로 읽기 게이트** — 멤버십 헬퍼 함수(`my_role()` 식)를 만들어 정책에서 재사용.
4. **익명 세션 권한 제한** — `is_anon()` 체크로 익명 JWT는 공유 리소스 생성/참여 차단(서버측).
5. **Storage는 private 버킷 + signed URL만.** 공개 URL 금지. 경로에 리소스 id를 넣고
   (`<resource_id>/<file>`), 정책이 경로 세그먼트로 멤버십 판정.
6. **`service_role` 키는 Edge Function에만.** 클라이언트/레포의 env 어디에도 금지.
7. 배포 후 `get_advisors`(security) 돌려서 RLS 빠진 테이블 없는지 확인.

`supabase-postgres-best-practices` 스킬이 있으면 스키마 작성 시 함께 로드.

## 4. 검증 — 클라우드 통합 스모크 테스트

실기기 없이 Supabase 인스턴스에 대해 도는 Node 스크립트를 만든다
(`scripts/cloud-integration-test.mjs` 식):

- anon key로 익명 세션 → 허용된 것/차단돼야 하는 것(익명의 공유 리소스 생성 등)을 실제로 호출해 단언
- RPC 해피패스 + 권한 없는 호출이 막히는지
- 실행: `API_URL=<url> ANON_KEY=<key> node scripts/cloud-integration-test.mjs`

이 스크립트는 cicd 이후 배포 검증에도 재사용된다.

## 5. 마무리

- 새 레포 CLAUDE.md에 보안모델 요약(위 규칙 1·2·5·6)과 마이그레이션 append-only 규칙 추가.
- HARNESS.md: backend 체크, 프로젝트 ref/리전 기록, 로그.
- 한 줄 보고 후 **`/gapp:cicd`를 바로 이어서 실행한다** (이어달리기 규칙).
