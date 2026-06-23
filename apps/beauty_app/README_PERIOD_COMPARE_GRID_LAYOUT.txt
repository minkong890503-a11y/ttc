# 기간비교 8.1단계 레이아웃 패치

## 반영 내용

- `+` 카드 추가 버튼을 카드 오른쪽 끝이 아니라 `조회` 버튼 옆으로 이동
- 카드 영역을 가로 스크롤이 아니라 그리드 배열로 변경
- 카드가 12개일 때 4 x 3 형태로 표시
- 화면이 좁으면 2열, 모바일에서는 1열로 자동 변경

## 사용 순서

1. 서버 끄기

```cmd
Ctrl + C
```

2. `apply_period_compare_grid_layout.py`를 app.py가 있는 폴더에 복사

```text
바탕화면 > beauty_app_step12_customer_import > beauty_app
```

3. CMD에서 이동

```cmd
cd /d %USERPROFILE%\OneDrive\바탕 화면\beauty_app_step12_customer_import\beauty_app
```

4. 패치 실행

```cmd
py apply_period_compare_grid_layout.py
```

5. 서버 실행

```cmd
py app.py
```

6. 브라우저 강력 새로고침

```text
Ctrl + F5
```
