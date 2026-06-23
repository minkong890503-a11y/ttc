# 기간별 비교 3단계 JS 패치

이 패치는 `static/analytics.js`에 아래 기능을 추가합니다.

- 분석 / 기간비교 하위 탭 전환
- 기본 탭은 기존 분석 탭 유지
- 기간비교 탭 최초 진입 시 기본값 설정
  - 단위: 일
  - 기준일: 오늘
- 단위 버튼 클릭 시 기준 입력 영역 show/hide
- 단위 변경 시 확인창 표시
- 조회 버튼 클릭 시 선택된 기간 범위 표시

아직 실제 카드 API 호출 및 카드 생성은 다음 단계에서 연결합니다.

## 사용 순서

1. 서버 끄기

```cmd
Ctrl + C
```

2. `add_period_compare_tab_js.py`를 app.py가 있는 폴더에 복사

```text
바탕화면 > beauty_app_step12_customer_import > beauty_app
```

3. CMD에서 beauty_app 폴더로 이동

```cmd
cd /d %USERPROFILE%\OneDrive\바탕 화면\beauty_app_step12_customer_import\beauty_app
```

4. 패치 실행

```cmd
py add_period_compare_tab_js.py
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
- 분석 / 기간비교 탭이 보이는지
- 기간비교 클릭 시 기존 분석 화면이 숨겨지는지
- 단위 버튼 클릭 시 기준 입력창이 바뀌는지
- 조회 버튼 클릭 시 기간 범위 안내가 나오는지
