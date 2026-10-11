@echo off
setlocal
cd /d "%~dp0"
echo ==================================================
echo Medigraph Graph Explorer - synthetic demo only
echo ==================================================
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher 'py' not found. Install Python 3 and try again.
  pause
  exit /b 1
)
py -m pip install -r requirements.txt
if errorlevel 1 goto failed
py -m streamlit run app.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo The graph explorer could not start. Check the error above.
pause
exit /b 1