# 고객 엑셀형 입력 - 충전금 사용 분리 v2 패치

v1 패치에서 `cleaned_rows 저장 루프 위치를 찾지 못했습니다`가 나온 경우 사용하는 보정판입니다.

## 반영 기준

```text
총매출 = 카드 + 현금 + 계좌이체 - 환불
```

- 충전금 사용은 매출에 포함하지 않음
- 충전금 사용은 별도 저장:
  - `prepaid_usage_entries`
  - `prepaid_usage_daily_summary`
- 충전금 사용만 있는 일반 행도 방문수는 카운트
- 환불 행은 방문수/신환/구환/성별 카운트 제외
- 환불 행에는 카드/현금/계좌이체/충전금 사용을 같이 입력할 수 없음

## 사용 순서

1. 서버가 켜져 있으면 끄기

```cmd
Ctrl + C
```

2. `fix_customer_excel_prepaid_separate_v2.py`를 app.py가 있는 폴더에 복사

```text
바탕화면 > beauty_app_step12_customer_import > beauty_app
```

3. CMD에서 이동

```cmd
cd /d %USERPROFILE%\OneDrive\바탕 화면\beauty_app_step12_customer_import\beauty_app
```

4. 패치 실행

```cmd
py fix_customer_excel_prepaid_separate_v2.py
```

5. 서버 실행

```cmd
py app.py
```

6. 테스트

```text
http://127.0.0.1:5000/customers/excel-input
```

## 주의

앞으로 저장되는 엑셀형 입력부터 적용됩니다.
이미 저장된 기존 데이터는 자동 재계산하지 않습니다.
