# 고객 엑셀형 입력 패치

## 추가되는 기능

- 새 페이지: `/customers/excel-input`
- 엑셀형 고객 입력 테이블
- 거래유형 삭제
- 방문시간 삭제
- 환불 컬럼 추가
- 고객명 입력 시 날짜가 비어 있으면 오늘 날짜 자동 입력
- 환불은 매출에서 차감
- 환불 행은 방문수/신환/구환/성별 카운트 제외

## 컬럼

```text
날짜 | 고객구분 | 성별 | 고객명 | 카드 | 현금 | 계좌이체 | 충전금 사용 | 환불 | 비고
```

## 사용 순서

1. 서버 끄기

```cmd
Ctrl + C
```

2. `add_customer_excel_input.py`를 app.py가 있는 폴더에 복사

```text
바탕화면 > beauty_app_step12_customer_import > beauty_app
```

3. CMD에서 이동

```cmd
cd /d %USERPROFILE%\OneDrive\바탕 화면\beauty_app_step12_customer_import\beauty_app
```

4. 패치 실행

```cmd
py add_customer_excel_input.py
```

5. 서버 실행

```cmd
py app.py
```

6. 브라우저 접속

```text
http://127.0.0.1:5000/customers/excel-input
```

## 주의

- `beauty_app.db`는 삭제하거나 초기화하지 않습니다.
- 저장 시 `customer_excel_entries` 테이블에 입력 내역을 저장합니다.
- 동시에 `daily_closing_summary`에 해당 날짜의 매출/방문수 요약을 반영합니다.
