# summary_v2 404 수정 패치

CMD 로그에 아래가 보일 때 사용하는 패치입니다.

GET /api/analytics/summary_v2?... 404

## 사용 순서

1. 서버가 켜져 있으면 Ctrl + C
2. `fix_summary_v2_404.py`를 `app.py`가 있는 beauty_app 폴더에 복사
3. CMD에서 beauty_app 폴더로 이동
4. 실행:

```cmd
py fix_summary_v2_404.py
```

5. 서버 실행:

```cmd
py app.py
```

6. 브라우저에서 새로고침:

```text
http://127.0.0.1:5000/analytics
```

beauty_app.db는 건드리지 않으므로 기존 고객 결제 데이터는 유지됩니다.
