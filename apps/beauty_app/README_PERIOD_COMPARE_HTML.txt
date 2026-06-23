# 기간별 비교 2단계 HTML 패치

이 패치는 `templates/analytics.html`에 아래 구조를 추가합니다.

- 결산분석 하위 탭: 분석 / 기간비교
- 기존 분석 화면을 `#tab-analysis`로 감싸기
- 신규 기간비교 탭 `#tab-period` 추가
- 기간비교 컨트롤, 카드 컨테이너, 기간 수정 모달 HTML 뼈대 추가

`beauty_app.db`는 건드리지 않습니다.

## 사용 순서

1. 서버 끄기

```cmd
Ctrl + C
```

2. `add_period_compare_html.py`를 app.py가 있는 폴더에 복사

```text
바탕화면 > beauty_app_step12_customer_import > beauty_app
```

3. CMD에서 beauty_app 폴더로 이동

```cmd
cd /d %USERPROFILE%\OneDrive\바탕 화면\beauty_app_step12_customer_import\beauty_app
```

4. 패치 실행

```cmd
py add_period_compare_html.py
```

5. 서버 실행

```cmd
py app.py
```

6. 브라우저 확인

```text
http://127.0.0.1:5000/analytics
```

아직 2단계는 HTML 뼈대만 추가하는 단계라, 탭 버튼 클릭 기능은 다음 단계에서 추가됩니다.
