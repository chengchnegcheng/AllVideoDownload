#!/bin/bash

# AVD Web版本 - 停止服务脚本 (Linux)
# 精确停止前后端服务，不影响其他服务

# 设置颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)
PIDS_FILE="$PROJECT_ROOT/.pids"

# 打印函数
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

# 显示横幅
show_banner() {
    echo -e "${BLUE}=================================="
    echo "    AVD Web版本 - 停止服务"
    echo "    全能视频下载器 v2.1.0"
    echo -e "==================================${NC}"
    echo
}

# 检查端口是否被占用
check_port() {
    local port=$1
    netstat -tlnp 2>/dev/null | grep ":$port " >/dev/null
    return $?
}

# 获取占用端口的进程PID
get_port_pid() {
    local port=$1
    netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1
}

# 检查进程是否属于当前项目
is_project_process() {
    local pid=$1
    if [[ -z "$pid" || "$pid" == "-" ]]; then
        return 1
    fi
    
    # 获取进程的工作目录和命令行
    local cwd=$(readlink -f "/proc/$pid/cwd" 2>/dev/null)
    local cmdline=$(cat "/proc/$pid/cmdline" 2>/dev/null | tr '\0' ' ')
    
    # 检查是否在项目目录下运行
    if [[ "$cwd" =~ "$PROJECT_ROOT" ]]; then
        return 0
    fi
    
    # 检查命令行是否包含项目相关内容
    if [[ "$cmdline" =~ "$PROJECT_ROOT" ]] || [[ "$cmdline" =~ "main.py" ]] || [[ "$cmdline" =~ "vite.*3000" ]] || [[ "$cmdline" =~ "npm.*serve" ]]; then
        return 0
    fi
    
    return 1
}

# 安全停止端口上的进程（只停止项目相关进程）
kill_port_process() {
    local port=$1
    print_info "检查端口 $port 上的进程..."
    
    # 获取所有占用该端口的PID
    local pids=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1 | sort -u)
    
    local found_project_process=false
    
        for pid in $pids; do
        if [[ -n "$pid" && "$pid" != "-" ]]; then
            # 检查是否是项目相关进程
            if is_project_process "$pid"; then
                found_project_process=true
                print_info "停止项目进程 PID: $pid (端口 $port)"
                
                # 先尝试温和停止
                kill "$pid" 2>/dev/null
        sleep 2
        
                # 检查进程是否还在运行
                if kill -0 "$pid" 2>/dev/null; then
                    print_warning "进程 $pid 未响应，强制停止..."
                    kill -9 "$pid" 2>/dev/null
                    sleep 1
                fi
                
                if ! kill -0 "$pid" 2>/dev/null; then
                    print_success "进程 $pid 已停止"
                else
                    print_error "无法停止进程 $pid"
                fi
            else
                local cmdline=$(cat "/proc/$pid/cmdline" 2>/dev/null | tr '\0' ' ')
                print_info "跳过非项目进程 PID: $pid (命令: ${cmdline:0:50}...)"
            fi
        fi
    done
        
    if [[ "$found_project_process" == "false" ]]; then
        if check_port "$port"; then
            print_info "端口 $port 上没有项目相关进程"
    else
            print_info "端口 $port 未被占用"
        fi
    fi
}

# 停止Python main.py进程（只停止项目相关的）
stop_python_main() {
    print_info "停止项目的Python main.py进程..."
    
    # 查找在项目目录下运行main.py的Python进程
    local pids=$(ps aux | grep "python.*main.py" | grep -v grep | grep "$PROJECT_ROOT" | awk '{print $2}')
    
    if [[ -n "$pids" ]]; then
        for pid in $pids; do
            print_info "停止项目Python进程 PID: $pid"
            kill "$pid" 2>/dev/null
            sleep 2
            
            if kill -0 "$pid" 2>/dev/null; then
                print_warning "强制停止Python进程 $pid"
                kill -9 "$pid" 2>/dev/null
            fi
        done
        print_success "项目Python main.py进程已停止"
    else
        print_info "未找到运行中的项目Python main.py进程"
    fi
}

# 停止项目的Node.js进程
stop_node_processes() {
    print_info "停止项目的Node.js进程..."
    
    # 查找项目目录下的npm、yarn、node等进程
    local node_pids=$(ps aux | grep -E "(npm|yarn|node.*serve|node.*dev|vite)" | grep -v grep | grep "$PROJECT_ROOT" | awk '{print $2}')
    
    if [[ -n "$node_pids" ]]; then
        for pid in $node_pids; do
            print_info "停止项目Node.js进程 PID: $pid"
            kill "$pid" 2>/dev/null
            sleep 1
        done
        print_success "项目Node.js进程已停止"
    else
        print_info "未找到运行中的项目Node.js进程"
    fi
}

# 停止通过PID文件记录的服务
stop_pid_services() {
    # 停止后端
    if [[ -f "$PIDS_FILE.backend" ]]; then
        local backend_pid=$(cat "$PIDS_FILE.backend" 2>/dev/null)
        if [[ -n "$backend_pid" ]]; then
            if kill -0 "$backend_pid" 2>/dev/null; then
                kill "$backend_pid" 2>/dev/null
            print_success "后端服务已停止 (PID: $backend_pid)"
        else
                print_info "后端服务进程不存在"
            fi
        fi
        rm -f "$PIDS_FILE.backend"
    fi
    
    # 停止前端
    if [[ -f "$PIDS_FILE.frontend" ]]; then
        local frontend_pid=$(cat "$PIDS_FILE.frontend" 2>/dev/null)
        if [[ -n "$frontend_pid" ]]; then
            if kill -0 "$frontend_pid" 2>/dev/null; then
                kill "$frontend_pid" 2>/dev/null
            print_success "前端服务已停止 (PID: $frontend_pid)"
        else
                print_info "前端服务进程不存在"
            fi
        fi
        rm -f "$PIDS_FILE.frontend"
    fi
}

# 清理项目临时文件
cleanup_temp_files() {
    print_info "清理项目临时文件..."
    
    # 只清理项目相关的文件
    rm -f "$PIDS_FILE".*
    rm -f "$PROJECT_ROOT/.lock"
    rm -f "$PROJECT_ROOT/backend/.lock"
    rm -f "$PROJECT_ROOT/frontend/.lock"
    rm -f "$PROJECT_ROOT/server.log"
    
    print_success "项目临时文件已清理"
}

# 显示服务状态
show_status() {
    echo
    print_info "检查项目服务状态..."
    
    local any_running=false
    
    # 检查项目端口
    for port in 3000 8000 5173; do
        if check_port "$port"; then
            local pid=$(get_port_pid "$port")
            if is_project_process "$pid"; then
                print_warning "项目端口 $port 仍在使用中 (PID: $pid)"
            any_running=true
            else
                print_info "端口 $port 被其他服务占用，跳过"
            fi
        fi
    done
    
    # 检查项目Python和Node进程
    if ps aux | grep "python.*main.py" | grep -v grep | grep "$PROJECT_ROOT" >/dev/null; then
        print_warning "仍有项目Python main.py进程在运行"
            any_running=true
    fi
    
    if ps aux | grep -E "(npm|yarn|node.*serve|vite)" | grep -v grep | grep "$PROJECT_ROOT" >/dev/null; then
        print_warning "仍有项目Node.js开发服务器在运行"
        any_running=true
    fi
    
    if [[ "$any_running" == "false" ]]; then
        print_success "所有项目服务已停止"
    fi
}

# 强制停止模式（限制在项目范围内）
force_stop() {
    print_warning "强制停止项目服务"
    
    # 只强制杀死项目相关进程
    ps aux | grep "python.*main.py" | grep "$PROJECT_ROOT" | grep -v grep | awk '{print $2}' | xargs -r kill -9 2>/dev/null
    ps aux | grep -E "(npm|yarn|node.*serve|vite)" | grep "$PROJECT_ROOT" | grep -v grep | awk '{print $2}' | xargs -r kill -9 2>/dev/null
    
    # 强制释放项目端口
    for port in 3000 8000 5173; do
        kill_port_process "$port"
    done
    
    cleanup_temp_files
    
    print_success "强制停止完成"
}

# 主停止函数
stop_all_services() {
    print_info "开始停止AVD Web项目服务..."
    
    # 1. 停止PID记录的服务
    stop_pid_services
    
    # 2. 停止项目Python main.py进程
    stop_python_main
    
    # 3. 停止项目Node.js进程
    stop_node_processes
    
    # 4. 安全停止项目端口进程
    kill_port_process 8000  # 后端
    kill_port_process 3000  # 前端React
    kill_port_process 5173  # 前端Vite
    
    # 5. 清理项目临时文件
    cleanup_temp_files
    
    # 6. 显示最终状态
    show_status
    
    echo
    print_success "================ 停止完成 ================"
    print_info "AVD Web项目服务已停止"
    print_info "如需重新启动，请运行: ./scripts/start.sh"
    echo "======================================="
}

# 显示帮助信息
show_help() {
    echo "AVD Web版本停止脚本 (Linux)"
    echo
    echo "用法:"
    echo "  $0 [选项]"
    echo
    echo "选项:"
    echo "  --force, -f    强制停止项目相关进程"
    echo "  --port PORT    仅停止指定端口上的项目进程"
    echo "  --help, -h     显示帮助信息"
    echo
    echo "示例:"
    echo "  $0              # 正常停止项目服务"
    echo "  $0 --force      # 强制停止项目服务"
    echo "  $0 --port 8000  # 仅停止8000端口上的项目进程"
    echo
    echo "注意: 此脚本只会停止AVD项目相关的进程，不会影响其他系统服务"
}

# 仅停止指定端口的项目进程
stop_port_only() {
    local port=$1
    print_info "仅停止端口 $port 上的项目进程"
    kill_port_process "$port"
}

# 主函数
main() {
    show_banner
    
    case "$1" in
        --force|-f)
            force_stop
            ;;
        --port)
            if [[ -n "$2" ]]; then
                stop_port_only "$2"
            else
                print_error "请指定端口号"
                echo
                show_help
                exit 1
            fi
            ;;
        --help|-h|help)
            show_help
            ;;
        "")
            stop_all_services
            ;;
        *)
            print_error "未知选项: $1"
            echo
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@" 