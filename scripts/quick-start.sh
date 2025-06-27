#!/bin/bash

# AVD Web版本 - 快速启动脚本 (Linux/Mac)
# 最简化的一键启动，适合日常使用

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BLUE}🚀 AVD Web版本 - 快速启动${NC}"
echo "=================================="

# 检查是否已经在运行
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${GREEN}✓ 后端服务已运行 (http://localhost:8000)${NC}"
else
    echo "🔄 启动后端服务..."
    cd "$PROJECT_ROOT/backend"
    source venv/bin/activate 2>/dev/null || {
        echo "📦 初始化Python环境..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    }
    nohup python main.py > /dev/null 2>&1 &
    sleep 3
fi

if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${GREEN}✓ 前端服务已运行 (http://localhost:3000)${NC}"
else
    echo "🔄 启动前端服务..."
    cd "$PROJECT_ROOT/frontend"
    if [ ! -d "node_modules" ]; then
        echo "📦 安装前端依赖..."
        npm install
    fi
    nohup npm run dev > /dev/null 2>&1 &
    sleep 3
fi

echo "=================================="
echo -e "${GREEN}🎉 启动完成！${NC}"
echo ""
echo "📱 前端访问: http://localhost:3000"
echo "🔧 后端API: http://localhost:8000"
echo "📖 API文档: http://localhost:8000/docs"
echo ""
echo "⏹️  停止服务: ./scripts/stop.sh"
echo "🔄 重启服务: ./scripts/start.sh restart" 