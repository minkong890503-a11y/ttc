# beauty_app_step10_beta

뷰티샵 일일결산 웹앱 베타 버전입니다.

## 포함 기능
- 로그인/로그아웃
- 고객 입력
- 화장품 재고
- 화장품 다중 제품 판매
- 지출 입력
- 시재 입력
- 일일결산 저장 이력
- 월간결산
- 직원매출현황
- 대시보드

## 실행 방법

```cmd
cd /d "%USERPROFILE%\OneDrive\바탕 화면\beauty_app_step10_beta\beauty_app"
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
py database.py
py app.py
```

브라우저 접속:

```text
http://127.0.0.1:5000
```

초기 계정:

```text
아이디: admin
비밀번호: BEAUTY_APP_ADMIN_PASSWORD
```

## 주의
이 파일은 전체 기능을 한 번에 확인하기 위한 beta 버전입니다. 실제 운영 전에는 계산식과 화면 흐름을 충분히 검수해야 합니다.


## Step11 Analytics 추가 기능
- 결산분석 메뉴 추가
- daily_closing_summary 요약 테이블 추가
- 고객/화장품/지출/일일결산 저장 후 요약 자동 재계산
- 누적 선 그래프, 요일별 막대 그래프 제공
