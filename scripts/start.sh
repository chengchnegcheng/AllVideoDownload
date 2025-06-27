#!/bin/bash

# AVD Web版本 - 一键启动脚本 v2.1.0
# 支持本地、IP和域名访问的全能视频下载器
# 用法: ./start.sh [command] [mode]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 项目配置
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
LOGS_DIR="$PROJECT_ROOT/logs"
PIDS_FILE="$PROJECT_ROOT/.pids"

# 网络配置
BACKEND_PORT=8000
FRONTEND_PORT=3000
DOMAIN_NAME="www.shcrystal.top"  # 配置的域名

# 创建必要目录
mkdir -p "$LOGS_DIR"

# 打印彩色输出
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_network() {
    echo -e "${CYAN}[NETWORK]${NC} $1"
}

print_tip() {
    echo -e "${PURPLE}[TIP]${NC} $1"
}

# 显示横幅
show_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════╗"
    echo "║              AVD Web版本 v2.1.0                 ║"
    echo "║           全能视频下载器启动脚本                 ║"
    echo "║      支持本地、IP、域名多种访问方式              ║"
    echo "╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 获取本机IP地址
get_local_ip() {
    # 尝试多种方法获取本机IP
    local ip=""
    
    # 方法1: 使用ip命令
    if command -v ip &> /dev/null; then
        ip=$(ip route get 1 2>/dev/null | grep -oP 'src \K\S+' 2>/dev/null || true)
    fi
    
    # 方法2: 使用hostname命令
    if [ -z "$ip" ] && command -v hostname &> /dev/null; then
        ip=$(hostname -I 2>/dev/null | awk '{print $1}' || true)
    fi
    
    # 方法3: 使用ifconfig命令
    if [ -z "$ip" ] && command -v ifconfig &> /dev/null; then
        ip=$(ifconfig 2>/dev/null | grep -E 'inet.*broadcast' | awk '{print $2}' | head -1 || true)
    fi
    
    # 默认值
    if [ -z "$ip" ]; then
        ip="127.0.0.1"
    fi
    
    echo "$ip"
}

# 检查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        return 1
    fi
    return 0
}

# 检查端口是否被占用
check_port() {
    local port=$1
    if command -v lsof &> /dev/null; then
        lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1
    elif command -v netstat &> /dev/null; then
        netstat -an | grep ":$port " | grep -q LISTEN
    elif command -v ss &> /dev/null; then
        ss -ln | grep ":$port " >/dev/null 2>&1
    else
        return 1
    fi
}

# 等待端口可用
wait_for_port() {
    local port=$1
    local timeout=${2:-30}
    local count=0
    
    print_info "等待端口 $port 启动..."
    while [ $count -lt $timeout ]; do
        if check_port $port; then
            print_success "端口 $port 已启动"
            return 0
        fi
        sleep 1
        ((count++))
        if [ $((count % 5)) -eq 0 ]; then
            echo -n "."
        fi
    done
    
    print_error "等待端口 $port 超时 (${timeout}秒)"
    return 1
}

# 测试网络连接
test_network_connection() {
    local host=$1
    local port=$2
    local timeout=${3:-5}
    
    if command -v curl &> /dev/null; then
        curl -s --connect-timeout $timeout "http://$host:$port/health" >/dev/null 2>&1
    elif command -v wget &> /dev/null; then
        wget -q --timeout=$timeout --tries=1 -O /dev/null "http://$host:$port/health" >/dev/null 2>&1
    elif command -v nc &> /dev/null; then
        echo "" | nc -w $timeout $host $port >/dev/null 2>&1
    else
        return 1
    fi
}

# 检查防火墙状态
check_firewall() {
    print_info "检查防火墙配置..."
    
    local needs_config=false
    
    if command -v firewall-cmd &> /dev/null; then
        # 检查firewalld
        if firewall-cmd --state >/dev/null 2>&1; then
            local ports=$(firewall-cmd --list-ports 2>/dev/null || true)
            
            if ! echo "$ports" | grep -q "${FRONTEND_PORT}/tcp"; then
                print_warning "端口 $FRONTEND_PORT 未在防火墙中开放"
                needs_config=true
            fi
            
            if ! echo "$ports" | grep -q "${BACKEND_PORT}/tcp"; then
                print_warning "端口 $BACKEND_PORT 未在防火墙中开放"
                needs_config=true
            fi
            
            if [ "$needs_config" = true ]; then
                print_tip "运行以下命令开放端口:"
                echo "  sudo firewall-cmd --permanent --add-port=${FRONTEND_PORT}/tcp"
                echo "  sudo firewall-cmd --permanent --add-port=${BACKEND_PORT}/tcp"
                echo "  sudo firewall-cmd --reload"
            fi
        fi
    elif command -v ufw &> /dev/null; then
        # 检查ufw
        if ufw status 2>/dev/null | grep -q "Status: active"; then
            if ! ufw status | grep -q "$FRONTEND_PORT"; then
                print_warning "端口 $FRONTEND_PORT 未在UFW中开放"
                needs_config=true
            fi
            
            if ! ufw status | grep -q "$BACKEND_PORT"; then
                print_warning "端口 $BACKEND_PORT 未在UFW中开放"
                needs_config=true
            fi
            
            if [ "$needs_config" = true ]; then
                print_tip "运行以下命令开放端口:"
                echo "  sudo ufw allow $FRONTEND_PORT"
                echo "  sudo ufw allow $BACKEND_PORT"
            fi
        fi
    fi
    
    if [ "$needs_config" = false ]; then
        print_success "防火墙配置正常"
    fi
}

# 检查系统要求
check_system_requirements() {
    print_info "检查系统要求..."
    
    # 检查内存
    if [ -f /proc/meminfo ]; then
        local mem_total=$(grep MemTotal /proc/meminfo | awk '{print $2}')
        local mem_gb=$((mem_total / 1024 / 1024))
        
        if [ $mem_gb -lt 2 ]; then
            print_warning "系统内存较低 (${mem_gb}GB)，建议至少2GB"
        else
            print_success "内存检查通过 (${mem_gb}GB)"
        fi
    fi
    
    # 检查磁盘空间
    local disk_free=$(df "$PROJECT_ROOT" | tail -1 | awk '{print $4}')
    local disk_gb=$((disk_free / 1024 / 1024))
    
    if [ $disk_gb -lt 5 ]; then
        print_warning "磁盘空间较低 (${disk_gb}GB)，建议至少5GB"
    else
        print_success "磁盘空间充足 (${disk_gb}GB)"
    fi
    
    # 检查网络连接
    if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        print_success "网络连接正常"
    else
        print_warning "网络连接可能存在问题"
    fi
}

# 检查Python环境
check_python() {
    print_info "检查Python环境..."
    
    if ! check_command "python3"; then
        print_error "未找到python3，请安装Python 3.8+"
        print_tip "Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
        print_tip "CentOS/RHEL: sudo yum install python3 python3-pip"
        exit 1
    fi
    
    local python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    print_success "Python版本: $python_version"
    
    if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"; then
        print_error "Python版本需要3.8或更高，当前版本: $python_version"
        exit 1
    fi
    
    # 检查pip
    if ! check_command "pip3"; then
        print_warning "未找到pip3，尝试使用python3 -m pip"
    fi
}

# 检查Node.js环境
check_nodejs() {
    print_info "检查Node.js环境..."
    
    if ! check_command "node"; then
        print_error "未找到node，请安装Node.js 16+"
        print_tip "官方安装: https://nodejs.org/"
        print_tip "使用nvm: curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash"
        exit 1
    fi
    
    if ! check_command "npm"; then
        print_error "未找到npm，请安装npm"
        exit 1
    fi
    
    local node_version=$(node -v | sed 's/v//')
    local npm_version=$(npm -v)
    print_success "Node.js版本: $node_version"
    print_success "npm版本: $npm_version"
    
    # 检查Node.js版本
    local major_version=$(echo $node_version | cut -d. -f1)
    if [ $major_version -lt 16 ]; then
        print_warning "Node.js版本较低 ($node_version)，建议使用16+版本"
    fi
}

# 安装后端依赖
install_backend_deps() {
    print_info "配置后端环境..."
    cd "$BACKEND_DIR"
    
    # 检查并创建虚拟环境
    if [ ! -d "venv" ]; then
        print_info "创建Python虚拟环境..."
        python3 -m venv venv
        
        if [ $? -ne 0 ]; then
            print_error "创建虚拟环境失败"
            print_tip "请确保已安装python3-venv: sudo apt install python3-venv"
            exit 1
        fi
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 升级pip
    print_info "升级pip..."
    python -m pip install --upgrade pip
    
    # 检查requirements.txt
    if [ ! -f "requirements.txt" ]; then
        print_error "未找到requirements.txt文件"
        exit 1
    fi
    
    # 安装依赖
    print_info "安装Python依赖包..."
    pip install -r requirements.txt
    
    if [ $? -eq 0 ]; then
        print_success "后端依赖安装完成"
    else
        print_error "后端依赖安装失败"
        exit 1
    fi
}

# 安装前端依赖
install_frontend_deps() {
    print_info "配置前端环境..."
    cd "$FRONTEND_DIR"
    
    # 检查package.json
    if [ ! -f "package.json" ]; then
        print_error "未找到package.json文件"
        exit 1
    fi
    
    if [ ! -d "node_modules" ] || [ ! -f "package-lock.json" ]; then
        print_info "安装Node.js依赖包..."
        npm install
        
        if [ $? -eq 0 ]; then
            print_success "前端依赖安装完成"
        else
            print_error "前端依赖安装失败"
            print_tip "尝试清理缓存: npm cache clean --force"
            print_tip "删除node_modules后重新安装"
            exit 1
        fi
    else
        print_success "前端依赖已存在"
    fi
}

# 启动后端服务
start_backend() {
    print_info "启动后端服务..."
    cd "$BACKEND_DIR"
    
    # 检查端口占用
    if check_port $BACKEND_PORT; then
        print_warning "端口${BACKEND_PORT}已被占用"
        
        # 尝试找到占用进程
        if command -v lsof &> /dev/null; then
            local pid=$(lsof -ti:$BACKEND_PORT)
            if [ -n "$pid" ]; then
                print_info "占用进程PID: $pid"
                print_tip "停止占用进程: kill $pid"
            fi
        fi
        return 1
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 检查main.py
    if [ ! -f "main.py" ]; then
        print_error "未找到main.py文件"
        exit 1
    fi
    
    # 启动后端服务
    print_info "启动Python后端服务..."
    nohup python main.py > "$LOGS_DIR/backend.log" 2>&1 &
    local backend_pid=$!
    echo $backend_pid > "$PIDS_FILE.backend"
    
    print_success "后端服务已启动 (PID: $backend_pid)"
    
    # 等待后端启动
    if wait_for_port $BACKEND_PORT 30; then
        print_success "后端服务启动成功"
        return 0
    else
        print_error "后端服务启动失败"
        print_tip "查看日志: tail -f $LOGS_DIR/backend.log"
        return 1
    fi
}

# 启动前端服务
start_frontend() {
    local mode=${1:-dev}
    print_info "启动前端服务 (模式: $mode)..."
    cd "$FRONTEND_DIR"
    
    # 检查端口占用
    if check_port $FRONTEND_PORT; then
        print_warning "端口${FRONTEND_PORT}已被占用"
        
        # 尝试找到占用进程
        if command -v lsof &> /dev/null; then
            local pid=$(lsof -ti:$FRONTEND_PORT)
            if [ -n "$pid" ]; then
                print_info "占用进程PID: $pid"
                print_tip "停止占用进程: kill $pid"
            fi
        fi
        return 1
    fi
    
    # 启动前端服务
    if [ "$mode" = "prod" ]; then
        # 生产模式：构建并使用serve
        print_info "构建前端项目..."
        npm run build
        
        if [ $? -ne 0 ]; then
            print_error "前端构建失败"
            return 1
        fi
        
        if ! check_command "serve"; then
            print_info "安装serve..."
            npm install -g serve
        fi
        
        print_info "启动生产服务器..."
        nohup serve -s dist -l $FRONTEND_PORT > "$LOGS_DIR/frontend.log" 2>&1 &
    else
        # 开发模式
        print_info "启动开发服务器..."
        nohup npm run dev > "$LOGS_DIR/frontend.log" 2>&1 &
    fi
    
    local frontend_pid=$!
    echo $frontend_pid > "$PIDS_FILE.frontend"
    
    print_success "前端服务已启动 (PID: $frontend_pid)"
    
    # 等待前端启动
    if wait_for_port $FRONTEND_PORT 60; then
        print_success "前端服务启动成功"
        return 0
    else
        print_error "前端服务启动失败"
        print_tip "查看日志: tail -f $LOGS_DIR/frontend.log"
        return 1
    fi
}

# 显示访问地址
show_access_urls() {
    local local_ip=$(get_local_ip)
    
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                  🎉 启动成功!                   ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}📱 访问地址:${NC}"
    echo -e "  ${GREEN}本地访问:${NC} http://localhost:$FRONTEND_PORT"
    echo -e "  ${GREEN}局域网访问:${NC} http://$local_ip:$FRONTEND_PORT"
    
    # 检查域名是否可用
    if [ -n "$DOMAIN_NAME" ]; then
        if nslookup "$DOMAIN_NAME" >/dev/null 2>&1; then
            echo -e "  ${GREEN}域名访问:${NC} http://$DOMAIN_NAME:$FRONTEND_PORT"
        fi
    fi
    
    echo ""
    echo -e "${CYAN}🔧 API服务:${NC}"
    echo -e "  ${GREEN}本地API:${NC} http://localhost:$BACKEND_PORT"
    echo -e "  ${GREEN}局域网API:${NC} http://$local_ip:$BACKEND_PORT"
    echo -e "  ${GREEN}API文档:${NC} http://localhost:$BACKEND_PORT/docs"
    
    echo ""
    echo -e "${CYAN}📋 管理命令:${NC}"
    echo -e "  ${YELLOW}查看日志:${NC} tail -f $LOGS_DIR/backend.log"
    echo -e "  ${YELLOW}查看日志:${NC} tail -f $LOGS_DIR/frontend.log"
    echo -e "  ${YELLOW}停止服务:${NC} $0 stop"
    echo -e "  ${YELLOW}重启服务:${NC} $0 restart"
    echo -e "  ${YELLOW}查看状态:${NC} $0 status"
    
    echo ""
    echo -e "${PURPLE}💡 提示:${NC}"
    echo -e "  • 首次使用建议访问API文档了解接口"
    echo -e "  • 支持YouTube、Bilibili等多平台视频下载"
    echo -e "  • 具备AI字幕生成和翻译功能"
    echo -e "  • 使用Ctrl+C安全停止服务"
    echo ""
}

# Docker模式启动
start_docker() {
    print_info "使用Docker启动服务..."
    
    if ! check_command "docker"; then
        print_error "未找到docker命令"
        print_tip "安装Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! check_command "docker-compose"; then
        print_error "未找到docker-compose命令"
        print_tip "安装Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    cd "$PROJECT_ROOT"
    
    # 检查docker-compose.yml
    if [ ! -f "docker-compose.yml" ]; then
        print_error "未找到docker-compose.yml文件"
        exit 1
    fi
    
    # 构建并启动服务
    print_info "构建和启动Docker容器..."
    docker-compose up -d --build
    
    if [ $? -eq 0 ]; then
        print_success "Docker服务启动成功"
        
        # 等待服务启动
        sleep 5
        
        echo ""
        echo -e "${GREEN}🐳 Docker服务已启动${NC}"
        echo -e "  ${GREEN}前端地址:${NC} http://localhost:$FRONTEND_PORT"
        echo -e "  ${GREEN}后端地址:${NC} http://localhost:$BACKEND_PORT"
        echo -e "  ${GREEN}API文档:${NC} http://localhost:$BACKEND_PORT/docs"
        echo ""
        echo -e "${CYAN}管理命令:${NC}"
        echo -e "  ${YELLOW}查看日志:${NC} docker-compose logs -f"
        echo -e "  ${YELLOW}停止服务:${NC} docker-compose down"
        echo -e "  ${YELLOW}重启服务:${NC} docker-compose restart"
        echo ""
    else
        print_error "Docker服务启动失败"
        print_tip "查看错误: docker-compose logs"
        exit 1
    fi
}

# 停止服务
stop_services() {
    print_info "正在停止所有服务..."
    
    local stopped_count=0
    
    # 停止后端
    if [ -f "$PIDS_FILE.backend" ]; then
        local backend_pid=$(cat "$PIDS_FILE.backend" 2>/dev/null)
        if [ -n "$backend_pid" ] && kill -0 $backend_pid 2>/dev/null; then
            kill $backend_pid 2>/dev/null
            sleep 2
            
            # 强制停止
            if kill -0 $backend_pid 2>/dev/null; then
                kill -9 $backend_pid 2>/dev/null
            fi
            
            print_success "后端服务已停止 (PID: $backend_pid)"
            ((stopped_count++))
        fi
        rm -f "$PIDS_FILE.backend"
    fi
    
    # 停止前端
    if [ -f "$PIDS_FILE.frontend" ]; then
        local frontend_pid=$(cat "$PIDS_FILE.frontend" 2>/dev/null)
        if [ -n "$frontend_pid" ] && kill -0 $frontend_pid 2>/dev/null; then
            kill $frontend_pid 2>/dev/null
            sleep 2
            
            # 强制停止
            if kill -0 $frontend_pid 2>/dev/null; then
                kill -9 $frontend_pid 2>/dev/null
            fi
            
            print_success "前端服务已停止 (PID: $frontend_pid)"
            ((stopped_count++))
        fi
        rm -f "$PIDS_FILE.frontend"
    fi
    
    # 停止可能的残留进程
    pkill -f "npm.*dev" 2>/dev/null && ((stopped_count++)) || true
    pkill -f "serve.*dist" 2>/dev/null && ((stopped_count++)) || true
    pkill -f "python.*main.py" 2>/dev/null && ((stopped_count++)) || true
    
    if [ $stopped_count -gt 0 ]; then
        print_success "已停止 $stopped_count 个服务进程"
    else
        print_info "没有发现运行中的服务"
    fi
    
    # 清理PID文件
    rm -f "$PIDS_FILE".*
    
    print_success "服务停止完成"
}

# 检查服务状态
check_status() {
    print_info "检查服务状态..."
    
    local local_ip=$(get_local_ip)
    local backend_running=false
    local frontend_running=false
    local backend_healthy=false
    local frontend_healthy=false
    
    echo ""
    
    # 检查后端
    if check_port $BACKEND_PORT; then
        print_success "后端端口 $BACKEND_PORT 正在监听"
        backend_running=true
        
        # 测试健康检查
        if test_network_connection "localhost" $BACKEND_PORT; then
            print_success "后端API响应正常"
            backend_healthy=true
        else
            print_warning "后端API无响应"
        fi
    else
        print_warning "后端服务未运行 (端口 $BACKEND_PORT)"
    fi
    
    # 检查前端
    if check_port $FRONTEND_PORT; then
        print_success "前端端口 $FRONTEND_PORT 正在监听"
        frontend_running=true
        
        # 简单检查前端
        if test_network_connection "localhost" $FRONTEND_PORT; then
            print_success "前端服务响应正常"
            frontend_healthy=true
        else
            print_warning "前端服务无响应"
        fi
    else
        print_warning "前端服务未运行 (端口 $FRONTEND_PORT)"
    fi
    
    echo ""
    
    # 显示访问地址
    if [ "$backend_running" = true ] && [ "$frontend_running" = true ]; then
        echo -e "${GREEN}✅ 所有服务运行正常${NC}"
        echo ""
        echo -e "${CYAN}📱 可用访问地址:${NC}"
        echo -e "  🌐 http://localhost:$FRONTEND_PORT"
        echo -e "  🌐 http://$local_ip:$FRONTEND_PORT"
        
        if [ -n "$DOMAIN_NAME" ] && nslookup "$DOMAIN_NAME" >/dev/null 2>&1; then
            echo -e "  🌐 http://$DOMAIN_NAME:$FRONTEND_PORT"
        fi
        
        echo ""
        echo -e "${CYAN}🔧 API地址:${NC}"
        echo -e "  📡 http://localhost:$BACKEND_PORT"
        echo -e "  📡 http://$local_ip:$BACKEND_PORT"
        echo -e "  📚 http://localhost:$BACKEND_PORT/docs"
        
    elif [ "$backend_running" = true ]; then
        print_warning "只有后端服务在运行"
        echo -e "  📡 http://localhost:$BACKEND_PORT"
    elif [ "$frontend_running" = true ]; then
        print_warning "只有前端服务在运行"
        echo -e "  🌐 http://localhost:$FRONTEND_PORT"
    else
        print_error "所有服务都未运行"
        print_tip "使用 '$0 start' 启动服务"
    fi
    
    # 显示PID信息
    echo ""
    echo -e "${CYAN}📊 进程信息:${NC}"
    
    if [ -f "$PIDS_FILE.backend" ]; then
        local backend_pid=$(cat "$PIDS_FILE.backend" 2>/dev/null)
        if [ -n "$backend_pid" ] && kill -0 $backend_pid 2>/dev/null; then
            echo -e "  后端PID: $backend_pid ✅"
        else
            echo -e "  后端PID: $backend_pid ❌ (进程不存在)"
        fi
    fi
    
    if [ -f "$PIDS_FILE.frontend" ]; then
        local frontend_pid=$(cat "$PIDS_FILE.frontend" 2>/dev/null)
        if [ -n "$frontend_pid" ] && kill -0 $frontend_pid 2>/dev/null; then
            echo -e "  前端PID: $frontend_pid ✅"
        else
            echo -e "  前端PID: $frontend_pid ❌ (进程不存在)"
        fi
    fi
    
    echo ""
}

# 网络诊断
diagnose_network() {
    print_info "开始网络诊断..."
    
    local local_ip=$(get_local_ip)
    
    echo ""
    echo -e "${CYAN}🌐 网络配置信息:${NC}"
    echo -e "  本机IP: $local_ip"
    echo -e "  域名: $DOMAIN_NAME"
    echo -e "  前端端口: $FRONTEND_PORT"
    echo -e "  后端端口: $BACKEND_PORT"
    
    echo ""
    echo -e "${CYAN}🔍 连通性测试:${NC}"
    
    # 测试本地回环
    if test_network_connection "127.0.0.1" $BACKEND_PORT; then
        print_success "本地回环连接正常"
    else
        print_error "本地回环连接失败"
    fi
    
    # 测试本机IP
    if test_network_connection "$local_ip" $BACKEND_PORT; then
        print_success "本机IP连接正常"
    else
        print_warning "本机IP连接失败 - 可能是防火墙阻止"
    fi
    
    # 测试域名解析
    if [ -n "$DOMAIN_NAME" ]; then
        if nslookup "$DOMAIN_NAME" >/dev/null 2>&1; then
            print_success "域名解析正常"
            
            # 测试域名连接
            if test_network_connection "$DOMAIN_NAME" $BACKEND_PORT; then
                print_success "域名连接正常"
            else
                print_warning "域名连接失败"
            fi
        else
            print_warning "域名解析失败"
        fi
    fi
    
    # 测试外网连接
    if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        print_success "外网连接正常"
    else
        print_warning "外网连接失败"
    fi
    
    echo ""
    check_firewall
    echo ""
}

# 重启服务
restart_services() {
    local mode=${1:-dev}
    print_info "重启服务 (模式: $mode)..."
    
    stop_services
    echo ""
    sleep 3
    start_services "$mode"
}

# 启动服务
start_services() {
    local mode=${1:-dev}
    
    print_info "启动模式: $mode"
    echo ""
    
    if [ "$mode" = "docker" ]; then
        start_docker
        return $?
    fi
    
    # 系统检查
    check_system_requirements
    echo ""
    
    # 环境检查
    check_python
    check_nodejs
    echo ""
    
    # 防火墙检查
    check_firewall
    echo ""
    
    # 安装依赖
    install_backend_deps
    echo ""
    install_frontend_deps
    echo ""
    
    # 启动服务
    if start_backend; then
        echo ""
        sleep 3  # 等待后端完全启动
        
        if start_frontend "$mode"; then
            show_access_urls
            return 0
        else
            print_error "前端启动失败，正在停止后端服务"
            stop_services
            return 1
        fi
    else
        print_error "后端启动失败"
        print_tip "查看日志: tail -f $LOGS_DIR/backend.log"
        return 1
    fi
}

# 日志查看
show_logs() {
    local service=${1:-both}
    
    case $service in
        backend|back|be)
            print_info "显示后端日志 (按Ctrl+C退出)..."
            tail -f "$LOGS_DIR/backend.log" 2>/dev/null || print_error "后端日志文件不存在"
            ;;
        frontend|front|fe)
            print_info "显示前端日志 (按Ctrl+C退出)..."
            tail -f "$LOGS_DIR/frontend.log" 2>/dev/null || print_error "前端日志文件不存在"
            ;;
        both|all)
            print_info "显示所有日志 (按Ctrl+C退出)..."
            if [ -f "$LOGS_DIR/backend.log" ] && [ -f "$LOGS_DIR/frontend.log" ]; then
                tail -f "$LOGS_DIR/backend.log" "$LOGS_DIR/frontend.log"
            elif [ -f "$LOGS_DIR/backend.log" ]; then
                tail -f "$LOGS_DIR/backend.log"
            elif [ -f "$LOGS_DIR/frontend.log" ]; then
                tail -f "$LOGS_DIR/frontend.log"
            else
                print_error "没有找到日志文件"
            fi
            ;;
        *)
            print_error "未知日志类型: $service"
            print_tip "可用选项: backend, frontend, both"
            ;;
    esac
}

# 清理功能
clean_project() {
    print_info "清理项目文件..."
    
    # 询问确认
    echo -e "${YELLOW}这将删除以下内容:${NC}"
    echo "  • Python虚拟环境 (backend/venv)"
    echo "  • Node.js依赖 (frontend/node_modules)"
    echo "  • 构建文件 (frontend/dist)"
    echo "  • 日志文件 (logs/*)"
    echo "  • PID文件"
    echo ""
    
    read -p "确认清理? [y/N]: " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "取消清理操作"
        return 0
    fi
    
    # 停止服务
    stop_services
    
    # 清理文件
    print_info "清理Python虚拟环境..."
    rm -rf "$BACKEND_DIR/venv"
    
    print_info "清理Node.js依赖..."
    rm -rf "$FRONTEND_DIR/node_modules"
    rm -f "$FRONTEND_DIR/package-lock.json"
    
    print_info "清理构建文件..."
    rm -rf "$FRONTEND_DIR/dist"
    
    print_info "清理日志文件..."
    rm -f "$LOGS_DIR"/*.log
    
    print_info "清理PID文件..."
    rm -f "$PIDS_FILE".*
    
    print_success "项目清理完成"
    print_tip "下次启动时将重新安装所有依赖"
}

# 显示帮助信息
show_help() {
    echo -e "${CYAN}AVD Web版本启动脚本 v2.1.0${NC}"
    echo ""
    echo -e "${YELLOW}用法:${NC}"
    echo "  $0 [command] [options]"
    echo ""
    echo -e "${YELLOW}命令:${NC}"
    echo -e "  ${GREEN}start [mode]${NC}     启动服务"
    echo -e "  ${GREEN}stop${NC}             停止所有服务"
    echo -e "  ${GREEN}restart [mode]${NC}   重启服务"
    echo -e "  ${GREEN}status${NC}           检查服务状态"
    echo -e "  ${GREEN}logs [service]${NC}   查看日志"
    echo -e "  ${GREEN}diagnose${NC}         网络诊断"
    echo -e "  ${GREEN}clean${NC}            清理项目文件"
    echo -e "  ${GREEN}help${NC}             显示帮助信息"
    echo ""
    echo -e "${YELLOW}启动模式:${NC}"
    echo -e "  ${GREEN}dev${NC}              开发模式 (默认，支持热重载)"
    echo -e "  ${GREEN}prod${NC}             生产模式 (构建优化版本)"
    echo -e "  ${GREEN}docker${NC}           Docker容器模式"
    echo ""
    echo -e "${YELLOW}日志选项:${NC}"
    echo -e "  ${GREEN}backend${NC}          查看后端日志"
    echo -e "  ${GREEN}frontend${NC}         查看前端日志"
    echo -e "  ${GREEN}both${NC}             查看所有日志 (默认)"
    echo ""
    echo -e "${YELLOW}使用示例:${NC}"
    echo -e "  ${CYAN}$0 start${NC}              # 开发模式启动"
    echo -e "  ${CYAN}$0 start prod${NC}         # 生产模式启动"
    echo -e "  ${CYAN}$0 start docker${NC}       # Docker模式启动"
    echo -e "  ${CYAN}$0 stop${NC}               # 停止所有服务"
    echo -e "  ${CYAN}$0 restart dev${NC}        # 重启到开发模式"
    echo -e "  ${CYAN}$0 status${NC}             # 检查运行状态"
    echo -e "  ${CYAN}$0 logs backend${NC}       # 查看后端日志"
    echo -e "  ${CYAN}$0 diagnose${NC}           # 网络问题诊断"
    echo -e "  ${CYAN}$0 clean${NC}              # 清理项目文件"
    echo ""
    echo -e "${YELLOW}支持的访问方式:${NC}"
    echo -e "  • 本地访问: http://localhost:3000"
    echo -e "  • IP访问: http://[your-ip]:3000"
    echo -e "  • 域名访问: http://$DOMAIN_NAME:3000"
    echo ""
    echo -e "${PURPLE}更多信息请查看项目文档${NC}"
}

# 主函数
main() {
    show_banner
    
    local command=${1:-start}
    local option=${2:-dev}
    
    case $command in
        start)
            start_services "$option"
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services "$option"
            ;;
        status)
            check_status
            ;;
        logs|log)
            show_logs "$option"
            ;;
        diagnose|diag)
            diagnose_network
            ;;
        clean)
            clean_project
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "未知命令: $command"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 信号处理 - 确保优雅关闭
cleanup_on_exit() {
    echo ""
    print_info "收到退出信号，正在安全停止服务..."
    stop_services
    print_success "安全退出完成"
    exit 0
}

# 注册信号处理
trap cleanup_on_exit INT TERM

# 运行主函数
main "$@" 