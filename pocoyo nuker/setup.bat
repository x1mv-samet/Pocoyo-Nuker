@echo off
echo ============================================
echo   Setup for DISCORD NUKE Tool
echo   Installing required Python packages...
echo ============================================

:: upgrade pip
python -m pip install --upgrade pip

:: install required libs
pip install discord.py

echo.
echo ============================================
echo   Installation complete!
echo   You can now run: python nuke_gui.py
echo ============================================

pause
