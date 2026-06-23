# 기존 고객 CSV 가져오기 안내

이 버전은 기존 월별 고객 시트 CSV를 웹앱의 `customer_records` 테이블 형식으로 가져오는 도구를 포함합니다.

## 포함 파일

```text
legacy_customer_csvs/
├── 1고객.csv
├── 2고객.csv
├── 3고객.csv
├── 4고객.csv
└── 5고객(1).csv

import_legacy_customer_csvs.py
```

## 실행 방법

Step11/Step12 웹앱 폴더에서 아래 순서로 실행합니다.

```cmd
venv\Scripts\activate
py import_legacy_customer_csvs.py
py app.py
```

## 가져오는 방식

- `구분`의 `신`은 `신규`, `구`는 `구환`으로 변환합니다.
- `결제+시술`은 현재 웹앱 DB 제약에 맞춰 `결제`로 저장하고, 원본 유형은 비고에 남깁니다.
- `환불` 행은 금액을 양수로 저장하고, 결산 계산에서 차감 처리합니다.
- 가져온 데이터의 `created_by`는 `legacy_import`로 저장합니다.
- 같은 스크립트를 다시 실행하면 기존 `legacy_import` 데이터만 삭제 후 다시 가져옵니다.
- 웹앱에서 직접 입력한 데이터는 삭제하지 않습니다.

## 새 CSV로 바꾸는 방법

1. `legacy_customer_csvs` 폴더 안의 CSV 파일을 새 파일로 교체합니다.
2. CSV는 기존 고객 시트와 같은 헤더를 유지해야 합니다.
3. 다시 아래 명령어를 실행합니다.

```cmd
py import_legacy_customer_csvs.py
```

필수 컬럼:

```text
날짜, 구분, 성별, 고객명, 방문시간, 결제,시술,환불,기타, 카드, 현금, 계좌이체, 충전금 사용, 비고, 확인자
```
