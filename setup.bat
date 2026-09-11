@echo off
chcp 65001 > nul
echo [1/4] Dang tao moi truong ao Virtualenv...
python -m venv venv

echo [2/4] Dang kich hoat moi truong va cap nhat pip...
call .\venv\Scripts\activate.bat
python -m pip install --upgrade pip

echo [3/4] Dang cai dat cac thu vien trong requirements.txt...
pip install -r requirements.txt

echo [4/4] Dang cai dat Playwright Chromium...
python -m playwright install chromium

echo.
echo === CAI DAT HOAN TAT! CHAY FILE run.bat DE MO UNG DUNG ===
pause
