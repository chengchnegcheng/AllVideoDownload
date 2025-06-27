# AVD Web版本 - 全能视频下载器

一个现代化的Web版视频下载工具，基于原始AVD桌面版本开发，采用前后端分离架构，提供更好的用户体验和部署灵活性。

## ✨ 主要特性

- 🎬 **多平台视频下载**：支持YouTube、Bilibili、抖音、微信视频号、小红书、腾讯视频、优酷、爱奇艺等主流平台
- 🏗️ **模块化下载器架构**：每个平台都有专门优化的下载器，智能识别URL并选择最佳下载策略
- 🔊 **音频提取**：一键转换视频为MP3格式
- 📝 **AI字幕生成**：基于faster-whisper的高精度语音识别
- 🌐 **字幕翻译**：支持多语言字幕翻译
- 🎯 **字幕烧录**：将字幕直接嵌入视频中
- 🌈 **现代化UI**：基于Ant Design的响应式界面，支持平台标识显示
- 🔄 **实时进度**：WebSocket实时下载进度更新
- 🐳 **Docker支持**：一键容器化部署
- 📱 **移动端适配**：支持手机和平板访问

### 🎯 支持的平台

| 平台 | 域名 | 特性 |
|------|------|------|
| YouTube | youtube.com, youtu.be | 高质量视频、字幕下载 |
| Bilibili | bilibili.com | B站视频、番剧下载 |
| 抖音 | douyin.com | 短视频、直播录制 |
| 微信视频号 | channels.weixin.qq.com | 视频号内容下载 |
| 小红书 | xiaohongshu.com | 笔记视频下载 |
| 腾讯视频 | v.qq.com | VIP视频下载（需Cookie） |
| 优酷 | youku.com | 优酷视频下载 |
| 爱奇艺 | iqiyi.com | 爱奇艺视频下载 |
| 其他平台 | - | 通用下载器支持大部分视频网站 |

## 🚀 一键启动

### 快速启动（推荐）

#### Linux/Mac用户
```bash
# 最简单的方式
./scripts/quick-start.sh

# 或使用完整功能启动
./scripts/start.sh
```

#### Windows用户
```batch
scripts\start.bat
```

### Docker部署（生产推荐）
```bash
# 使用Docker管理脚本
./scripts/docker-manager.sh start -d

# 或直接使用docker-compose
docker-compose up -d
```

### 停止服务
```bash
# Linux/Mac
./scripts/stop.sh

# Windows
scripts\stop.bat
```

## 📋 技术架构

### 前端技术栈
- **React 18** + **TypeScript** - 现代化的前端框架
- **Ant Design 5** - 企业级UI设计语言
- **Vite** - 快速的构建工具
- **WebSocket** - 实时通信
- **Axios** - HTTP客户端

### 后端技术栈
- **FastAPI** - 现代、快速的Web框架
- **SQLAlchemy** - ORM数据库操作
- **yt-dlp** - 视频下载引擎
- **faster-whisper** - AI语音识别
- **Uvicorn** - ASGI服务器

### 部署技术
- **Docker** + **Docker Compose** - 容器化部署
- **Nginx** - 反向代理（可选）
- **Redis** - 缓存和会话存储
- **MySQL/PostgreSQL** - 数据库（可选）

## 📦 项目结构

```
AllVideoDownload/
├── backend/                 # 后端服务
│   ├── main.py             # FastAPI应用入口
│   ├── src/                # 源代码
│   │   ├── api/            # API路由
│   │   ├── core/           # 核心功能
│   │   │   ├── downloaders/  # 模块化下载器
│   │   │   │   ├── base_downloader.py      # 基础下载器类
│   │   │   │   ├── downloader_factory.py   # 下载器工厂
│   │   │   │   ├── youtube_downloader.py   # YouTube下载器
│   │   │   │   ├── bilibili_downloader.py  # Bilibili下载器
│   │   │   │   └── ...                     # 其他平台下载器
│   │   │   └── downloader.py  # 主下载器接口
│   │   └── models/         # 数据模型
│   ├── requirements.txt    # Python依赖
│   └── Dockerfile         # 后端Docker镜像
├── frontend/               # 前端应用
│   ├── src/               # React源代码
│   │   ├── components/    # 组件
│   │   ├── pages/         # 页面
│   │   ├── hooks/         # 自定义Hook
│   │   └── services/      # 服务层
│   ├── package.json       # Node.js依赖
│   └── Dockerfile         # 前端Docker镜像
├── scripts/               # 启动停止脚本
│   ├── start.sh           # Linux/Mac启动脚本
│   ├── start.bat          # Windows启动脚本
│   ├── stop.sh            # 停止脚本
│   ├── quick-start.sh     # 快速启动脚本
│   ├── docker-manager.sh  # Docker管理脚本
│   └── README.md          # 脚本使用指南
├── docker-compose.yml     # Docker编排文件
└── README.md              # 项目说明文档
```

## 🛠️ 手动安装和配置

如果不使用一键脚本，也可以手动安装：

### 环境要求
- **Python 3.8+**
- **Node.js 16+**
- **FFmpeg**（用于媒体处理）
- **Docker & Docker Compose**（Docker部署）

### 后端安装
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### 前端安装
```bash
cd frontend
npm install
npm run dev
```

## 🎯 功能特性

### 🎬 视频下载
- 支持多种视频质量选择
- 批量下载功能
- 下载进度实时显示
- 断点续传支持
- 自动重试机制
- **智能平台识别**：自动检测视频来源平台
- **平台专属优化**：针对不同平台的特殊处理

### 📝 字幕功能
- AI自动生成字幕
- 支持多语言识别
- 字幕文件导出（SRT/VTT）
- 字幕翻译功能
- 字幕烧录到视频

### 🔧 系统管理
- 下载历史记录
- **平台筛选功能**：按平台过滤历史任务
- 批量操作
- 系统设置
- 用户会话管理
- 文件管理

### 📊 仪表板
- 实时下载统计
- 系统资源监控
- 下载任务概览
- **平台分布统计**：查看各平台下载情况
- 错误日志查看

## 🚀 启动脚本详细说明

项目提供了多种启动方式，适合不同的使用场景：

### 1. 快速启动脚本 (`quick-start.sh`)
- **适用场景**：日常开发，快速测试
- **特点**：一键启动，智能检测，自动安装依赖
- **使用方法**：`./scripts/quick-start.sh`

### 2. 完整启动脚本 (`start.sh` / `start.bat`)
- **适用场景**：开发和生产环境
- **特点**：支持多种模式，完整环境检查
- **使用方法**：`./scripts/start.sh [command] [mode]`

### 3. Docker管理脚本 (`docker-manager.sh`)
- **适用场景**：生产部署，容器化管理
- **特点**：完整的Docker生命周期管理
- **使用方法**：`./scripts/docker-manager.sh <command> [options]`

详细的脚本使用说明请查看：[scripts/README.md](scripts/README.md)

## 🌐 访问地址

启动成功后，可通过以下地址访问：

- **前端界面**：http://localhost:3000
- **后端API**：http://localhost:8000  
- **API文档**：http://localhost:8000/docs
- **Redis管理**：http://localhost:8001（如果启用）

## 🔧 配置说明

### 环境变量配置

创建 `.env` 文件来配置环境变量：

```bash
# 数据库配置
DATABASE_URL=sqlite:///./avd_web.db
# DATABASE_URL=mysql://user:password@localhost/avd_web
# DATABASE_URL=postgresql://user:password@localhost/avd_web

# Redis配置
REDIS_URL=redis://localhost:6379

# AI模型配置
WHISPER_MODEL_SIZE=small
WHISPER_DEVICE=cpu

# 代理配置
HTTP_PROXY=
HTTPS_PROXY=

# 安全配置
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# 文件路径配置
DOWNLOAD_PATH=./downloads
UPLOAD_PATH=./uploads
```

### Docker配置

Docker环境下的配置在 `docker-compose.yml` 中：

```yaml
services:
  backend:
    environment:
      - DATABASE_URL=mysql://root:password@mysql:3306/avd_web
      - REDIS_URL=redis://redis:6379
  
  frontend:
    environment:
      - REACT_APP_API_URL=http://localhost:8000
```

## 🐛 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   ./scripts/stop.sh --force  # 强制停止所有服务
   ```

2. **依赖安装失败**
   ```bash
   # 清理并重新安装
   rm -rf backend/venv frontend/node_modules
   ./scripts/start.sh start dev
   ```

3. **Docker问题**
   ```bash
   ./scripts/docker-manager.sh cleanup --all
   ./scripts/docker-manager.sh build --no-cache
   ```

4. **权限问题（Linux/Mac）**
   ```bash
   chmod +x scripts/*.sh
   ```

### 日志查看

```bash
# 查看后端日志
tail -f logs/backend.log

# 查看前端日志  
tail -f logs/frontend.log

# 查看Docker日志
./scripts/docker-manager.sh logs -f
```

## 🤝 贡献指南

欢迎提交Issue和Pull Request来帮助改进项目！

### 开发流程
1. Fork项目
2. 创建功能分支
3. 提交变更
4. 创建Pull Request

### 代码规范
- 后端遵循PEP 8规范
- 前端使用ESLint和Prettier
- 提交信息遵循Conventional Commits

## 📄 许可证

本项目采用MIT许可证，详见 [LICENSE](LICENSE) 文件。

## 🔗 相关链接

- **原始AVD项目**：基于桌面版本的现代化Web重构
- **技术文档**：[AVD_WEB_DEVELOPMENT.md](AVD_WEB_DEVELOPMENT.md)
- **脚本文档**：[scripts/README.md](scripts/README.md)
- **更新日志**：查看Git提交历史

---

**注意**：本项目仅供学习和研究使用，请遵守相关平台的服务条款和版权法律。 