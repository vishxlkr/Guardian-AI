@echo off
REM Personal Security Software - Windows Setup Script
REM Run as Administrator for full functionality

echo ========================================
echo Personal Security Software Setup
echo ========================================
echo.

REM Check for admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Administrator privileges required!
    echo Please right-click and select "Run as administrator"
    pause
    exit /b 1
)

REM Check Python installation
echo Checking Python installation...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from python.org
    pause
    exit /b 1
)

REM Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Found Python %PYTHON_VERSION%

REM Create directory structure
echo.
echo Creating directory structure...
if not exist "data\logs" mkdir "data\logs"
if not exist "data\images\intruders" mkdir "data\images\intruders"
if not exist "data\images\authorized" mkdir "data\images\authorized"
if not exist "data\models" mkdir "data\models"
if not exist "data\backups" mkdir "data\backups"
if not exist "config" mkdir "config"
if not exist "src\plugins" mkdir "src\plugins"

REM Create __init__.py files
echo. > "src\__init__.py"
echo. > "src\core\__init__.py"
echo. > "src\modules\__init__.py"
echo. > "src\plugins\__init__.py"
echo. > "src\utils\__init__.py"

echo Directory structure created successfully

REM Install Visual C++ if needed (for dlib)
echo.
echo Checking Visual C++ Redistributable...
reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" >nul 2>&1
if %errorLevel% neq 0 (
    echo WARNING: Visual C++ 2015-2019 Redistributable not found
    echo Download from: https://aka.ms/vs/16/release/vc_redist.x64.exe
    echo.
)

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo.
echo Installing Python dependencies...
echo This may take several minutes...
python -m pip install -r requirements.txt

if %errorLevel% neq 0 (
    echo.
    echo ERROR: Failed to install some dependencies
    echo.
    echo Common solutions:
    echo 1. Install Visual Studio Build Tools
    echo 2. Try: pip install --upgrade setuptools wheel
    echo 3. Install dlib manually: pip install dlib-binary
    pause
    exit /b 1
)

REM Create default config if not exists
if not exist "config\config.yaml" (
    echo.
    echo Creating default configuration...
    python -c "from src.core.config_manager import ConfigManager; ConfigManager()"
)

REM Test camera
echo.
echo Testing camera access...
python main.py test-camera
if %errorLevel% neq 0 (
    echo WARNING: Camera test failed
    echo Please check camera permissions in Windows Settings
)

REM Create desktop shortcut
echo.
echo Creating desktop shortcut...
set DESKTOP=%USERPROFILE%\Desktop
set SHORTCUT=%DESKTOP%\Personal Security.lnk

powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT%'); $Shortcut.TargetPath = '%CD%\main.py'; $Shortcut.Arguments = 'run'; $Shortcut.WorkingDirectory = '%CD%'; $Shortcut.IconLocation = 'imageres.dll,54'; $Shortcut.Save()"

REM Ask about startup
echo.
set /p STARTUP="Add to Windows startup? (Y/N): "
if /i "%STARTUP%"=="Y" (
    echo Adding to startup...
    copy "%SHORTCUT%" "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\"
    echo Added to startup
)

REM Ask about service installation
echo.
set /p SERVICE="Install as Windows service? (Y/N): "
if /i "%SERVICE%"=="Y" (
    echo Installing service...
    python scripts\service_installer.py install
    
    set /p START_SERVICE="Start service now? (Y/N): "
    if /i "%START_SERVICE%"=="Y" (
        net start PersonalSecurityService
    )
)

REM Setup face recognition
echo.
echo ========================================
echo Face Recognition Setup
echo ========================================
echo.
echo Please add your authorized face for recognition.
echo Make sure you have good lighting and look directly at the camera.
echo.
set /p NAME="Enter your name: "
if not "%NAME%"=="" (
    echo.
    echo A camera window will open. Press SPACE to capture your face, Q to quit.
    echo.
    REM This would need a separate capture script
    echo TODO: Implement face capture utility
    REM python scripts\capture_face.py --name "%NAME%"
)

REM Display final instructions
echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Add authorized faces: python main.py add-face --name "Name" --image "photo.jpg"
echo 2. Configure settings: edit config\config.yaml
echo 3. Run the application: python main.py run
echo    Or use the desktop shortcut
echo.
echo For help: python main.py --help
echo.
echo Security Tips:
echo - Keep the application running for continuous protection
echo - Regularly check logs in data\logs\
echo - Update authorized faces as needed
echo - Configure plugins in config\config.yaml
echo.

pause