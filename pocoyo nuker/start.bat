@echo off
chcp 65001 > nul
:: Wechsel in das Verzeichnis der Batch-Datei
cd /d "%~dp0"

echo ==================================================
echo Starting DISCORD N U K E (diagnostic start)
echo Folder: %CD%
echo Looking for pocoyo nuker.py...
if exist "pocoyo nuker.py" (
    echo Found pocoyo nuker.py
) else (
    echo ERROR: pocoyo nuker.py not found in this folder.
    echo Make sure the file is named exactly "pocoyo nuker.py" and is in the same directory as this start.bat.
    pause
    exit /b 1
)

echo.
echo Checking for Python...
where python >nul 2>&1
if %ERRORLEVEL%==0 (
    echo python found via PATH
    echo Running: python -u "pocoyo nuker.py"
    python -u "pocoyo nuker.py"
    echo.
    echo Program exited. (python)
    pause
    exit /b 0
)

echo python not found in PATH, trying the py launcher...
where py >nul 2>&1
if %ERRORLEVEL%==0 (
    echo py launcher found
    echo Running: py -3 -u "pocoyo nuker.py"
    py -3 -u "pocoyo nuker.py"
    echo.
    echo Program exited. (py launcher)
    pause
    exit /b 0
)

echo No python or py launcher found.
echo Possible fixes:
echo  - Install Python 3 and check "Add Python to PATH" during installation.
echo  - Or run this script from a machine that has python in PATH.
echo.
pause
exit /b 1