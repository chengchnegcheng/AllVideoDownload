#!/bin/bash

# AVD全能视频下载器 - BUG检查和修复验证脚本
# 检查已修复的BUG和系统整体健康状况

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}====== AVD BUG检查和修复验证 ======${NC}"
echo -e "${BLUE}检查时间: $(date)${NC}"
echo

# 切换到项目根目录
cd "$(dirname "$0")/.."

# ========================= 
# 1. 已修复BUG验证
# =========================
echo -e "${YELLOW}1. 验证已修复的BUG...${NC}"

# 检查 BUG 1: VideoDownloader导入错误（已修复）
echo "✓ 检查VideoDownloader导入错误修复..."
if grep -q "from.*video_downloader.*import VideoDownloader" backend/src/api/routers/subtitles.py; then
    echo -e "${RED}  ❌ BUG 1: VideoDownloader错误导入仍然存在${NC}"
    BUG_FOUND=1
else
    echo -e "${GREEN}  ✅ BUG 1: VideoDownloader导入错误已修复${NC}"
fi

# 检查 BUG 2: Google翻译器timeout设置错误（已修复）
echo "✓ 检查Google翻译器timeout设置..."
if grep -q "client\.timeout.*=" backend/src/core/subtitle_processor.py; then
    echo -e "${RED}  ❌ BUG 2: Google翻译器client.timeout错误设置仍然存在${NC}"
    BUG_FOUND=1
else
    echo -e "${GREEN}  ✅ BUG 2: Google翻译器timeout设置错误已修复${NC}"
fi

# 检查 BUG 3: main.py循环内导入json（已修复）
echo "✓ 检查main.py循环内json导入..."
if grep -A 5 -B 5 "import json" backend/main.py | grep -q "try:"; then
    echo -e "${RED}  ❌ BUG 3: main.py循环内导入json仍然存在${NC}"
    BUG_FOUND=1
else
    echo -e "${GREEN}  ✅ BUG 3: main.py循环内json导入已修复${NC}"
fi

# 检查 BUG 4: 类型注解错误（已修复）
echo "✓ 检查类型注解错误..."
if grep -q "Dict\[str, any\]" backend/src/core/downloaders/downloader_factory.py backend/src/core/downloader.py; then
    echo -e "${RED}  ❌ BUG 4: 类型注解错误（any -> Any）仍然存在${NC}"
    BUG_FOUND=1
else
    echo -e "${GREEN}  ✅ BUG 4: 类型注解错误已修复${NC}"
fi

echo

# ========================= 
# 2. Python语法检查
# =========================
echo -e "${YELLOW}2. Python语法检查...${NC}"
cd backend

# 检查主要文件的语法
SYNTAX_ERROR=0
for file in main.py src/core/subtitle_processor.py src/api/routers/subtitles.py; do
    echo "✓ 检查语法: $file"
    if python3 -m py_compile "$file" 2>/dev/null; then
        echo -e "${GREEN}  ✅ $file 语法正确${NC}"
    else
        echo -e "${RED}  ❌ $file 语法错误${NC}"
        SYNTAX_ERROR=1
    fi
done

cd ..

# ========================= 
# 3. 导入依赖检查
# =========================
echo -e "${YELLOW}3. 检查导入依赖...${NC}"

echo "✓ 检查关键导入..."
cd backend

# 检查关键模块的导入
IMPORT_ERROR=0
echo "  检查subtitle_processor导入..."
if python3 -c "from src.core.subtitle_processor import SubtitleProcessor; print('SubtitleProcessor导入成功')" 2>/dev/null; then
    echo -e "${GREEN}  ✅ SubtitleProcessor导入正常${NC}"
else
    echo -e "${RED}  ❌ SubtitleProcessor导入失败${NC}"
    IMPORT_ERROR=1
fi

echo "  检查downloader_factory导入..."
if python3 -c "from src.core.downloaders.downloader_factory import downloader_factory; print('downloader_factory导入成功')" 2>/dev/null; then
    echo -e "${GREEN}  ✅ downloader_factory导入正常${NC}"
else
    echo -e "${RED}  ❌ downloader_factory导入失败${NC}"
    IMPORT_ERROR=1
fi

cd ..

# ========================= 
# 4. 配置文件一致性检查
# =========================
echo -e "${YELLOW}4. 配置文件一致性检查...${NC}"

echo "✓ 检查requirements.txt关键依赖..."
MISSING_DEPS=0

# 检查新增的依赖
declare -a required_deps=("pysrt" "langdetect" "deep-translator" "googletrans" "httpx")

for dep in "${required_deps[@]}"; do
    if grep -q "$dep" backend/requirements.txt; then
        echo -e "${GREEN}  ✅ $dep 已在requirements.txt中${NC}"
    else
        echo -e "${RED}  ❌ $dep 缺失在requirements.txt中${NC}"
        MISSING_DEPS=1
    fi
done

# ========================= 
# 5. 潜在问题扫描
# =========================
echo -e "${YELLOW}5. 潜在问题扫描...${NC}"

echo "✓ 扫描可能的问题模式..."

# 检查未使用的导入（简单检查）
echo "  检查潜在未使用的导入..."
UNUSED_IMPORTS=$(find backend/src -name "*.py" -exec grep -l "^import.*warnings" {} \; | wc -l)
if [ $UNUSED_IMPORTS -gt 5 ]; then
    echo -e "${YELLOW}  ⚠️  发现多个文件导入warnings模块，可能存在未使用的导入${NC}"
fi

# 检查硬编码的路径
echo "  检查硬编码路径..."
HARDCODED_PATHS=$(find backend/src -name "*.py" -exec grep -l "/tmp\|/var\|C:\\\\" {} \; | wc -l)
if [ $HARDCODED_PATHS -gt 0 ]; then
    echo -e "${YELLOW}  ⚠️  发现 $HARDCODED_PATHS 个文件可能包含硬编码路径${NC}"
fi

# 检查长行（超过120字符）
echo "  检查代码行长度..."
LONG_LINES=$(find backend/src -name "*.py" -exec awk 'length($0) > 120 {count++} END {print count+0}' {} \; | awk '{sum+=$1} END {print sum+0}')
if [ $LONG_LINES -gt 20 ]; then
    echo -e "${YELLOW}  ⚠️  发现 $LONG_LINES 行超过120字符，建议优化代码格式${NC}"
fi

# ========================= 
# 6. 快速功能测试
# =========================
echo -e "${YELLOW}6. 快速功能测试...${NC}"

echo "✓ 测试关键功能模块..."

cd backend
TEST_ERROR=0

# 测试配置加载
echo "  测试配置加载..."
if python3 -c "from src.core.config import settings; print('配置加载成功')" 2>/dev/null; then
    echo -e "${GREEN}  ✅ 配置加载正常${NC}"
else
    echo -e "${RED}  ❌ 配置加载失败${NC}"
    TEST_ERROR=1
fi

# 测试数据库模块
echo "  测试数据库模块..."
if python3 -c "from src.core.database import init_db; print('数据库模块正常')" 2>/dev/null; then
    echo -e "${GREEN}  ✅ 数据库模块正常${NC}"
else
    echo -e "${RED}  ❌ 数据库模块异常${NC}"
    TEST_ERROR=1
fi

cd ..

# ========================= 
# 7. 生成报告
# =========================
echo
echo -e "${BLUE}====== BUG检查报告 ======${NC}"
echo "检查时间: $(date)"
echo

TOTAL_ERRORS=0

if [ ${BUG_FOUND:-0} -eq 1 ]; then
    echo -e "${RED}❌ 发现未修复的BUG${NC}"
    TOTAL_ERRORS=$((TOTAL_ERRORS + 1))
else
    echo -e "${GREEN}✅ 所有已知BUG均已修复${NC}"
fi

if [ $SYNTAX_ERROR -eq 1 ]; then
    echo -e "${RED}❌ 发现Python语法错误${NC}"
    TOTAL_ERRORS=$((TOTAL_ERRORS + 1))
else
    echo -e "${GREEN}✅ Python语法检查通过${NC}"
fi

if [ $IMPORT_ERROR -eq 1 ]; then
    echo -e "${RED}❌ 发现导入错误${NC}"
    TOTAL_ERRORS=$((TOTAL_ERRORS + 1))
else
    echo -e "${GREEN}✅ 关键模块导入正常${NC}"
fi

if [ $MISSING_DEPS -eq 1 ]; then
    echo -e "${RED}❌ 缺少必要依赖${NC}"
    TOTAL_ERRORS=$((TOTAL_ERRORS + 1))
else
    echo -e "${GREEN}✅ 依赖配置完整${NC}"
fi

if [ $TEST_ERROR -eq 1 ]; then
    echo -e "${RED}❌ 功能测试失败${NC}"
    TOTAL_ERRORS=$((TOTAL_ERRORS + 1))
else
    echo -e "${GREEN}✅ 关键功能测试通过${NC}"
fi

echo
if [ $TOTAL_ERRORS -eq 0 ]; then
    echo -e "${GREEN}🎉 所有检查通过！系统状态良好。${NC}"
    echo -e "${GREEN}建议：可以安全地启动应用程序。${NC}"
    exit 0
else
    echo -e "${RED}⚠️  发现 $TOTAL_ERRORS 个问题需要修复。${NC}"
    echo -e "${YELLOW}建议：修复上述问题后再启动应用程序。${NC}"
    exit 1
fi 