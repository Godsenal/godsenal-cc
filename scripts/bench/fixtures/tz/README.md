# orders

여러 나라 가게의 주문 처리. 주문 타임스탬프는 가게 현지 시각에 오프셋을 붙인 ISO 8601 문자열이다
(`2026-03-01T23:30:00+09:00`). 시간 규칙은 `docs/time.md`.

    python3 -m src.reports.daily data/orders.jsonl     # 가게·날짜별 매출
