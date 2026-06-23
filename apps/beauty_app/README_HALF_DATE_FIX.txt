# 기간비교 반기 날짜 계산 수정 패치

Claude 검토 내용 중 반기 날짜 계산 부분을 반영한 패치입니다.

## 수정 내용

### 1. period_getInitialRange 반기 수정

```javascript
const end = h === 1 ? new Date(year, 5, 30) : new Date(year, 11, 31);
```

### 2. period_getNextRange 반기 수정

```javascript
const nextEnd = halfStartMonth === 0
    ? new Date(normalizedStart.getFullYear(), 5, 30)
    : new Date(normalizedStart.getFullYear(), 11, 31);
```

## 사용 순서

1. 서버 끄기

```cmd
Ctrl + C
```

2. `fix_period_compare_half_dates.py`를 app.py가 있는 폴더에 복사

```text
바탕화면 > beauty_app_step12_customer_import > beauty_app
```

3. CMD에서 이동

```cmd
cd /d %USERPROFILE%\OneDrive\바탕 화면\beauty_app_step12_customer_import\beauty_app
```

4. 패치 실행

```cmd
py fix_period_compare_half_dates.py
```

5. 서버 실행

```cmd
py app.py
```

6. 브라우저 강력 새로고침

```text
Ctrl + F5
```

`beauty_app.db`는 건드리지 않습니다.
