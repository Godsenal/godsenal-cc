# 게이트웨이 규약

- `POST /charges`, `POST /refunds`, `POST /payouts` 는 `Idempotency-Key` 헤더를 받는다. 같은 키로 다시 온 요청은 새로 처리하지 않고
  처음 처리한 결과를 그대로 돌려준다(24시간).
- `ConnectError`: 요청이 게이트웨이에 닿지 않았다.
- `ReadTimeout`: 요청은 닿았고 처리됐을 수도 있다. 응답만 못 받은 것이다.
