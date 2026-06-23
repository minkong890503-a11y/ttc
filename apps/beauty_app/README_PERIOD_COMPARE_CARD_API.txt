# 기간별 비교 4단계 카드/API 패치

이 패치는 `static/analytics.js`에 실제 카드 생성 기능을 추가합니다.

## 추가 기능

- 기간비교 탭 최초 진입 시 카드 1개 자동 생성
- 조회 버튼 클릭 시 선택 기간 카드 1개 생성
- `/api/analytics/period-summary` API 호출
- 카드에 아래 항목 표시
  - 총내원
  - 신환매출
  - 구환매출
  - 총매출
  - 총지출
  - 결산
  - 근무일수, 단 일 단위에서는 숨김
- 진행 중 / 데이터 없음 뱃지 표시
- 카드가 1개일 때 삭제 버튼 비활성화

아직 + 버튼으로 다음 기간 추가 기능은 다음 단계에서 연결합니다.

## 사용 순서

1. 서버 끄기

```cmd
Ctrl + C
```

2. `add_period_compare_card_api.py`를 app.py가 있는 폴더에 복사

```text
바탕화면 > beauty_app_step12_customer_import > beauty_app
```

3. CMD에서 beauty_app 폴더로 이동

```cmd
cd /d %USERPROFILE%\OneDrive\바탕 화면\beauty_app_step12_customer_import\beauty_app
```

4. 패치 실행

```cmd
py add_period_compare_card_api.py
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
- 기간비교 탭 클릭 시 오늘 기준 카드 1개가 자동으로 뜨는지
- 조회 버튼 클릭 시 선택한 기간의 카드가 다시 생성되는지
- 일 단위에서는 근무일수가 숨겨지는지
- 주/월/분기/반기/연간 단위에서는 근무일수가 보이는지
