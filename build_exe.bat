@echo off
rem Builds dist\Vigil.exe on Windows. Needs Python 3.12 and Node.js 20.
cd /d "%~dp0"
pushd web
call npm ci || exit /b 1
call npx vite build || exit /b 1
popd
python -m pip install --upgrade pyinstaller || exit /b 1
python -m PyInstaller --noconfirm --onefile --console --name Vigil --icon installer\vigil.ico ^
  --add-data "web\dist;web\dist" ^
  --add-data "mask_terms.example.txt;." ^
  --add-data "environment.example.txt;." ^
  alert_console.py || exit /b 1
echo Built dist\Vigil.exe
