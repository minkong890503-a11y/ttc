# 잘못 들어간 안내 문구 제거 패치

## 해결하는 오류

```text
if __name__ == '__main__': 위에 추가
SyntaxError: invalid syntax
```

## 사용 순서

1. `fix_remove_bad_guide_lines.py`를 app.py가 있는 폴더에 복사

```text
바탕화면 > beauty_app_step12_customer_import > beauty_app
```

2. CMD에서 실행

```cmd
py fix_remove_bad_guide_lines.py
```

3. 문법 검사 통과 후 서버 실행

```cmd
py app.py
```

`beauty_app.db`는 건드리지 않습니다.
