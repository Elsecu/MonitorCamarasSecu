@echo off
cd /d "%~dp0"
echo [1/3] Creando entorno virtual...
py -m venv venv || goto :error
call venv\Scripts\activate || goto :error
echo [2/3] Instalando dependencias...
python -m pip install --upgrade pip
pip install -r requirements-dev.txt || goto :error
echo [3/3] Generando .exe...
pyinstaller --onefile --noconsole --uac-admin --name MonitorCamaras main.py || goto :error
echo.
echo LISTO: dist\MonitorCamaras.exe
pause
exit /b 0
:error
echo.
echo ERROR. Revisa el mensaje de arriba.
pause
exit /b 1
