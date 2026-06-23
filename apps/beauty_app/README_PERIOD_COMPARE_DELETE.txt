# 기간별 비교 6단계 카드 삭제 안정화 패치

이 패치는 `static/analytics.js`에 카드 삭제 안정화 기능을 추가합니다.

## 추가 기능

- × 버튼으로 카드 삭제
- 카드가 1개일 때 × 버튼 비활성화
- 삭제 전 확인창 표시
- 삭제 후 내부 카드 상태 재정리
- 삭제 후 + 버튼 상태 갱신
- 최대 12개 제한과 함께 안정적으로 동작

## 사용 순서

1. 서버 끄기

```cmd
Ctrl + C
```

2. `add_period_compare_delete_stabilize.py`를 app.py가 있는 폴더에 복사

```text
바탕화면 > beauty_app_step12_customer_import > beauty_app
```

3. CMD에서 beauty_app 폴더로 이동

```cmd
cd /d %USERPROFILE%\OneDrive\바탕 화면\beauty_app_step12_customer_import\beauty_app
```

4. 패치 실행

```cmd
py add_period_compare_delete_stabilize.py
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
- 카드가 1개일 때 × 버튼이 비활성화되는지
- +로 카드를 2개 이상 만든 뒤 ×로 삭제되는지
- 삭제 후 카드가 1개 남으면 다시 × 버튼이 비활성화되는지
- 삭제 후 + 버튼이 다시 정상 활성화되는지
