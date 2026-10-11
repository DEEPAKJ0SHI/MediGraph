@echo off
setlocal
cd /d "%~dp0"
echo ==================================================
echo Medigraph demo loader - Neo4j Aura
echo This loads SYNTHETIC placeholder data. Use a dedicated database.
echo ==================================================
set /p NEO4J_URI=Paste your Neo4j Aura URI (neo4j+s://...): 
set /p NEO4J_USERNAME=Enter your Neo4j username: 
set /p NEO4J_DATABASE=Database name [neo4j]: 
for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "$secure = Read-Host 'Enter your rotated Neo4j password' -AsSecureString; $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure); try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }"`) do set "NEO4J_PASSWORD=%%P"
if "%NEO4J_DATABASE%"=="" set NEO4J_DATABASE=neo4j
if "%NEO4J_URI%"=="" goto missing
if "%NEO4J_USERNAME%"=="" goto missing
if "%NEO4J_PASSWORD%"=="" goto missing
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher 'py' not found. Install Python 3 from https://www.python.org/downloads/ and try again.
  pause
  exit /b 1
)
py -m pip install -r requirements.txt
if errorlevel 1 goto failed
py load_data.py data
if errorlevel 1 goto failed
echo.
echo Finished. Press any key to close.
pause >nul
exit /b 0
:missing
echo Missing a required value. Please run run.bat again.
pause
exit /b 1
:failed
echo The command failed. Check the error above and confirm Aura is running and credentials are correct.
pause
exit /b 1
