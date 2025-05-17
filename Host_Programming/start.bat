@echo off
REM 内部批处理，由 VBScript 静默调用

REM 获取当前批处理文件所在的目录路径
SET "CURRENT_DIR=%~dp0"

REM 设置虚拟环境的路径
SET "VENV_PATH=%CURRENT_DIR%venv"

REM 设置主程序脚本的路径
SET "MAIN_SCRIPT=%CURRENT_DIR%splash.py"

REM 激活虚拟环境并运行主程序
CALL "%VENV_PATH%\Scripts\activate.bat"
IF EXIST "%VENV_PATH%\Scripts\python.exe" (
    IF EXIST "%MAIN_SCRIPT%" (
        "%VENV_PATH%\Scripts\python.exe" "%MAIN_SCRIPT%"
    )
)
exit /b