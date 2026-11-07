@echo off
REM ============================================================
REM  Script de build Greed pour Windows 11
REM  Génère dist\Greed\Greed.exe + tous les assets
REM  Pré-requis : Python 3.10+, pip
REM ============================================================

echo [1/3] Installation des dependances...
pip install pyinstaller pygame-ce

echo [2/3] Compilation avec PyInstaller...
pyinstaller --clean --noconfirm greed.spec

echo [3/3] Build termine !
echo Votre jeu se trouve dans :  dist\Greed\Greed.exe
pause
