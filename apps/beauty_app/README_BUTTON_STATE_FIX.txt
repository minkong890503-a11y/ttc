# 기간비교 6.1단계 버튼 상태 보정 패치

## 해결하는 문제

- 카드가 1개만 남았는데도 `×` 버튼이 활성화되어 보임
- 카드가 12개가 되었는데도 `+` 버튼이 활성화되어 보임

## 적용 내용

- 카드 개수를 항상 다시 계산해서 버튼 상태를 보정
- 카드가 1개면 `×` 버튼 disabled
- 카드가 12개면 `+` 버튼 disabled
- 카드가 추가/삭제/재렌더링될 때마다 자동으로 상태 갱신

`beauty_app.db`는 건드리지 않습니다.

## 사용 순서

1. 서버 끄기

```cmd
Ctrl + C
```

2. `fix_period_compare_button_states.py`를 app.py가 있는 폴더에 복사

```text
바탕화면 > beauty_app_step12_customer_import > beauty_app
```

3. CMD에서 beauty_app 폴더로 이동

```cmd
cd /d %USERPROFILE%\OneDrive\바탕 화면\beauty_app_step12_customer_import\beauty_app
```

4. 패치 실행

```cmd
py fix_period_compare_button_states.py
```

5. 서버 실행

```cmd
py app.py
```

6. 브라우저에서 강력 새로고침

```text
Ctrl + F5
```
