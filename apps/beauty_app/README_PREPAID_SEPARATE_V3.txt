# 고객 엑셀형 입력 - 충전금 사용 분리 v3 패치

이전 v2에서 아래 오류가 난 경우 사용하는 보정판입니다.

```text
if __name__ == '__main__': 위에 추가
SyntaxError: invalid syntax
```

## 이번 v3에서 추가로 처리하는 것

- 먼저 잘못 들어간 `if __name__ == '__main__': 위에 추가` 안내 문구를 자동으로 주석 처리
- 그 다음 엑셀형 저장 API 전체를 교체
- 마지막에 `app.py` 문법 검사까지 실행

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

## 사용 순서

1. 서버가 켜져 있으면 끄기

```cmd
Ctrl + C
```

2. `fix_customer_excel_prepaid_separate_v3.py`를 app.py가 있는 폴더에 복사

```text
바탕화면 > beauty_app_step12_customer_import > beauty_app
```

3. CMD에서 이동

```cmd
cd /d %USERPROFILE%\OneDrive\바탕 화면\beauty_app_step12_customer_import\beauty_app
```

4. 패치 실행

```cmd
py fix_customer_excel_prepaid_separate_v3.py
```

5. 서버 실행

```cmd
py app.py
```
