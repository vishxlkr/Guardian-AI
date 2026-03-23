"""
Simple auto-start solution without Windows service complexity
This creates shortcuts and scheduled tasks instead
"""

import os
import sys
import subprocess
from pathlib import Path
import ctypes

def create_vbs_launcher():
    """Create a VBS script to run the app hidden"""
    vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{Path.cwd()}"
WshShell.Run "cmd /c ""{sys.executable}"" main.py run", 0
Set WshShell = Nothing
'''
    
    vbs_file = Path("start_hidden.vbs")
    vbs_file.write_text(vbs_content)
    print(f"✓ Created hidden launcher: {vbs_file}")
    return vbs_file

def create_batch_launcher():
    """Create a batch file to run the app"""
    bat_content = f'''@echo off
cd /d "{Path.cwd()}"
echo Starting Personal Security Software...
"{sys.executable}" main.py run
pause
'''
    
    bat_file = Path("start_security.bat")
    bat_file.write_text(bat_content)
    print(f"✓ Created batch launcher: {bat_file}")
    return bat_file

def add_to_startup_folder():
    """Add shortcut to Windows startup folder"""
    try:
        import win32com.client
        
        # Get startup folder
        shell = win32com.client.Dispatch("WScript.Shell")
        startup_folder = shell.SpecialFolders("Startup")
        
        # Create shortcut
        shortcut_path = os.path.join(startup_folder, "PersonalSecurity.lnk")
        shortcut = shell.CreateShortCut(shortcut_path)
        
        # Use VBS for hidden start
        vbs_file = create_vbs_launcher()
        shortcut.TargetPath = str(vbs_file.absolute())
        shortcut.WorkingDirectory = str(Path.cwd())
        shortcut.Description = "Personal Security Software"
        shortcut.Save()
        
        print(f"✓ Added to startup folder: {shortcut_path}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to add to startup: {e}")
        return False

def create_scheduled_task():
    """Create a scheduled task for more reliable startup"""
    task_name = "PersonalSecurityAutoStart"
    
    # Create task XML
    task_xml = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Start Personal Security Software on login</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{sys.executable}</Command>
      <Arguments>main.py run</Arguments>
      <WorkingDirectory>{Path.cwd()}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>'''
    
    # Save XML
    xml_file = Path("task.xml")
    xml_file.write_text(task_xml, encoding='utf-16')
    
    try:
        # Delete existing task
        subprocess.run(["schtasks", "/delete", "/tn", task_name, "/f"], capture_output=True)
        
        # Create new task
        result = subprocess.run([
            "schtasks", "/create", "/xml", str(xml_file), "/tn", task_name
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✓ Created scheduled task: {task_name}")
            xml_file.unlink()  # Clean up
            return True
        else:
            print(f"❌ Failed to create task: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error creating task: {e}")
    
    return False

def create_desktop_shortcuts():
    """Create desktop shortcuts for easy access"""
    desktop = Path.home() / "Desktop"
    
    # Start shortcut
    start_bat = f'''@echo off
cd /d "{Path.cwd()}"
start "Personal Security" /min cmd /c "{sys.executable}" main.py run
echo Personal Security started in background
timeout /t 2
'''
    
    start_file = desktop / "Start Personal Security.bat"
    start_file.write_text(start_bat)
    print(f"✓ Created desktop shortcut: {start_file.name}")
    
    # Stop shortcut  
    stop_bat = f'''@echo off
echo Stopping Personal Security...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Personal Security*"
echo Done
pause
'''
    
    stop_file = desktop / "Stop Personal Security.bat"
    stop_file.write_text(stop_bat)
    print(f"✓ Created desktop shortcut: {stop_file.name}")

def main():
    print("🚀 Personal Security - Simple Auto-Start Setup")
    print("=" * 50)
    print("\nThis will set up auto-start WITHOUT using Windows services")
    print("(Much simpler and more reliable!)\n")
    
    # Create launchers
    vbs_file = create_vbs_launcher()
    bat_file = create_batch_launcher()
    
    # Add to startup
    print("\n📁 Setting up auto-start...")
    startup_ok = add_to_startup_folder()
    
    # Create scheduled task as backup
    task_ok = create_scheduled_task()
    
    # Create desktop shortcuts
    print("\n🖥️ Creating desktop shortcuts...")
    create_desktop_shortcuts()
    
    # Create management script
    manage_content = f'''@echo off
:menu
cls
echo ========================================
echo Personal Security Management
echo ========================================
echo 1. Start Security System
echo 2. Stop Security System  
echo 3. Check if Running
echo 4. Enable Auto-Start
echo 5. Disable Auto-Start
echo 6. Exit
echo ========================================
set /p choice=Enter choice (1-6): 

if "%choice%"=="1" goto start
if "%choice%"=="2" goto stop
if "%choice%"=="3" goto check
if "%choice%"=="4" goto enable
if "%choice%"=="5" goto disable
if "%choice%"=="6" exit
goto menu

:start
echo Starting Personal Security...
cd /d "{Path.cwd()}"
start "Personal Security" /min "{sys.executable}" main.py run
echo Started in background!
pause
goto menu

:stop
echo Stopping Personal Security...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Personal Security*"
pause
goto menu

:check
echo Checking if running...
tasklist | findstr python
pause
goto menu

:enable
schtasks /enable /tn PersonalSecurityAutoStart
echo Auto-start enabled!
pause
goto menu

:disable
schtasks /disable /tn PersonalSecurityAutoStart
echo Auto-start disabled!
pause
goto menu
'''
    
    manage_file = Path("manage_security.bat")
    manage_file.write_text(manage_content)
    print(f"\n✓ Created management tool: {manage_file}")
    
    print("\n" + "=" * 50)
    print("✅ SETUP COMPLETE!")
    print("=" * 50)
    
    print("\n🎯 Quick Start Options:")
    print("\n1. MANUAL START (Recommended for testing):")
    print("   - Double-click: start_security.bat")
    print("   - Or run: python main.py run")
    
    print("\n2. AUTO-START is now configured:")
    if startup_ok:
        print("   ✓ Startup folder shortcut created")
    if task_ok:
        print("   ✓ Scheduled task created")
    
    print("\n3. DESKTOP SHORTCUTS created:")
    print("   - Start Personal Security.bat")
    print("   - Stop Personal Security.bat")
    
    print("\n4. MANAGEMENT TOOL:")
    print("   - Run: manage_security.bat")
    
    print("\n💡 The app will start automatically on next login!")
    print("   To test now, just double-click 'start_security.bat'")

if __name__ == "__main__":
    main()
    input("\nPress Enter to exit...")