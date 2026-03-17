## ETF 트래커 (KoAct / TIME 코스닥 액티브)

두 개의 코스닥 액티브 ETF(**KoAct 코스닥액티브, TIME 코스닥 액티브**)의 **일별 편입/편출, 수량 변화, 현재 비중**을 자동으로 비교해 텔레그램으로 알려주는 도구입니다.

### 이 프로그램으로 할 수 있는 것

- 매일 웹에서 두 ETF의 **구성 종목 엑셀을 자동 다운로드**
- 전일 대비 **편입 / 편출 / 수량 증가 / 수량 감소** 계산
- 각 종목에 대해 **전일 수량 → 현재 수량 (Δ수량) [현재 비중]** 형식으로 텔레그램에 요약 전송
- 전체 결과 CSV 파일을 텔레그램에 **첨부 파일**로 함께 전송

---

### 빠른 시작

#### 1. 사전 준비

1. **Python 3.10 이상 설치**
2. 텔레그램에서 봇을 만들고(`@BotFather`), 봇 토큰과 알림을 받을 채팅의 `chat_id` 를 준비합니다.
3. 프로젝트 폴더(예: `C:\ETF Tracker`) 안의 `.env` 파일을 생성하고 아래처럼 값을 채웁니다.

```env
TELEGRAM_BOT_TOKEN=여기에_봇_토큰
TELEGRAM_CHAT_ID=여기에_chat_id
```

#### 2. 오늘 기준으로 자동 실행

1. `run_etf_tracker.bat` 파일을 더블클릭합니다.
2. 처음 실행 시에는:
  - Python 가상환경을 만들고
  - 필요한 라이브러리(엑셀/텔레그램 관련)를 자동으로 설치합니다.
3. 이후에는:
  - KoAct / TIME 두 ETF의 **오늘자 구성 종목**을 웹에서 내려받고
  - 어제와 비교해서 **편입/편출/수량 증가/수량 감소**를 계산한 뒤
  - 텔레그램으로 요약 메시지 + 전체 CSV 파일을 보내줍니다.

#### 3. 날짜를 직접 골라서 실행하고 싶을 때

과거 날짜 기준으로 결과를 보고 싶다면 `run_etf_tracker_with_date.bat` 를 사용합니다.

1. `run_etf_tracker_with_date.bat` 를 더블클릭합니다.
2. 콘솔에 나오는 안내에 따라 날짜를 입력합니다. (예: `2026-03-12`)
3. 해당 날짜 기준으로 두 ETF의 데이터를 내려받아 동일한 방식으로 비교/알림을 수행합니다.

#### 4. 매일 정해진 시간에 자동 실행 (윈도우 작업 스케줄러)

1. 윈도우 검색에서 **“작업 스케줄러”** 를 실행합니다.
2. **작업 만들기**를 선택합니다.
3. **트리거** 탭에서:
  - 새로 만들기 → 매일 → 예: 19:00 로 설정합니다. (장 마감 후)
4. **동작** 탭에서:
  - 새로 만들기 →
    - 프로그램/스크립트: `C:\ETF Tracker\run_etf_tracker.bat`

이렇게 설정해 두면, 매일 지정한 시간에 자동으로 트래커가 실행되고 텔레그램으로 결과가 도착합니다.

---

### 설치

1. Python 3.10 이상을 설치합니다.
2. (선택) 가상환경을 직접 만들고 싶다면:

```bash
python -m venv .venv
.\.venv\Scripts\activate
```

1. 의존성 설치:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

1. 텔레그램 환경 변수 또는 `.env` 파일 설정:

```env
TELEGRAM_BOT_TOKEN=123456:ABCDEF...
TELEGRAM_CHAT_ID=123456789
```

---

### 수동 실행 예시

기본 실행 (두 ETF 모두, 오늘 날짜 기준):

```bash
python main.py --all
```

특정 날짜/ETF로 실행:

```bash
python main.py --etf koact --date 2026-03-12
python main.py --etf time --date 2026-03-12
```

---

### 디렉터리 구조 (참고)

- `data/` : ETF별·날짜별 원본 엑셀 파일 (자동 다운로드)
  - `data/koact/YYYY-MM-DD_koact.xls`
  - `data/time/YYYY-MM-DD_time.xlsx`
- `reports/` : 일별 비교 결과(csv)
  - `koact_YYYY-MM-DD_full.csv`
  - `time_YYYY-MM-DD_full.csv`
- `etf_tracker/`
  - `etl/` : 엑셀 파싱 및 다운로드 모듈
  - `core/` : 비교(difference) 계산 로직
  - `alerts/` : 텔레그램 알림 모듈
  - `config.py` : ETF 설정 및 공통 상수
- `main.py` : 전체 파이프라인 실행 진입점
- `run_etf_tracker.bat` : 오늘 기준 자동 실행용 배치 파일
- `run_etf_tracker_with_date.bat` : 날짜를 직접 입력해 실행하는 배치 파일

