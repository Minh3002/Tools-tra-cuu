@echo off
chcp 65001 > nul
echo Dang khoi chay ung dung Streamlit BHYT Crawler...
call .\venv\Scripts\activate.bat
streamlit run app.py
pause
