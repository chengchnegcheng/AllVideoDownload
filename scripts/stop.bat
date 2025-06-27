@echo off
setlocal enabledelayedexpansion

REM AVD Web版本 - 停止服务脚本 (Windows)

REM 设置代码页为UTF-8
chcp 65001 >nul

REM 项目根目录
set "PROJECT_ROOT=%~dp0.."
set "PIDS_FILE=%PROJECT_ROOT%\.pids"

REM 颜色定义 (Windows 10+)
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "NC=[0m"

REM 显示横幅
:show_banner
echo %BLUE%==================================
echo    AVD Web版本 - 停止服务
echo    全能视频下载器 v2.0.0
echo ==================================%NC%
echo.
goto :eof

REM 打印彩色输出
:print_info
echo %BLUE%[INFO]%NC% %~1
goto :eof

:print_success
echo %GREEN%[SUCCESS]%NC% %~1
goto :eof

:print_warning
echo %YELLOW%[WARNING]%NC% %~1
goto :eof

:print_error
echo %RED%[ERROR]%NC% %~1
goto :eof

REM 检查端口是否被占用
:check_port
netstat -an | findstr ":%1 " | findstr "LISTENING" >nul
if errorlevel 1 (
    exit /b 1
) else (
    exit /b 0
)

REM 强制停止端口上的进程
:kill_port_process
set "port=%1"
call :print_info "正在停止端口 %port% 上的进程..."

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%port% "') do (
    taskkill /PID %%a /F >nul 2>&1
)

timeout /t 1 /nobreak >nul

call :check_port %port%
if errorlevel 1 (
    call :print_success "端口 %port% 已释放"
) else (
    call :print_warning "端口 %port% 上仍有进程运行"
)
goto :eof

REM 停止Docker服务
:stop_docker
call :print_info "停止Docker服务..."

cd /d "%PROJECT_ROOT%"

if exist "docker-compose.yml" (
    docker-compose down >nul 2>&1
    call :print_success "Docker服务已停止"
) else (
    call :print_warning "未找到docker-compose.yml文件"
)
goto :eof

REM 停止通过PID文件记录的服务
:stop_pid_services
REM 停止后端
if exist "%PIDS_FILE%.backend" (
    for /f %%i in ('type "%PIDS_FILE%.backend"') do (
        taskkill /PID %%i /F >nul 2>&1
        if not errorlevel 1 (
            call :print_success "后端服务已停止 (PID: %%i)"
        ) else (
            call :print_info "后端服务进程不存在"
        )
    )
    del "%PIDS_FILE%.backend" >nul 2>&1
)

REM 停止前端
if exist "%PIDS_FILE%.frontend" (
    for /f %%i in ('type "%PIDS_FILE%.frontend"') do (
        taskkill /PID %%i /F >nul 2>&1
        if not errorlevel 1 (
            call :print_success "前端服务已停止 (PID: %%i)"
        ) else (
            call :print_info "前端服务进程不存在"
        )
    )
    del "%PIDS_FILE%.frontend" >nul 2>&1
)
goto :eof

REM 停止可能的Node.js和Python进程
:stop_node_python_processes
call :print_info "停止相关进程..."

REM 停止npm进程
tasklist /FI "IMAGENAME eq node.exe" /FO CSV | findstr /C:"npm" >nul 2>&1
if not errorlevel 1 (
    taskkill /F /IM "node.exe" /FI "WINDOWTITLE eq npm*" >nul 2>&1
    call :print_success "已停止npm进程"
)

REM 停止Python进程
tasklist /FI "IMAGENAME eq python.exe" /FO CSV | findstr /C:"main.py" >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=2 delims=," %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV ^| findstr /C:"main.py"') do (
        taskkill /PID %%~i /F >nul 2>&1
    )
    call :print_success "已停止Python主进程"
)

REM 强制停止所有可能的进程
taskkill /F /IM "node.exe" >nul 2>&1
taskkill /F /IM "python.exe" >nul 2>&1

goto :eof

REM 清理临时文件
:cleanup_temp_files
call :print_info "清理临时文件..."

REM 清理PID文件
del "%PIDS_FILE%.*" >nul 2>&1

REM 清理可能的锁文件
del "%PROJECT_ROOT%\.lock" >nul 2>&1
del "%PROJECT_ROOT%\backend\.lock" >nul 2>&1
del "%PROJECT_ROOT%\frontend\.lock" >nul 2>&1

call :print_success "临时文件已清理"
goto :eof

REM 显示服务状态
:show_status
echo.
call :print_info "检查服务状态..."

set "any_running=false"

REM 检查常用端口
for %%p in (3000 8000 5173) do (
    call :check_port %%p
    if not errorlevel 1 (
        call :print_warning "端口 %%p 仍在使用中"
        set "any_running=true"
    )
)

REM 检查Docker
docker-compose ps 2>nul | findstr "Up" >nul
if not errorlevel 1 (
    call :print_warning "Docker服务仍在运行"
    set "any_running=true"
)

if "%any_running%"=="false" (
    call :print_success "所有服务已停止"
)
goto :eof

REM 主停止函数
:stop_all_services
call :print_info "开始停止所有AVD Web服务..."

REM 1. 停止PID记录的服务
call :stop_pid_services

REM 2. 停止Docker服务
call :stop_docker

REM 3. 强制停止端口进程
call :kill_port_process 3000
call :kill_port_process 8000
call :kill_port_process 5173

REM 4. 停止相关进程
call :stop_node_python_processes

REM 5. 清理临时文件
call :cleanup_temp_files

REM 6. 显示最终状态
call :show_status

echo.
call :print_success "================ 停止完成 ================"
call :print_info "所有AVD Web服务已停止"
call :print_info "如需重新启动，请运行: scripts\start.bat"
echo =======================================
goto :eof

REM 显示帮助信息
:show_help
echo AVD Web版本停止脚本
echo.
echo 用法:
echo   %~nx0 [选项]
echo.
echo 选项:
echo   --force, -f    强制停止所有相关进程
echo   --docker, -d   仅停止Docker服务
echo   --help, -h     显示帮助信息
echo.
echo 示例:
echo   %~nx0              # 正常停止所有服务
echo   %~nx0 --force      # 强制停止所有服务
echo   %~nx0 --docker     # 仅停止Docker服务
goto :eof

REM 强制停止模式
:force_stop
call :print_warning "强制停止模式"

REM 强制杀死所有相关进程
taskkill /F /IM "node.exe" >nul 2>&1
taskkill /F /IM "python.exe" >nul 2>&1
taskkill /F /IM "cmd.exe" /FI "WINDOWTITLE eq *npm*" >nul 2>&1
taskkill /F /IM "cmd.exe" /FI "WINDOWTITLE eq *vite*" >nul 2>&1

REM 强制停止Docker
docker-compose kill >nul 2>&1
docker-compose down --remove-orphans >nul 2>&1

REM 强制释放端口
for %%p in (3000 8000 5173) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%p "') do (
        taskkill /PID %%a /F >nul 2>&1
    )
)

call :cleanup_temp_files

call :print_success "强制停止完成"
goto :eof

REM 仅停止Docker
:docker_only_stop
call :print_info "仅停止Docker服务"
call :stop_docker
goto :eof

REM 主函数
:main
call :show_banner

set "command=%~1"

if "%command%"=="--force" goto force_stop_main
if "%command%"=="-f" goto force_stop_main
if "%command%"=="--docker" goto docker_only_main
if "%command%"=="-d" goto docker_only_main
if "%command%"=="--help" goto help_main
if "%command%"=="-h" goto help_main
if "%command%"=="help" goto help_main
if "%command%"=="" goto normal_stop_main

call :print_error "未知选项: %command%"
echo.
call :show_help
exit /b 1

:force_stop_main
call :force_stop
goto :eof

:docker_only_main
call :docker_only_stop
goto :eof

:help_main
call :show_help
goto :eof

:normal_stop_main
call :stop_all_services
goto :eof

REM 运行主函数
call :main %* 