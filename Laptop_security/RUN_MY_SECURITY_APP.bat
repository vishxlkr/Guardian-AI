@echo off
:: =============================================
:: PERSONAL SECURITY SOFTWARE - INSTANT RUNNER
:: Just save this file and double-click!
:: =============================================

cls
color 0A
echo.
echo  ╔═══════════════════════════════════════════╗
echo  ║   PERSONAL SECURITY SOFTWARE              ║
echo  ║   Face Recognition Protection System      ║
echo  ╚═══════════════════════════════════════════╝
echo.

:: Go to your project directory
E:
cd "E:\pytorch\Deep Learning for  Computer Vision\Laptop_security\Laptop_security"

:: Check if we're in the right place
if not exist "main.py" (
    echo  [ERROR] main.py not found in current directory!
    echo  Please make sure this file is in your project folder.
    pause
    exit /b 1
)

echo   Project directory found
echo   Checking conda environment 'shiv'...

:: Check if conda environment exists
"E:\Anaconda\Scripts\conda.exe" env list | findstr "shiv" >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Conda environment 'shiv' not found!
    echo   Please create it with: conda create -n shiv python
    pause
    exit /b 1
)

echo   Conda environment 'shiv' found
echo   Checking Python and packages...

:: Check if OpenCV is available in the environment
"E:\Anaconda\Scripts\conda.exe" run -n shiv python -c "import cv2; print('OpenCV version:', cv2.__version__)" 2>nul
if errorlevel 1 (
    echo   [WARNING] OpenCV (cv2) not found in environment 'shiv'
    echo   Please install it with: conda activate shiv ^&^& conda install opencv-python
    pause
    exit /b 1
)

echo   All packages are available
echo.
echo  ═════════════════════════════════════════════
echo.
echo  Choose how to run:
echo  1. Run in THIS window (see all messages)
echo  2. Run in BACKGROUND (minimized)
echo  3. Exit
echo.
set /p choice="Enter your choice (1-3): "

if "%choice%"=="1" goto foreground
if "%choice%"=="2" goto background
if "%choice%"=="3" exit
goto :choice

:foreground
echo.
echo  Starting Personal Security (foreground mode)...
echo  Press Ctrl+C to stop
echo.
echo  ═════════════════════════════════════════════
echo.
"E:\Anaconda\Scripts\conda.exe" run -n shiv python main.py run
pause
exit

:background
echo.
echo  Starting Personal Security (background mode)...
start "Personal Security Monitor" /min cmd /c ""E:\Anaconda\Scripts\conda.exe" run -n shiv python main.py run"
echo.
echo  ╔═══════════════════════════════════════════╗
echo  ║      SECURITY SYSTEM NOW RUNNING!         ║
echo  ║                                           ║
echo  ║   The app is monitoring in background     ║
echo  ║   Check the taskbar for the window        ║
echo  ║                                           ║
echo  ║   To stop: Close the minimized window     ║
echo  ╚═══════════════════════════════════════════╝
echo.
echo  Your computer is now protected!
echo.
pause
exit