# summary_v2 위치 수정 패치

현재 확인된 상태:

- `if __name__ == '__main__':` : 471줄
- `@app.route("/api/analytics/summary_v2")` : 480줄

이 경우 Flask 서버가 먼저 실행되고, 그 아래 라우트는 등록되지 않아 404가 발생합니다.

## 사용 순서

1. 서버 끄기

```cmd
Ctrl + C
```

2. `fix_move_summary_v2_before_main.py`를 app.py가 있는 폴더에 복사

3. CMD에서 실행

```cmd
py fix_move_summary_v2_before_main.py
```

4. 확인

```cmd
findstr /n summary_v2 app.py
findstr /n __main__ app.py
```

summary_v2 줄 번호가 __main__보다 작아야 정상입니다.

5. 서버 실행

```cmd
py app.py
```
