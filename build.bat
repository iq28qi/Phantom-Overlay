@echo off
chcp 65001 > nul
echo ==========================================
echo    Phantom Overlay — финальная сборка
echo ==========================================
echo.

:: 1. Виртуальное окружение
if exist "venv\Scripts\activate.bat" (
    echo [1/5] Активирую виртуальное окружение (venv)...
    call venv\Scripts\activate.bat
) else (
    echo [1/5] Внимание: папка venv не найдена! Использую системный Python.
)

echo.
echo [2/5] Установка зависимостей из requirements.txt...
if exist requirements.txt (
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
) else (
    echo requirements.txt не найден, пропускаю.
)

echo.
echo [3/5] Проверка/установка PyInstaller...
python -m pip install pyinstaller

echo.
echo [4/5] Упаковка в .EXE...
:: --collect-all winsdk чинит медиа-модуль
python -m PyInstaller --noconfirm --onefile --windowed ^
    --collect-all winsdk ^
    --icon="icon.ico" ^
    --name="PhantomOverlay" ^
    phantom.py

echo.
echo [5/5] Очистка временных файлов...
if exist build rmdir /s /q build
if exist PhantomOverlay.spec del /q PhantomOverlay.spec

echo.
echo ==========================================
echo ГОТОВО! Итоговый EXE — в папке "dist".
echo ==========================================
pause
