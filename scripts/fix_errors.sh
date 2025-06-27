#!/bin/bash

# AVD Web 错误修复脚本
echo "=== AVD Web 错误修复脚本 ==="

# 进入后端目录
cd /www/AllVideoDownload/backend

# 激活虚拟环境
source venv/bin/activate

echo "1. 安装缺少的依赖..."
pip install langdetect deep-translator pysrt urllib3

echo "2. 检查已安装的翻译相关包..."
pip list | grep -E "(langdetect|deep-translator|pysrt|googletrans)"

echo "3. 清理旧的日志文件..."
# 备份当前错误日志
cp /www/AllVideoDownload/logs/avd_web_error.log /www/AllVideoDownload/logs/avd_web_error.log.backup

# 清空错误日志
> /www/AllVideoDownload/logs/avd_web_error.log

echo "4. 清理模型缓存..."
rm -rf /www/AllVideoDownload/backend/data/models/sentencepiece.*

echo "5. 停止现有的后端进程..."
pkill -f "python main.py" || true

echo "6. 等待进程停止..."
sleep 2

echo "7. 启动后端服务..."
cd /www/AllVideoDownload/backend
python main.py &

echo "8. 等待服务启动..."
sleep 5

echo "9. 检查服务状态..."
curl -s http://localhost:8000/health || echo "服务启动检查失败"

echo "=== 错误修复完成 ==="
echo "请查看新的日志文件，确认错误是否已解决" 