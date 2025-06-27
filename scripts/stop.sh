#!/bin/bash

# AVD Web版本 - 停止服务脚本 v2.1.0
# 支持本地、IP和域名访问的全能视频下载器
# 用法: ./stop.sh [command] [options]

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
LOGS_DIR="$PROJECT_ROOT/logs"
PIDS_FILE="$PROJECT_ROOT/.pids"

# 网络配置
BACKEND_PORT=8000
FRONTEND_PORT=3000
DOMAIN_NAME="www.shcrystal.top"

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
    echo -e "${RED}"
    echo "╔══════════════════════════════════════════════════╗"
    echo "║              AVD Web版本 v2.1.0                 ║"
    echo "║           全能视频下载器停止脚本                 ║"
    echo "║          🛑 安全停止所有服务                     ║"
    echo "╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"
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

# 获取端口占用进程信息
get_port_process() {
    local port=$1
    local pids=""
    
    if command -v lsof &> /dev/null; then
        pids=$(lsof -ti :$port 2>/dev/null || true)
    elif command -v netstat &> /dev/null; then
        pids=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1 | grep -v '-' || true)
    elif command -v ss &> /dev/null; then
        pids=$(ss -tlnp 2>/dev/null | grep ":$port " | sed 's/.*pid=\([0-9]*\).*/\1/' || true)
    fi
    
    echo "$pids"
}

# 强制停止端口上的进程
kill_port_process() {
    local port=$1
    local service_name=${2:-"服务"}
    
    if ! check_port $port; then
        print_success "端口 $port 未被占用"
        return 0
    fi
    
    local pids=$(get_port_process $port)
    
    if [ -n "$pids" ]; then
        print_info "正在停止端口 $port 上的 $service_name 进程..."
        
        # 尝试优雅停止
        for pid in $pids; do
            if kill -0 $pid 2>/dev/null; then
                print_info "停止进程 $pid (端口 $port)"
                kill $pid 2>/dev/null || true
            fi
        done
        
        sleep 2
        
        # 检查是否还有进程
        local remaining_pids=$(get_port_process $port)
        if [ -n "$remaining_pids" ]; then
            print_warning "强制停止端口 $port 上的残留进程..."
            for pid in $remaining_pids; do
                if kill -0 $pid 2>/dev/null; then
                    kill -9 $pid 2>/dev/null || true
                fi
            done
            sleep 1
        fi
        
        # 最终检查
        if check_port $port; then
            print_warning "端口 $port 仍被占用，尝试使用 fuser 强制释放"
            if command -v fuser &> /dev/null; then
                fuser -k ${port}/tcp 2>/dev/null || true
                sleep 1
            fi
        fi
        
        if ! check_port $port; then
            print_success "端口 $port ($service_name) 已释放"
        else
            print_error "端口 $port 释放失败"
        fi
    else
        print_warning "无法获取端口 $port 的进程信息"
    fi
}

# 停止Docker服务
stop_docker() {
    print_info "🐳 停止Docker服务..."
    
    cd "$PROJECT_ROOT"
    
    if [ ! -f "docker-compose.yml" ]; then
        print_warning "未找到docker-compose.yml文件"
        return 0
    fi
    
    if ! check_command "docker-compose"; then
        print_error "未找到docker-compose命令"
        return 1
    fi
    
    # 检查是否有容器在运行
    local running_containers=$(docker-compose ps -q 2>/dev/null || true)
    
    if [ -z "$running_containers" ]; then
        print_success "Docker容器未运行"
        return 0
    fi
    
    print_info "停止Docker容器..."
    docker-compose down --remove-orphans 2>/dev/null || {
        print_warning "正常停止失败，尝试强制停止..."
        docker-compose kill 2>/dev/null || true
        docker-compose down --remove-orphans 2>/dev/null || true
    }
    
    # 验证容器是否已停止
    local remaining_containers=$(docker-compose ps -q 2>/dev/null || true)
    if [ -z "$remaining_containers" ]; then
        print_success "Docker服务已停止"
    else
        print_error "部分Docker容器停止失败"
        print_tip "手动清理: docker-compose down --remove-orphans --volumes"
    fi
}

# 停止通过PID文件记录的服务
stop_pid_services() {
    print_info "📋 停止PID记录的服务..."
    
    local stopped_count=0
    
    # 停止后端
    if [ -f "$PIDS_FILE.backend" ]; then
        local backend_pid=$(cat "$PIDS_FILE.backend" 2>/dev/null)
        if [ -n "$backend_pid" ] && kill -0 $backend_pid 2>/dev/null; then
            print_info "停止后端服务 (PID: $backend_pid)"
            kill $backend_pid 2>/dev/null || true
            sleep 2
            
            # 强制停止
            if kill -0 $backend_pid 2>/dev/null; then
                print_warning "强制停止后端服务"
                kill -9 $backend_pid 2>/dev/null || true
            fi
            
            print_success "后端服务已停止 (PID: $backend_pid)"
            ((stopped_count++))
        else
            print_info "后端服务进程不存在或已停止"
        fi
        rm -f "$PIDS_FILE.backend"
    fi
    
    # 停止前端
    if [ -f "$PIDS_FILE.frontend" ]; then
        local frontend_pid=$(cat "$PIDS_FILE.frontend" 2>/dev/null)
        if [ -n "$frontend_pid" ] && kill -0 $frontend_pid 2>/dev/null; then
            print_info "停止前端服务 (PID: $frontend_pid)"
            kill $frontend_pid 2>/dev/null || true
            sleep 2
            
            # 强制停止
            if kill -0 $frontend_pid 2>/dev/null; then
                print_warning "强制停止前端服务"
                kill -9 $frontend_pid 2>/dev/null || true
            fi
            
            print_success "前端服务已停止 (PID: $frontend_pid)"
            ((stopped_count++))
        else
            print_info "前端服务进程不存在或已停止"
        fi
        rm -f "$PIDS_FILE.frontend"
    fi
    
    if [ $stopped_count -eq 0 ]; then
        print_info "没有找到PID记录的服务"
    fi
}

# 停止相关进程
stop_related_processes() {
    print_info "🔄 停止相关进程..."
    
    local killed_count=0
    
    # 定义进程模式和描述
    local processes=(
        "npm.*dev:npm开发服务器"
        "serve.*dist:serve生产服务器"
        "python.*main.py:Python主程序"
        "python.*uvicorn:uvicorn服务器"
        "vite.*dev:Vite开发服务器"
        "node.*vite:Node.js Vite进程"
        "fastapi.*:FastAPI应用"
        "celery.*:Celery任务队列"
    )
    
    for process_info in "${processes[@]}"; do
        local pattern=${process_info%:*}
        local description=${process_info#*:}
        
        if pkill -f "$pattern" 2>/dev/null; then
            print_success "已停止 $description"
            ((killed_count++))
            sleep 0.5
        fi
    done
    
    if [ $killed_count -eq 0 ]; then
        print_info "没有找到相关的运行进程"
    else
        print_success "共停止了 $killed_count 个相关进程"
    fi
}

# 清理临时文件和缓存
cleanup_temp_files() {
    print_info "🧹 清理临时文件..."
    
    local cleaned_count=0
    
    # 清理PID文件
    if rm -f "$PIDS_FILE".* 2>/dev/null; then
        print_success "清理PID文件"
        ((cleaned_count++))
    fi
    
    # 清理锁文件
    local lock_files=(
        "$PROJECT_ROOT/.lock"
        "$PROJECT_ROOT/backend/.lock"
        "$PROJECT_ROOT/frontend/.lock"
        "$PROJECT_ROOT/backend/app.lock"
        "$PROJECT_ROOT/frontend/vite.lock"
    )
    
    for lock_file in "${lock_files[@]}"; do
        if [ -f "$lock_file" ]; then
            rm -f "$lock_file"
            print_success "清理锁文件: $(basename $lock_file)"
            ((cleaned_count++))
        fi
    done
    
    # 清理临时下载文件
    if [ -d "$PROJECT_ROOT/backend/data/downloads" ]; then
        local temp_files=$(find "$PROJECT_ROOT/backend/data/downloads" -name "*.tmp" -o -name "*.temp" 2>/dev/null | wc -l)
        if [ $temp_files -gt 0 ]; then
            find "$PROJECT_ROOT/backend/data/downloads" -name "*.tmp" -o -name "*.temp" -delete 2>/dev/null || true
            print_success "清理下载临时文件 ($temp_files 个)"
            ((cleaned_count++))
        fi
    fi
    
    # 清理Node.js缓存
    if [ -d "$PROJECT_ROOT/frontend/.cache" ]; then
        rm -rf "$PROJECT_ROOT/frontend/.cache"
        print_success "清理前端缓存"
        ((cleaned_count++))
    fi
    
    if [ $cleaned_count -eq 0 ]; then
        print_info "没有需要清理的临时文件"
    else
        print_success "共清理了 $cleaned_count 项临时文件"
    fi
}

# 显示详细的服务状态
show_detailed_status() {
    echo ""
    print_info "🔍 检查服务状态..."
    
    local any_running=false
    local status_info=()
    
    # 检查主要端口
    local ports=("$FRONTEND_PORT:前端服务" "$BACKEND_PORT:后端API" "5173:Vite开发服务器")
    
    for port_info in "${ports[@]}"; do
        local port=${port_info%:*}
        local service=${port_info#*:}
        
        if check_port $port; then
            print_warning "端口 $port ($service) 仍在使用中"
            any_running=true
            
            # 获取进程信息
            local pids=$(get_port_process $port)
            if [ -n "$pids" ]; then
                print_info "  占用进程: $pids"
            fi
        else
            print_success "端口 $port ($service) 已释放"
        fi
    done
    
    # 检查Docker服务
    if command -v docker-compose &> /dev/null; then
        cd "$PROJECT_ROOT"
        local running_containers=$(docker-compose ps -q 2>/dev/null | wc -l)
        if [ $running_containers -gt 0 ]; then
            print_warning "Docker容器仍在运行 ($running_containers 个)"
            any_running=true
        else
            print_success "Docker服务已停止"
        fi
    fi
    
    # 检查相关进程
    local process_patterns=("npm.*dev" "serve.*dist" "python.*main.py" "vite.*dev")
    local running_processes=0
    
    for pattern in "${process_patterns[@]}"; do
        if pgrep -f "$pattern" >/dev/null 2>&1; then
            ((running_processes++))
        fi
    done
    
    if [ $running_processes -gt 0 ]; then
        print_warning "仍有 $running_processes 个相关进程在运行"
        any_running=true
    else
        print_success "所有相关进程已停止"
    fi
    
    echo ""
    
    if [ "$any_running" = false ]; then
        echo -e "${GREEN}✅ 所有AVD Web服务已完全停止${NC}"
        echo ""
        echo -e "${CYAN}📱 启动服务:${NC}"
        echo -e "  ${GREEN}开发模式:${NC} ./scripts/start.sh start"
        echo -e "  ${GREEN}生产模式:${NC} ./scripts/start.sh start prod"
        echo -e "  ${GREEN}Docker模式:${NC} ./scripts/start.sh start docker"
        echo ""
        echo -e "${CYAN}📊 管理命令:${NC}"
        echo -e "  ${GREEN}检查状态:${NC} ./scripts/start.sh status"
        echo -e "  ${GREEN}查看日志:${NC} ./scripts/start.sh logs"
        echo -e "  ${GREEN}网络诊断:${NC} ./scripts/start.sh diagnose"
    else
        echo -e "${YELLOW}⚠️  部分服务仍在运行${NC}"
        echo ""
        print_tip "如需强制停止: $0 --force"
        print_tip "检查详细状态: ./scripts/start.sh status"
    fi
}

# 主停止函数
stop_all_services() {
    print_info "🛑 开始停止所有AVD Web服务..."
    echo ""
    
    # 1. 停止PID记录的服务
    stop_pid_services
    echo ""
    
    # 2. 停止Docker服务
    stop_docker
    echo ""
    
    # 3. 强制停止端口进程
    print_info "🔌 释放网络端口..."
    kill_port_process $FRONTEND_PORT "前端服务"
    kill_port_process $BACKEND_PORT "后端API"
    kill_port_process 5173 "Vite开发服务器"
    echo ""
    
    # 4. 停止相关进程
    stop_related_processes
    echo ""
    
    # 5. 清理临时文件
    cleanup_temp_files
    echo ""
    
    # 6. 显示最终状态
    show_detailed_status
    
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                🎉 停止完成!                     ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
}

# 强制停止模式
force_stop() {
    echo -e "${RED}⚠️  强制停止模式${NC}"
    print_warning "这将强制终止所有相关进程，可能导致数据丢失"
    echo ""
    
    # 询问确认
    read -p "确认强制停止所有服务? [y/N]: " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "取消强制停止操作"
        return 0
    fi
    
    echo ""
    print_info "💀 执行强制停止..."
    
    # 强制杀死所有相关进程
    local force_patterns=(
        "npm.*dev"
        "serve.*dist"  
        "python.*main.py"
        "python.*uvicorn"
        "vite.*dev"
        "node.*vite"
        "fastapi"
        "celery"
    )
    
    for pattern in "${force_patterns[@]}"; do
        if pkill -9 -f "$pattern" 2>/dev/null; then
            print_success "强制停止: $pattern"
        fi
    done
    
    # 强制停止Docker
    cd "$PROJECT_ROOT"
    if [ -f "docker-compose.yml" ]; then
        print_info "强制停止Docker容器..."
        docker-compose kill 2>/dev/null || true
        docker-compose down --remove-orphans --volumes 2>/dev/null || true
    fi
    
    # 强制释放端口
    local force_ports=($FRONTEND_PORT $BACKEND_PORT 5173)
    for port in "${force_ports[@]}"; do
        if command -v fuser &> /dev/null; then
            fuser -k ${port}/tcp 2>/dev/null || true
        fi
        
        # 使用lsof强制关闭
        if command -v lsof &> /dev/null; then
            lsof -ti:$port | xargs -r kill -9 2>/dev/null || true
        fi
    done
    
    # 清理所有临时文件
    cleanup_temp_files
    
    # 清理可能的僵尸进程
    print_info "清理僵尸进程..."
    ps aux | grep -E "(npm|node|python|vite)" | grep -v grep | awk '{print $2}' | xargs -r kill -9 2>/dev/null || true
    
    echo ""
    print_success "💀 强制停止完成"
    
    # 显示状态
    show_detailed_status
}

# 仅停止Docker
docker_only_stop() {
    print_info "🐳 停止Docker服务 (仅Docker模式)"
    echo ""
    stop_docker
    echo ""
    
    # 检查Docker状态
    cd "$PROJECT_ROOT"
    if command -v docker-compose &> /dev/null && [ -f "docker-compose.yml" ]; then
        local running_containers=$(docker-compose ps -q 2>/dev/null | wc -l)
        if [ $running_containers -eq 0 ]; then
            print_success "Docker服务已完全停止"
        else
            print_warning "部分Docker容器仍在运行"
            print_tip "查看状态: docker-compose ps"
        fi
    fi
}

# 快速停止（仅停止主要服务）
quick_stop() {
    print_info "⚡ 快速停止主要服务..."
    echo ""
    
    # 只停止主要端口和PID服务
    stop_pid_services
    echo ""
    
    kill_port_process $FRONTEND_PORT "前端服务"
    kill_port_process $BACKEND_PORT "后端API"
    
    # 清理PID文件
    rm -f "$PIDS_FILE".*
    
    echo ""
    print_success "⚡ 快速停止完成"  
    print_tip "如需完全清理: $0 --force"
}

# 仅清理临时文件
cleanup_only() {
    print_info "🧹 仅执行清理操作..."
    echo ""
    
    cleanup_temp_files
    
    echo ""
    print_success "🧹 清理完成"
}

# 显示帮助信息
show_help() {
    echo -e "${CYAN}AVD Web版本停止脚本 v2.1.0${NC}"
    echo ""
    echo -e "${YELLOW}用法:${NC}"
    echo "  $0 [command] [options]"
    echo ""
    echo -e "${YELLOW}命令:${NC}"
    echo -e "  ${GREEN}stop${NC}             正常停止所有服务 (默认)"
    echo -e "  ${GREEN}force${NC}            强制停止所有服务"
    echo -e "  ${GREEN}docker${NC}           仅停止Docker服务"
    echo -e "  ${GREEN}quick${NC}            快速停止主要服务"
    echo -e "  ${GREEN}cleanup${NC}          仅清理临时文件"
    echo -e "  ${GREEN}status${NC}           检查服务状态"
    echo -e "  ${GREEN}help${NC}             显示帮助信息"
    echo ""
    echo -e "${YELLOW}选项:${NC}"
    echo -e "  ${GREEN}--force, -f${NC}      强制停止所有相关进程"
    echo -e "  ${GREEN}--docker, -d${NC}     仅停止Docker服务"  
    echo -e "  ${GREEN}--quick, -q${NC}      快速停止主要服务"
    echo -e "  ${GREEN}--cleanup, -c${NC}    仅清理临时文件"
    echo -e "  ${GREEN}--help, -h${NC}       显示帮助信息"
    echo ""
    echo -e "${YELLOW}使用示例:${NC}"
    echo -e "  ${CYAN}$0${NC}                    # 正常停止所有服务"
    echo -e "  ${CYAN}$0 stop${NC}               # 正常停止所有服务"
    echo -e "  ${CYAN}$0 force${NC}              # 强制停止所有服务"  
    echo -e "  ${CYAN}$0 --force${NC}            # 强制停止所有服务"
    echo -e "  ${CYAN}$0 docker${NC}             # 仅停止Docker服务"
    echo -e "  ${CYAN}$0 quick${NC}              # 快速停止主要服务"
    echo -e "  ${CYAN}$0 cleanup${NC}            # 仅清理临时文件"
    echo -e "  ${CYAN}$0 status${NC}             # 检查服务状态"
    echo ""
    echo -e "${YELLOW}停止后操作:${NC}"
    echo -e "  • 启动服务: ./scripts/start.sh"
    echo -e "  • 检查状态: ./scripts/start.sh status"  
    echo -e "  • 查看日志: ./scripts/start.sh logs"
    echo ""
    echo -e "${PURPLE}安全提示: 强制停止可能导致数据丢失，请谨慎使用${NC}"
}

# 检查服务状态（简化版）
check_status() {
    print_info "🔍 检查当前服务状态..."
    show_detailed_status
}

# 主函数
main() {
    show_banner
    
    local command=${1:-stop}
    
    case $command in
        stop|"")
            stop_all_services
            ;;
        force|--force|-f)
            force_stop
            ;;
        docker|--docker|-d)
            docker_only_stop
            ;;
        quick|--quick|-q)
            quick_stop
            ;;
        cleanup|--cleanup|-c)
            cleanup_only
            ;;
        status)
            check_status
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
cleanup_on_interrupt() {
    echo ""
    print_warning "收到中断信号，执行强制停止..."
    force_stop
    exit 0
}

# 注册信号处理
trap cleanup_on_interrupt INT TERM

# 运行主函数
main "$@" 