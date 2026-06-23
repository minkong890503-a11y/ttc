# 기간별 비교 5단계 + 버튼 패치

이 패치는 `static/analytics.js`에 + 버튼 기능을 추가합니다.

## 추가 기능

- + 버튼 클릭 시 마지막 카드의 다음 기간을 자동 계산
- 오른쪽에 새 카드 추가
- 최대 12개 제한
- 12개 도달 시 + 버튼 비활성화
- 단위별 다음 기간 계산
  - 일: 다음 날
  - 주: 다음 주 월~일
  - 월: 다음 달
  - 분기: 다음 분기
  - 반기: 다음 반기
  - 연간: 다음 해

## 사용 순서

1. 서버 끄기

```cmd
Ctrl + C
```

2. `add_period_compare_add_button.py`를 app.py가 있는 폴더에 복사

```text
바탕화면 > beauty_app_step12_customer_import > beauty_app
```

3. CMD에서 beauty_app 폴더로 이동

```cmd
cd /d %USERPROFILE%\OneDrive\바탕 화면\beauty_app_step12_customer_import\beauty_app
```

4. 패치 실행

```cmd
py add_period_compare_add_button.py
```

5. 서버 실행

```cmd
py app.py
```

6. 브라우저 확인

```text
http://127.0.0.1:5000/analytics
```

확인 포인트:
- 기간비교 탭에서 + 버튼 클릭 시 다음 기간 카드가 추가되는지
- 주 단위는 7일씩 밀리는지
- 월/분기/반기/연간도 다음 기간으로 추가되는지
- 카드가 12개가 되면 + 버튼이 비활성화되는지
