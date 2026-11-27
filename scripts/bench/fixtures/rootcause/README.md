# sales

지역별 매출 리포트, 지역별 고객 내보내기, 지역별 목표.

    python3 -m src.report data/sales.csv      # 지역별 매출 합계
    python3 -m src.export data/sales.csv      # 지역별 고객 목록
    python3 -m src.targets data/targets.csv   # 지역별 월 목표

입력 CSV 는 모두 영업팀이 엑셀에서 내보낸 파일이다.
