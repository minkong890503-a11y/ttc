# 기간별 비교 7단계 기간 수정 모달 패치

이 패치는 `static/analytics.js`에 기간 수정 모달 기능을 추가합니다.

## 추가 기능

- 카드의 날짜 범위 클릭 시 모달 열기
- 시작일 / 종료일 수정
- 시작일이 종료일보다 늦으면 저장 차단
- 확인 클릭 시 해당 카드만 API 재조회
- 취소 / 바깥 클릭 / ESC로 닫기

## 사용 순서

1. 서버 끄기

```cmd
Ctrl + C
```

2. `add_period_compare_edit_modal.py`를 app.py가 있는 폴더에 복사

```text
바탕화면 > beauty_app_step12_customer_import > beauty_app
```

3. CMD에서 beauty_app 폴더로 이동

```cmd
cd /d %USERPROFILE%\OneDrive\바탕 화면\beauty_app_step12_customer_import\beauty_app
```

4. 패치 실행

```cmd
py add_period_compare_edit_modal.py
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
- 기간비교 카드의 날짜 범위를 클릭하면 모달이 열리는지
- 시작일/종료일 변경 후 확인하면 해당 카드 데이터가 바뀌는지
- 시작일 > 종료일이면 오류 메시지가 나오는지
- 취소/ESC/바깥 클릭으로 닫히는지
