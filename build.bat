@echo off
chcp 65001 > nul
echo ==========================================
echo    Финальная сборка Phantom Overlay
echo ==========================================
echo.

:: 1. Проверяем наличие виртуального окружения и активируем его
if exist "venv\Scripts\activate.bat" (
    echo [1/4] Активирую виртуальное окружение (venv)...
    call venv\Scripts\activate.bat
) else (
    echo [1/4] Внимание: папка venv не найдена! Использую системный Python.
)

echo.
echo [2/4] Проверка сборщика...
python -m pip install pyinstaller

echo.
echo [3/4] Упаковка в .EXE...
:: Флаг --collect-all winsdk решает проблему с библиотекой музыки
python -m PyInstaller --noconfirm --onefile --windowed --collect-all winsdk --icon="icon.ico" --name="PhantomOverlay" phantom.py

echo.
echo [4/4] Очистка временных файлов...
if exist build rmdir /s /q build
if exist PhantomOverlay.spec del /q PhantomOverlay.spec

echo.
echo ==========================================
echo ГОТОВО! Проверь папку "dist".
echo ==========================================
pause