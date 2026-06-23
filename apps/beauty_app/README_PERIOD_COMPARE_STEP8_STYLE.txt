# 기간비교 8단계 스타일 패치

## 해결하는 문제

현재 화면처럼 카드가 박스 형태가 아니라 행처럼 길게 펼쳐지는 문제를 해결합니다.

## 적용 내용

- 분석 / 기간비교 탭 스타일 정리
- 단위 버튼 스타일 정리
- 기간비교 컨트롤 영역 흰색 박스 처리
- 기간 카드 흰색 박스 형태 적용
- 카드 가로 스크롤 적용
- 카드 내부 라벨/값 2열 정렬
- + 버튼 원형 스타일 적용
- 진행 중 / 데이터 없음 뱃지 정리
- 모바일 기본 대응

## 사용 순서

1. 서버 끄기

```cmd
Ctrl + C
```

2. `apply_period_compare_step8_style.py`를 app.py가 있는 폴더에 복사

```text
바탕화면 > beauty_app_step12_customer_import > beauty_app
```

3. CMD에서 이동

```cmd
cd /d %USERPROFILE%\OneDrive\바탕 화면\beauty_app_step12_customer_import\beauty_app
```

4. 패치 실행

```cmd
py apply_period_compare_step8_style.py
```

5. 서버 실행

```cmd
py app.py
```

6. 브라우저 강력 새로고침

```text
Ctrl + F5
```
