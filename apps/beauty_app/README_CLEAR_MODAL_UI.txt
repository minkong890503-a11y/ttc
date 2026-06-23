# 기간비교 7.2단계 명확한 모달 UI 패치

## 해결하는 문제
- 기간 수정창이 어디에 뜨는지 모호함
- 취소 버튼이 안 보이거나 애매함
- 시작일/종료일 입력창이 명확하게 보이지 않음

## 적용 내용
- 화면 중앙에 크게 뜨는 기간 수정 팝업
- 오른쪽 위 X 닫기 버튼
- 하단 취소 / 확인 버튼
- 시작일 / 종료일 date input 명확히 표시
- 바깥 어두운 배경 처리

## 사용 순서

1. 서버 끄기

```cmd
Ctrl + C
```

2. `fix_period_compare_clear_modal_ui.py`를 app.py가 있는 폴더에 복사

```text
바탕화면 > beauty_app_step12_customer_import > beauty_app
```

3. CMD에서 이동

```cmd
cd /d %USERPROFILE%\OneDrive\바탕 화면\beauty_app_step12_customer_import\beauty_app
```

4. 패치 실행

```cmd
py fix_period_compare_clear_modal_ui.py
```

5. 서버 실행

```cmd
py app.py
```

6. 브라우저에서 강력 새로고침

```text
Ctrl + F5
```

7. 기간비교 카드의 날짜 범위 부분을 클릭하세요.
