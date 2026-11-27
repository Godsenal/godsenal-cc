# storefront

가게 화면 렌더러. 화면은 `src/screens/` 의 모듈마다 `render(order)` 하나이고, 각 모듈의 `STORE` 가 그 화면의 가게다.
가게별 통화는 `src/stores.py` 의 `STORES` 에 있다. 금액은 모두 통화의 최소 단위 정수다(KRW 원, USD 센트, JPY 엔).

    python3 -m src.preview            # 모든 화면을 예시 주문으로 렌더링
