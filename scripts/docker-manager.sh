#!/bin/bash

# AVD Web版本 - Docker管理脚本 (Linux/Mac)
# 专门用于管理Docker容器化部署

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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

# 显示横幅
show_banner() {
    echo -e "${BLUE}"
    echo "=================================="
    echo "   AVD Web版本 - Docker管理"
    echo "   全能视频下载器 v2.0.0"
    echo "=================================="
    echo -e "${NC}"
}

# 检查Docker环境
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "请安装Docker"
        echo "安装方法: https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_error "请安装Docker Compose"
        echo "安装方法: https://docs.docker.com/compose/install/"
        exit 1
    fi

    # 检查Docker守护进程是否运行
    if ! docker info &> /dev/null; then
        print_error "Docker守护进程未运行，请启动Docker"
        exit 1
    fi

    print_success "Docker环境检查通过"
}

# 构建镜像
build_images() {
    print_info "构建Docker镜像..."
    cd "$PROJECT_ROOT"
    
    local build_args=""
    if [ "$1" = "--no-cache" ]; then
        build_args="--no-cache"
        print_info "使用--no-cache构建"
    fi
    
    docker-compose build $build_args
    
    if [ $? -eq 0 ]; then
        print_success "Docker镜像构建完成"
    else
        print_error "Docker镜像构建失败"
        exit 1
    fi
}

# 启动服务
start_services() {
    print_info "启动Docker服务..."
    cd "$PROJECT_ROOT"
    
    local compose_args=""
    if [ "$1" = "--detach" ] || [ "$1" = "-d" ]; then
        compose_args="-d"
        print_info "后台模式启动"
    fi
    
    docker-compose up $compose_args --build
    
    if [ $? -eq 0 ]; then
        print_success "Docker服务启动成功"
        echo ""
        print_info "服务访问地址:"
        print_info "  前端: http://localhost:3000"
        print_info "  后端: http://localhost:8000"
        print_info "  API文档: http://localhost:8000/docs"
        echo ""
        print_info "管理命令:"
        print_info "  查看日志: docker-compose logs -f"
        print_info "  停止服务: docker-compose down"
        print_info "  重启服务: docker-compose restart"
    else
        print_error "Docker服务启动失败"
        exit 1
    fi
}

# 停止服务
stop_services() {
    print_info "停止Docker服务..."
    cd "$PROJECT_ROOT"
    
    local stop_args=""
    if [ "$1" = "--remove-orphans" ]; then
        stop_args="--remove-orphans"
        print_info "同时清理孤立容器"
    fi
    
    docker-compose down $stop_args
    
    if [ $? -eq 0 ]; then
        print_success "Docker服务已停止"
    else
        print_error "停止Docker服务时出错"
    fi
}

# 重启服务
restart_services() {
    print_info "重启Docker服务..."
    stop_services
    sleep 2
    start_services -d
}

# 查看服务状态
show_status() {
    print_info "Docker服务状态:"
    cd "$PROJECT_ROOT"
    docker-compose ps
    
    echo ""
    print_info "容器资源使用情况:"
    docker stats --no-stream $(docker-compose ps -q) 2>/dev/null || print_warning "没有运行的容器"
}

# 查看日志
show_logs() {
    cd "$PROJECT_ROOT"
    
    local service="$1"
    local follow_flag=""
    
    if [ "$2" = "--follow" ] || [ "$2" = "-f" ]; then
        follow_flag="-f"
    fi
    
    if [ -n "$service" ]; then
        print_info "显示 $service 服务日志..."
        docker-compose logs $follow_flag "$service"
    else
        print_info "显示所有服务日志..."
        docker-compose logs $follow_flag
    fi
}

# 清理Docker资源
cleanup() {
    print_warning "开始清理Docker资源..."
    cd "$PROJECT_ROOT"
    
    # 停止并移除容器
    docker-compose down --remove-orphans
    
    # 移除镜像
    if [ "$1" = "--images" ]; then
        print_info "清理项目镜像..."
        docker-compose down --rmi all --remove-orphans
    fi
    
    # 清理构建缓存
    if [ "$1" = "--all" ]; then
        print_info "清理所有Docker资源..."
        docker system prune -f
        docker volume prune -f
    fi
    
    print_success "Docker资源清理完成"
}

# 进入容器
enter_container() {
    local service="$1"
    local shell="${2:-/bin/bash}"
    
    if [ -z "$service" ]; then
        print_error "请指定要进入的服务名 (backend/frontend)"
        return 1
    fi
    
    cd "$PROJECT_ROOT"
    
    print_info "进入 $service 容器..."
    docker-compose exec "$service" "$shell"
}

# 更新镜像
update_images() {
    print_info "更新Docker镜像..."
    cd "$PROJECT_ROOT"
    
    # 拉取最新的基础镜像
    docker-compose pull
    
    # 重新构建
    build_images --no-cache
    
    print_success "Docker镜像更新完成"
}

# 备份数据
backup_data() {
    local backup_dir="${1:-./backups/$(date +%Y%m%d_%H%M%S)}"
    
    print_info "备份数据到: $backup_dir"
    mkdir -p "$backup_dir"
    
    cd "$PROJECT_ROOT"
    
    # 备份数据库
    if docker-compose ps | grep -q mysql; then
        print_info "备份MySQL数据库..."
        docker-compose exec -T mysql mysqldump -u root -p$MYSQL_ROOT_PASSWORD avd_web > "$backup_dir/database.sql"
    fi
    
    # 备份上传的文件和下载的内容
    if [ -d "backend/downloads" ]; then
        print_info "备份下载文件..."
        cp -r backend/downloads "$backup_dir/"
    fi
    
    if [ -d "backend/uploads" ]; then
        print_info "备份上传文件..."
        cp -r backend/uploads "$backup_dir/"
    fi
    
    print_success "数据备份完成: $backup_dir"
}

# 恢复数据
restore_data() {
    local backup_dir="$1"
    
    if [ -z "$backup_dir" ] || [ ! -d "$backup_dir" ]; then
        print_error "请指定有效的备份目录"
        return 1
    fi
    
    print_warning "恢复数据从: $backup_dir"
    cd "$PROJECT_ROOT"
    
    # 恢复数据库
    if [ -f "$backup_dir/database.sql" ]; then
        print_info "恢复MySQL数据库..."
        docker-compose exec -T mysql mysql -u root -p$MYSQL_ROOT_PASSWORD avd_web < "$backup_dir/database.sql"
    fi
    
    # 恢复文件
    if [ -d "$backup_dir/downloads" ]; then
        print_info "恢复下载文件..."
        cp -r "$backup_dir/downloads" backend/
    fi
    
    if [ -d "$backup_dir/uploads" ]; then
        print_info "恢复上传文件..."
        cp -r "$backup_dir/uploads" backend/
    fi
    
    print_success "数据恢复完成"
}

# 显示帮助信息
show_help() {
    echo "AVD Web版本 Docker管理脚本"
    echo ""
    echo "用法:"
    echo "  $0 <command> [options]"
    echo ""
    echo "基础命令:"
    echo "  start [--detach|-d]     启动服务"
    echo "  stop [--remove-orphans] 停止服务"
    echo "  restart                 重启服务"
    echo "  status                  查看服务状态"
    echo "  logs [service] [-f]     查看日志"
    echo ""
    echo "构建命令:"
    echo "  build [--no-cache]      构建镜像"
    echo "  update                  更新镜像"
    echo ""
    echo "管理命令:"
    echo "  enter <service> [shell] 进入容器 (backend/frontend)"
    echo "  cleanup [--images|--all] 清理资源"
    echo ""
    echo "数据命令:"
    echo "  backup [dir]            备份数据"
    echo "  restore <dir>           恢复数据"
    echo ""
    echo "示例:"
    echo "  $0 start -d             # 后台启动服务"
    echo "  $0 logs backend -f      # 实时查看后端日志"
    echo "  $0 enter backend        # 进入后端容器"
    echo "  $0 backup ./my-backup   # 备份数据"
    echo "  $0 cleanup --all        # 清理所有资源"
}

# 主函数
main() {
    show_banner
    
    local command="$1"
    shift || true
    
    case "$command" in
        start)
            check_docker
            start_services "$@"
            ;;
        stop)
            stop_services "$@"
            ;;
        restart)
            check_docker
            restart_services
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$@"
            ;;
        build)
            check_docker
            build_images "$@"
            ;;
        update)
            check_docker
            update_images
            ;;
        enter)
            enter_container "$@"
            ;;
        cleanup)
            cleanup "$@"
            ;;
        backup)
            backup_data "$@"
            ;;
        restore)
            restore_data "$@"
            ;;
        help|--help|-h)
            show_help
            ;;
        "")
            print_error "请指定命令"
            echo ""
            show_help
            exit 1
            ;;
        *)
            print_error "未知命令: $command"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@" 