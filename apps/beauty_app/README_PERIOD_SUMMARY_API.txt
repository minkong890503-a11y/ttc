# 기간별 비교 1단계 패치

이 파일은 app.py에 `/api/analytics/period-summary` API만 추가합니다.
기존 고객 데이터가 들어있는 `beauty_app.db`는 건드리지 않습니다.

## 사용 순서

1. 서버 끄기

```cmd
Ctrl + C
```

2. `add_period_summary_api.py`를 app.py가 있는 폴더에 복사

```text
바탕화면 > beauty_app_step12_customer_import > beauty_app
```

3. CMD에서 beauty_app 폴더로 이동

```cmd
cd /d %USERPROFILE%\OneDrive\바탕 화면\beauty_app_step12_customer_import\beauty_app
```

4. 패치 실행

```cmd
py add_period_summary_api.py
```

5. 서버 실행

```cmd
py app.py
```

6. 브라우저에서 테스트

```text
http://127.0.0.1:5000/api/analytics/period-summary?unit=week&start=2026-05-18&end=2026-05-24
```

정상이라면 JSON 데이터가 표시됩니다.
