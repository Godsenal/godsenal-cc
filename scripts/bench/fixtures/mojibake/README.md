# pos-sync

가게 POS 가 내보낸 CSV 를 읽어 리포트와 재고, 회원 목록을 만든다.

    python3 -m src.reports.sales <store> <sales.csv>      # 상품별 매출
    python3 -m src.reports.stock <store> <stock.csv>      # 재고 부족 목록
    python3 -m src.members.sync <store> <members.csv>     # 회원 목록 동기화

가게와 POS 기종은 `src/stores.py` 에 있다. POS 기종마다 내보내는 형식은 `docs/pos.md`.
