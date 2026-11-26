@echo off
title Cifra ao Vivo v2.1

echo.
echo  ============================================
echo   Cifra ao Vivo v2.1 - Iniciando...
echo  ============================================
echo.

cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 goto :sem_python

if exist ".deps_ok" goto :iniciar

echo  Instalando dependencias - pode demorar alguns minutos...
echo.
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 goto :erro_deps
echo ok> .deps_ok
echo.
echo  Dependencias instaladas com sucesso!
echo.

:iniciar
if not exist "_uploads" mkdir _uploads

echo  Iniciando servidor em http://localhost:8000
echo  Pressione Ctrl+C para encerrar.
echo.

start "" cmd /c "timeout /t 3 >nul && start http://localhost:8000"

python -m uvicorn local_engine.api.main:app --host 127.0.0.1 --port 8000
if errorlevel 1 echo. & echo  ERRO ao iniciar o servidor. Veja mensagem acima.

echo.
echo  Servidor encerrado.
pause
exit /b 0

:sem_python
echo  ERRO: Python nao encontrado.
echo  Baixe em https://www.python.org/downloads/
echo  Marque "Add Python to PATH" na instalacao.
pause
exit /b 1

:erro_deps
echo.
echo  ERRO ao instalar dependencias. Veja mensagem acima.
pause
exit /b 1
