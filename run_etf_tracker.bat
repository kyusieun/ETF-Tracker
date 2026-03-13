@echo off
REM ==== ETF 트래커 실행 배치 파일 ====
REM 이 파일을 더블클릭하면 자동으로 실행됩니다.

SETLOCAL

REM 한글 로그가 깨지지 않도록 UTF-8 코드 페이지로 변경
chcp 65001 >nul

REM 1) 작업 폴더로 이동
cd /d "%~dp0"

REM 2) (선택) 가상환경 폴더 이름
set VENV_DIR=.venv

REM 3) 가상환경이 없으면 새로 만들기
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [INFO] Python 가상환경 생성 중...
    python -m venv "%VENV_DIR%"
)

REM 4) 가상환경 활성화
call "%VENV_DIR%\Scripts\activate.bat"

REM 5) 필요한 라이브러리 설치/업데이트
echo [INFO] Python 패키지 설치/업데이트...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

REM 6) ETF 트래커 실행 (오늘 기준, 두 ETF 모두)
echo [INFO] ETF 트래커 실행 중...
python main.py --all

echo.
echo [INFO] 작업이 완료되었습니다. 텔레그램을 확인하세요.
echo 창을 닫으려면 아무 키나 누르세요.
pause >nul

ENDLOCAL