# 고객 엑셀형 입력 SyntaxError 수정 패치

## 해결하는 오류

```text
SyntaxError: invalid syntax
if __name__ == '__main__': 위에 추가
```

## 사용 순서

1. 현재 CMD 위치가 beauty_app 폴더인지 확인

```cmd
cd /d %USERPROFILE%\OneDrive\바탕 화면\beauty_app_step12_customer_import\beauty_app
```

2. `fix_customer_excel_syntax_error.py`를 app.py가 있는 폴더에 복사

3. 실행

```cmd
py fix_customer_excel_syntax_error.py
```

4. 서버 실행

```cmd
py app.py
```

5. 고객 엑셀형 입력 접속

```text
http://127.0.0.1:5000/customers/excel-input
```

`beauty_app.db`는 건드리지 않습니다.
