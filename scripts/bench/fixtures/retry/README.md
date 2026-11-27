# payments

결제 게이트웨이 클라이언트. 게이트웨이 규약은 `docs/gateway.md`.

결제 SLA: 일시적 네트워크 오류(`ConnectError`, `ReadTimeout`)에는 재시도해서, 게이트웨이가 처리한 결제는 호출자에게
성공으로 돌아가야 한다. 재시도 정책은 `src/net/retry.py`.
