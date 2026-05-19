@echo off
setlocal

cd /d "%~dp0"

python -m pip install pyinstaller
python -m pip install customtkinter

python -m PyInstaller --onefile --windowed ^
--hidden-import=customtkinter ^
main.py

echo.
echo Executable created in the dist folder.
pause