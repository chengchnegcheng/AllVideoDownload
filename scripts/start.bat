@echo off
setlocal enabledelayedexpansion

REM AVD Web版本 - 一键启动脚本 (Windows)
REM 用法: start.bat [command] [mode]
REM command: start, stop, restart, status, help
REM mode: dev(开发模式), prod(生产模式), docker(Docker模式)

REM 设置代码页为UTF-8
chcp 65001 >nul

REM 项目根目录
set "PROJECT_ROOT=%~dp0.."
set "BACKEND_DIR=%PROJECT_ROOT%\backend"
set "FRONTEND_DIR=%PROJECT_ROOT%\frontend"
set "LOGS_DIR=%PROJECT_ROOT%\logs"
set "PIDS_FILE=%PROJECT_ROOT%\.pids"

REM 创建日志目录
if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%"

REM 颜色定义 (Windows 10+)
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "NC=[0m"

REM 显示横幅
:show_banner
echo %BLUE%==================================
echo    AVD Web版本 - 启动脚本
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

REM 检查命令是否存在
:check_command
where %1 >nul 2>&1
if errorlevel 1 (
    call :print_error "未找到命令: %1"
    exit /b 1
)
goto :eof

REM 检查端口是否被占用
:check_port
netstat -an | findstr ":%1 " | findstr "LISTENING" >nul
if errorlevel 1 (
    exit /b 1
) else (
    exit /b 0
)

REM 等待端口可用
:wait_for_port
set "port=%1"
set "timeout=%2"
if "%timeout%"=="" set "timeout=30"
set "count=0"

call :print_info "等待端口 %port% 可用..."
:wait_loop
call :check_port %port%
if not errorlevel 1 (
    call :print_success "端口 %port% 已可用"
    exit /b 0
)
timeout /t 1 /nobreak >nul
set /a count+=1
if %count% lss %timeout% goto wait_loop

call :print_error "等待端口 %port% 超时"
exit /b 1

REM 检查Python环境
:check_python
call :print_info "检查Python环境..."

call :check_command python
if errorlevel 1 (
    call :print_error "请安装Python 3.8+"
    exit /b 1
)

for /f "tokens=*" %%i in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set "python_version=%%i"
call :print_info "Python版本: %python_version%"

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"
if errorlevel 1 (
    call :print_error "Python版本需要3.8或更高"
    exit /b 1
)
goto :eof

REM 检查Node.js环境
:check_nodejs
call :print_info "检查Node.js环境..."

call :check_command node
if errorlevel 1 (
    call :print_error "请安装Node.js 16+"
    exit /b 1
)

call :check_command npm
if errorlevel 1 (
    call :print_error "请安装npm"
    exit /b 1
)

for /f "tokens=*" %%i in ('node -v') do set "node_version=%%i"
call :print_info "Node.js版本: %node_version%"
goto :eof

REM 安装后端依赖
:install_backend_deps
call :print_info "安装后端依赖..."
cd /d "%BACKEND_DIR%"

REM 检查并创建虚拟环境
if not exist "venv" (
    call :print_info "创建Python虚拟环境..."
    python -m venv venv
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 升级pip
python -m pip install --upgrade pip

REM 安装依赖
pip install -r requirements.txt

call :print_success "后端依赖安装完成"
goto :eof

REM 安装前端依赖
:install_frontend_deps
call :print_info "安装前端依赖..."
cd /d "%FRONTEND_DIR%"

if not exist "node_modules" (
    npm install
) else (
    call :print_info "前端依赖已存在，跳过安装"
)

call :print_success "前端依赖安装完成"
goto :eof

REM 启动后端服务
:start_backend
call :print_info "启动后端服务..."
cd /d "%BACKEND_DIR%"

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 检查端口8000
call :check_port 8000
if not errorlevel 1 (
    call :print_warning "端口8000已被占用，请检查是否有其他实例在运行"
    exit /b 1
)

REM 启动后端服务
start /B python main.py > "%LOGS_DIR%\backend.log" 2>&1

REM 获取进程ID并保存
for /f "tokens=2" %%i in ('tasklist /fi "imagename eq python.exe" /fo table /nh ^| findstr /v "INFO:"') do (
    echo %%i > "%PIDS_FILE%.backend"
    set "backend_pid=%%i"
    goto :found_backend_pid
)
:found_backend_pid

call :print_success "后端服务已启动 (PID: %backend_pid%)"

REM 等待后端启动
call :wait_for_port 8000 30
if errorlevel 1 (
    call :print_error "后端服务启动失败"
    exit /b 1
)

call :print_success "后端服务启动成功: http://localhost:8000"
goto :eof

REM 启动前端服务
:start_frontend
call :print_info "启动前端服务..."
cd /d "%FRONTEND_DIR%"

REM 检查端口3000
call :check_port 3000
if not errorlevel 1 (
    call :print_warning "端口3000已被占用，请检查是否有其他实例在运行"
    exit /b 1
)

REM 启动前端服务
if "%~1"=="prod" (
    REM 生产模式：构建并使用serve
    call :print_info "构建前端项目..."
    npm run build
    
    call :check_command serve
    if errorlevel 1 (
        call :print_info "安装serve..."
        npm install -g serve
    )
    
    start /B serve -s dist -l 3000 > "%LOGS_DIR%\frontend.log" 2>&1
) else (
    REM 开发模式
    start /B npm run dev > "%LOGS_DIR%\frontend.log" 2>&1
)

REM 获取进程ID并保存
for /f "tokens=2" %%i in ('tasklist /fi "imagename eq node.exe" /fo table /nh ^| findstr /v "INFO:"') do (
    echo %%i > "%PIDS_FILE%.frontend"
    set "frontend_pid=%%i"
    goto :found_frontend_pid
)
:found_frontend_pid

call :print_success "前端服务已启动 (PID: %frontend_pid%)"

REM 等待前端启动
call :wait_for_port 3000 30
if errorlevel 1 (
    call :print_error "前端服务启动失败"
    exit /b 1
)

call :print_success "前端服务启动成功: http://localhost:3000"
goto :eof

REM Docker模式启动
:start_docker
call :print_info "使用Docker启动服务..."

call :check_command docker
if errorlevel 1 (
    call :print_error "请安装Docker"
    exit /b 1
)

call :check_command docker-compose
if errorlevel 1 (
    call :print_error "请安装Docker Compose"
    exit /b 1
)

cd /d "%PROJECT_ROOT%"

REM 构建并启动服务
docker-compose up -d --build

if not errorlevel 1 (
    call :print_success "Docker服务启动成功"
    call :print_info "前端地址: http://localhost:3000"
    call :print_info "后端地址: http://localhost:8000"
    call :print_info "查看日志: docker-compose logs -f"
) else (
    call :print_error "Docker服务启动失败"
    exit /b 1
)
goto :eof

REM 停止服务
:stop_services
call :print_info "停止所有服务..."

REM 停止后端
if exist "%PIDS_FILE%.backend" (
    for /f %%i in ('type "%PIDS_FILE%.backend"') do (
        taskkill /PID %%i /F >nul 2>&1
        if not errorlevel 1 (
            call :print_success "后端服务已停止 (PID: %%i)"
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
        )
    )
    del "%PIDS_FILE%.frontend" >nul 2>&1
)

REM 停止可能的Node.js进程
taskkill /F /IM "node.exe" >nul 2>&1
taskkill /F /IM "python.exe" >nul 2>&1

call :print_success "所有服务已停止"
goto :eof

REM 检查服务状态
:check_status
call :print_info "检查服务状态..."

set "backend_running=false"
set "frontend_running=false"

REM 检查后端
call :check_port 8000
if not errorlevel 1 (
    call :print_success "后端服务运行中 (端口: 8000)"
    set "backend_running=true"
) else (
    call :print_warning "后端服务未运行"
)

REM 检查前端
call :check_port 3000
if not errorlevel 1 (
    call :print_success "前端服务运行中 (端口: 3000)"
    set "frontend_running=true"
) else (
    call :print_warning "前端服务未运行"
)

if "%backend_running%"=="true" if "%frontend_running%"=="true" (
    call :print_success "所有服务运行正常"
    echo.
    echo 访问地址:
    echo   前端: http://localhost:3000
    echo   后端: http://localhost:8000
    echo   API文档: http://localhost:8000/docs
)
goto :eof

REM 重启服务
:restart_services
call :print_info "重启服务..."
call :stop_services
timeout /t 2 /nobreak >nul
call :start_services %1
goto :eof

REM 启动服务
:start_services
set "mode=%~1"
if "%mode%"=="" set "mode=dev"

call :print_info "启动模式: %mode%"

if "%mode%"=="docker" (
    call :start_docker
    goto :eof
)

REM 检查环境
call :check_python
if errorlevel 1 exit /b 1

call :check_nodejs
if errorlevel 1 exit /b 1

REM 安装依赖
call :install_backend_deps
if errorlevel 1 exit /b 1

call :install_frontend_deps
if errorlevel 1 exit /b 1

REM 启动服务
call :start_backend
if errorlevel 1 exit /b 1

timeout /t 3 /nobreak >nul

call :start_frontend %mode%
if errorlevel 1 (
    call :print_error "前端启动失败，停止后端服务"
    call :stop_services
    exit /b 1
)

echo.
call :print_success "================ 启动完成 ================"
call :print_success "前端地址: http://localhost:3000"
call :print_success "后端地址: http://localhost:8000"
call :print_success "API文档: http://localhost:8000/docs"
call :print_info "查看日志: type %LOGS_DIR%\backend.log"
call :print_info "查看日志: type %LOGS_DIR%\frontend.log"
call :print_info "停止服务: scripts\start.bat stop"
echo =======================================
goto :eof

REM 显示帮助信息
:show_help
echo AVD Web版本启动脚本
echo.
echo 用法:
echo   %~nx0 [command] [mode]
echo.
echo 命令:
echo   start [mode]  启动服务 (默认: dev)
echo   stop          停止服务
echo   restart [mode] 重启服务
echo   status        检查服务状态
echo   help          显示帮助信息
echo.
echo 模式:
echo   dev           开发模式 (热重载)
echo   prod          生产模式 (构建优化)
echo   docker        Docker容器模式
echo.
echo 示例:
echo   %~nx0 start dev      # 开发模式启动
echo   %~nx0 start prod     # 生产模式启动
echo   %~nx0 start docker   # Docker模式启动
echo   %~nx0 stop           # 停止所有服务
echo   %~nx0 restart dev    # 重启服务
echo   %~nx0 status         # 检查状态
goto :eof

REM 主函数
:main
call :show_banner

set "command=%~1"
set "mode=%~2"

if "%command%"=="" set "command=start"

if "%command%"=="start" (
    call :start_services %mode%
) else if "%command%"=="stop" (
    call :stop_services
) else if "%command%"=="restart" (
    call :restart_services %mode%
) else if "%command%"=="status" (
    call :check_status
) else if "%command%"=="help" (
    call :show_help
) else if "%command%"=="--help" (
    call :show_help
) else if "%command%"=="-h" (
    call :show_help
) else (
    call :print_error "未知命令: %command%"
    echo.
    call :show_help
    exit /b 1
)

goto :eof

REM 运行主函数
call :main %* 