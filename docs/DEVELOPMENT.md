# AVD (全能视频下载器) 开发文档

## 项目概述

AVD (All Video Downloader) 是一个功能强大的桌面视频下载工具，基于Python开发，支持多种视频平台的内容下载、AI字幕生成和字幕翻译功能。项目采用现代化的GUI设计和模块化架构，提供了良好的用户体验和代码可维护性。

### 主要特性

- 🎬 **多平台视频下载**：支持YouTube、Bilibili、Twitter等主流平台
- 🔊 **音频提取**：一键转换视频为MP3格式
- 📝 **AI字幕生成**：基于faster-whisper实现的高精度语音识别
- 🌐 **字幕翻译**：支持多语言字幕翻译（在线/离线模式）
- 🎯 **字幕烧录**：将字幕直接嵌入视频中
- 🧩 **浏览器集成**：保存网站登录状态便于下载受限内容
- 🌈 **主题支持**：支持明亮、暗黑和蓝色主题
- 🖥️ **双模式操作**：图形界面 + 命令行接口

## 技术栈

### 核心技术
- **Python 3.8+**：主要开发语言
- **PyQt6**：GUI框架
- **yt-dlp**：视频下载引擎
- **faster-whisper**：AI语音识别
- **Selenium**：浏览器自动化
- **FFmpeg**：媒体文件处理

### 主要依赖库
```
pyqt6>=6.3.0          # GUI框架
typer>=0.9.0           # CLI框架
yt-dlp>=2023.3.4       # 视频下载
faster-whisper>=0.10.0 # 语音识别
selenium>=4.8.0        # 浏览器自动化
transformers>=4.30.0   # 机器学习模型
torch>=2.0.0           # 深度学习框架
```

## 项目架构

### 目录结构
```
AllVideoDownload/
├── config.ini                 # 配置文件(ini格式)
├── config.json               # 配置文件(json格式)
├── main.py                   # 主入口文件
├── requirements.txt          # 依赖清单
├── run.bat / run.sh          # 启动脚本
├── cookies/                  # Cookie存储目录
├── downloads/                # 下载文件存储
├── logs/                     # 日志文件
├── models/                   # AI模型缓存
└── src/                      # 源代码目录
    ├── __init__.py
    ├── main.py               # 应用主逻辑
    ├── core/                 # 核心功能模块
    │   ├── downloader.py     # 视频下载器
    │   ├── media_processor.py # 媒体文件处理
    │   ├── platform_handler.py # 平台适配器
    │   └── subtitles.py      # 字幕处理器
    ├── ui/                   # 用户界面模块
    │   ├── main_window.py    # 主窗口
    │   ├── download_tab.py   # 下载标签页
    │   ├── subtitle_tab.py   # 字幕标签页
    │   ├── login_tab.py      # 登录标签页
    │   ├── settings_tab.py   # 设置标签页
    │   ├── log_tab.py        # 日志标签页
    │   └── style/            # 样式和主题
    │       ├── theme_manager.py
    │       └── style.qss
    └── utils/                # 工具模块
        ├── browser.py        # 浏览器工具
        ├── config.py         # 配置管理
        ├── logger.py         # 日志管理
        └── network.py        # 网络工具
```

### 核心模块设计

#### 1. 下载器模块 (`core/downloader.py`)

**主要类：**
- `Downloader`：主要下载器类
- `DownloadOptions`：下载选项配置
- `DownloadProgress`：下载进度跟踪
- `VideoInfo`：视频信息容器

**核心功能：**
- 多平台视频下载
- 下载进度监控
- Cookie管理
- 质量选择和格式转换
- 并发下载支持

**关键方法：**
```python
def download_video(self, url: str, options: DownloadOptions) -> Optional[str]
def get_video_info(self, url: str) -> Optional[VideoInfo]
def cancel_download(self)
```

#### 2. 字幕处理模块 (`core/subtitles.py`)

**主要类：**
- `SubtitleProcessor`：字幕处理核心
- `SubtitleEntry`：字幕条目

**核心功能：**
- AI字幕生成（基于faster-whisper）
- 字幕翻译（在线/离线）
- SRT文件解析和生成
- 字幕时间轴处理

**关键方法：**
```python
def generate_subtitles_from_audio(self, audio_path: str, language: str) -> Optional[str]
def translate_srt(self, srt_path: str, target_lang: str) -> Optional[str]
def parse_srt_file(self, srt_path: str) -> List[SubtitleEntry]
```

#### 3. 媒体处理模块 (`core/media_processor.py`)

**核心功能：**
- 音频提取
- 字幕烧录
- 格式转换
- FFmpeg集成

#### 4. 平台适配模块 (`core/platform_handler.py`)

**核心功能：**
- 平台特定处理逻辑
- Cookie获取和管理
- 登录状态维护

#### 5. UI模块 (`ui/`)

**模块化设计：**
- `MainWindow`：主窗口框架
- 各功能标签页独立实现
- 主题管理系统
- 响应式布局

### 配置管理

项目支持两种配置格式：
- `config.json`：主要配置文件
- `config.ini`：备用配置格式

**主要配置项：**
```json
{
    "version": "1.0.5",
    "download_directory": "下载目录路径",
    "whisper_model_size": "模型大小(tiny/small/medium/large)",
    "theme": "主题(light/dark/blue)",
    "max_concurrency": "最大并发数",
    "use_proxy": "是否使用代理",
    "auto_download_subs": "自动下载字幕"
}
```

## 开发指南

### 环境搭建

1. **Python环境**
   ```bash
   # 推荐使用Python 3.8-3.13
   python --version
   ```

2. **依赖安装**
   ```bash
   pip install -r requirements.txt
   ```

3. **环境变量设置**
   ```bash
   # 设置模型缓存目录
   export HF_HOME=./models
   export TRANSFORMERS_CACHE=./models/transformers
   ```

### 开发模式启动

1. **GUI模式**
   ```bash
   python main.py
   # 或直接启动GUI
   python main.py gui
   ```

2. **CLI模式**
   ```bash
   # 下载视频
   python main.py download [URL] --quality best
   
   # 生成字幕
   python main.py subgen [视频路径] --language auto
   
   # 翻译字幕
   python main.py translate [字幕路径] --to zh-CN
   ```

### 核心开发原则

#### 1. 模块化设计
- 每个功能模块独立开发
- 清晰的接口定义
- 低耦合高内聚

#### 2. 错误处理
- 完善的异常处理机制
- 用户友好的错误提示
- 详细的日志记录

#### 3. 进度反馈
```python
# 进度回调函数示例
def progress_callback(message: str, progress: int):
    """
    Args:
        message: 状态消息
        progress: 进度百分比 (0-100)
    """
    print(f"[{progress}%] {message}")
```

#### 4. 资源管理
- 及时释放系统资源
- 进程和线程的正确管理
- 临时文件清理

### 添加新功能

#### 1. 新增下载平台支持

1. 在`core/platform_handler.py`中添加平台检测：
```python
def detect_platform(url: str) -> str:
    if "newplatform.com" in url:
        return "newplatform"
    # ... 其他平台检测逻辑
```

2. 在`core/downloader.py`中添加平台特定配置：
```python
def _get_platform_options(self, platform: str) -> dict:
    if platform == "newplatform":
        return {
            "extractor_args": {"newplatform": {"特定参数": "值"}}
        }
```

#### 2. 新增UI功能

1. 创建新的标签页：
```python
# src/ui/new_tab.py
class NewTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        # UI初始化逻辑
        pass
```

2. 在主窗口中注册：
```python
# src/ui/main_window.py
self.new_tab = NewTab()
self.content_area.addWidget(self.new_tab)
```

#### 3. 新增字幕处理功能

1. 在`SubtitleProcessor`类中添加方法：
```python
def new_subtitle_feature(self, input_path: str) -> Optional[str]:
    """新的字幕处理功能"""
    try:
        # 实现逻辑
        return output_path
    except Exception as e:
        log.error(f"处理失败: {e}")
        return None
```

### 调试和测试

#### 1. 日志系统
项目使用统一的日志系统，支持多级别日志：
```python
from src.utils.logger import log

log.debug("调试信息")
log.info("一般信息")
log.warning("警告信息")
log.error("错误信息")
```

#### 2. 测试文件结构
```
tests/
├── test_downloader.py     # 下载器测试
├── test_subtitles.py      # 字幕功能测试
├── test_ui.py             # UI测试
└── fixtures/              # 测试数据
    ├── sample_video.mp4
    └── sample_subtitle.srt
```

#### 3. 测试示例
```python
import unittest
from src.core.downloader import Downloader, DownloadOptions

class TestDownloader(unittest.TestCase):
    def setUp(self):
        self.downloader = Downloader()
    
    def test_video_info_extraction(self):
        url = "https://example.com/video"
        info = self.downloader.get_video_info(url)
        self.assertIsNotNone(info)
        self.assertTrue(len(info.title) > 0)
```

### 性能优化

#### 1. 下载性能
- 使用适当的并发数量
- 实现下载队列管理
- 支持断点续传

#### 2. AI模型优化
- 模型缓存机制
- 按需加载模型
- GPU加速支持

#### 3. 内存管理
- 及时释放大文件引用
- 流式处理大型媒体文件
- 垃圾回收优化

### 部署和分发

#### 1. 打包方式
```bash
# 使用PyInstaller打包
pip install pyinstaller
pyinstaller --onefile --windowed main.py
```

#### 2. 依赖管理
- 使用固定版本号
- 定期更新依赖库
- 兼容性测试

#### 3. 发布流程
1. 版本号更新
2. 功能测试
3. 打包构建
4. 发布文档更新

## 故障排除

### 常见问题

#### 1. 模型下载失败
**现象：** faster-whisper模型下载超时
**解决方案：**
- 检查网络连接
- 配置代理设置
- 使用本地模型文件

#### 2. 视频下载失败
**现象：** 特定网站视频无法下载
**解决方案：**
- 更新yt-dlp版本
- 检查Cookie有效性
- 验证URL格式

#### 3. 字幕生成错误
**现象：** 音频转录失败
**解决方案：**
- 检查音频文件格式
- 调整模型大小
- 验证FFmpeg安装

#### 4. GUI显示问题
**现象：** 界面显示异常
**解决方案：**
- 检查PyQt6版本
- 更新显卡驱动
- 重置主题设置

### 调试技巧

1. **启用详细日志**
   ```python
   import logging
   logging.getLogger().setLevel(logging.DEBUG)
   ```

2. **使用开发者工具**
   - PyQt6 Designer用于UI设计
   - Python Debugger进行代码调试

3. **性能分析**
   ```python
   import cProfile
   cProfile.run('main_function()')
   ```

## 贡献指南

### 代码规范

#### 1. Python代码风格
- 遵循PEP 8规范
- 使用类型提示
- 编写文档字符串

#### 2. 命名约定
- 类名：PascalCase
- 函数名：snake_case
- 常量：UPPER_CASE
- 私有方法：_private_method

#### 3. 注释规范
```python
def download_video(self, url: str, options: DownloadOptions) -> Optional[str]:
    """
    下载指定URL的视频
    
    Args:
        url: 视频URL
        options: 下载选项配置
        
    Returns:
        下载的文件路径，失败时返回None
        
    Raises:
        ValueError: 当URL格式无效时
        ConnectionError: 当网络连接失败时
    """
    pass
```

### 提交流程

1. **Fork项目**
2. **创建功能分支**
   ```bash
   git checkout -b feature/new-feature
   ```
3. **编写代码和测试**
4. **提交变更**
   ```bash
   git commit -m "feat: 添加新功能描述"
   ```
5. **推送分支**
   ```bash
   git push origin feature/new-feature
   ```
6. **创建Pull Request**

### 提交信息规范
```
feat: 新功能
fix: 修复bug
docs: 文档更新
style: 代码格式调整
refactor: 代码重构
test: 测试相关
chore: 构建工具或辅助工具的变动
```

## 路线图

### 已完成功能 (v1.0.5)
- ✅ 基础视频下载功能
- ✅ AI字幕生成
- ✅ 字幕翻译
- ✅ 字幕烧录
- ✅ 主题系统
- ✅ 浏览器登录集成

### 计划功能

#### v1.1.0
- 🔄 批量下载管理
- 🔄 下载队列优化
- 🔄 更多视频平台支持
- 🔄 插件系统框架

#### v1.2.0
- 📋 视频播放器集成
- 📋 字幕编辑器
- 📋 下载历史管理
- 📋 云同步功能

#### v2.0.0
- 📋 Web版本开发
- 📋 移动端支持
- 📋 API服务提供
- 📋 企业版功能

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 联系方式

- 项目地址：[GitHub Repository]
- 问题反馈：[Issues]
- 讨论交流：[Discussions]

---

**注意：** 本文档会随着项目发展持续更新，请关注最新版本。

# AVD Web版本 - 开发文档

## 项目概述

AVD (All Video Downloader) Web版本是一个基于Web的全能视频下载器，支持多个主流视频平台的视频下载和字幕处理功能。

### 主要特性

- 支持多平台视频下载（YouTube、Bilibili、抖音等）
- AI字幕生成（基于Whisper）
- 字幕翻译功能
- 实时下载进度显示
- 任务管理和历史记录
- 系统监控和配置管理

## 技术栈

### 后端
- **框架**: FastAPI (Python)
- **数据库**: SQLite + SQLAlchemy ORM
- **下载核心**: yt-dlp
- **AI模型**: faster-whisper
- **异步任务**: asyncio
- **WebSocket**: 实时通信

### 前端
- **框架**: React 18 + TypeScript
- **UI组件**: Ant Design 5
- **构建工具**: Vite
- **状态管理**: React Hooks
- **WebSocket**: 实时更新

## 下载器架构

### 模块化设计

项目采用模块化的下载器架构，支持灵活扩展：

```
backend/src/core/downloaders/
├── __init__.py
├── base_downloader.py          # 基础下载器抽象类
├── downloader_factory.py       # 下载器工厂
├── youtube_downloader.py       # YouTube专用下载器
├── bilibili_downloader.py      # Bilibili专用下载器
├── douyin_downloader.py        # 抖音专用下载器
├── weixin_downloader.py        # 微信视频号下载器
├── xiaohongshu_downloader.py   # 小红书下载器
├── qq_downloader.py            # 腾讯视频下载器
├── youku_downloader.py         # 优酷下载器
├── iqiyi_downloader.py         # 爱奇艺下载器
└── generic_downloader.py       # 通用下载器（后备方案）
```

### 下载器特性

1. **智能平台检测**: 自动识别URL对应的平台
2. **专用优化**: 每个平台都有专门的下载器实现
3. **通用后备**: 对于未识别的平台使用通用下载器
4. **统一接口**: 所有下载器实现相同的接口
5. **向后兼容**: 保持与原有API的完全兼容

### 添加新平台支持

1. 创建新的下载器文件：
```python
# backend/src/core/downloaders/newplatform_downloader.py
from .base_downloader import BaseDownloader

class NewPlatformDownloader(BaseDownloader):
    """新平台下载器"""
    
    PLATFORM_NAME = "newplatform"
    SUPPORTED_DOMAINS = ["newplatform.com", "www.newplatform.com"]
    
    async def download(self, url: str, options: DownloadOptions, 
                      progress_callback=None, task_id: str = None) -> dict:
        # 实现下载逻辑
        pass
```

2. 在工厂中注册：
```python
# backend/src/core/downloaders/downloader_factory.py
from .newplatform_downloader import NewPlatformDownloader

# 添加到下载器列表
self._downloaders = [
    # ... 其他下载器
    NewPlatformDownloader(),
]
```

## 项目结构

```
AllVideoDownload/
├── backend/                    # 后端代码
│   ├── src/                   # 源代码
│   │   ├── api/              # API路由
│   │   ├── core/             # 核心功能
│   │   │   ├── downloaders/  # 下载器模块
│   │   │   ├── downloader.py # 主下载器
│   │   │   └── ...
│   │   ├── models/           # 数据模型
│   │   └── utils/            # 工具函数
│   ├── data/                 # 数据存储
│   └── main.py              # 入口文件
├── frontend/                  # 前端代码
│   ├── src/
│   │   ├── components/       # React组件
│   │   ├── hooks/           # 自定义Hooks
│   │   └── App.tsx          # 主应用
│   └── package.json
└── docker-compose.yml        # Docker配置
```

## 前端更新说明

### 平台信息展示

前端已更新以充分利用后端的模块化下载器架构：

1. **下载页面**
   - 视频信息展示包含平台标识
   - 下载任务列表显示平台标签
   - 使用图标和颜色区分不同平台

2. **历史页面**
   - 任务列表显示平台信息
   - 支持按平台筛选历史记录
   - 平台标签可视化展示

3. **系统页面**
   - 支持平台列表使用标签展示
   - 直观显示所有支持的平台

### 平台标识配置

```typescript
const platformConfig = {
  youtube: { icon: <YoutubeOutlined />, color: 'red', name: 'YouTube' },
  bilibili: { icon: <PlayCircleOutlined />, color: 'pink', name: 'Bilibili' },
  douyin: { icon: <PlayCircleOutlined />, color: 'black', name: '抖音' },
  // ... 其他平台配置
};
```

## API接口

### 下载相关

- `POST /api/v1/downloads/info` - 获取视频信息
- `POST /api/v1/downloads/start` - 开始下载任务
- `GET /api/v1/downloads/tasks` - 获取任务列表
- `DELETE /api/v1/downloads/tasks/{task_id}` - 删除任务

### 系统相关

- `GET /api/v1/system/info` - 获取系统信息
- `GET /api/v1/system/settings` - 获取系统设置
- `PUT /api/v1/system/settings` - 更新系统设置

## 开发指南

### 环境准备

1. **后端环境**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或
   venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

2. **前端环境**
   ```bash
   cd frontend
   npm install
   ```

### 启动开发服务器

1. **启动后端**
   ```bash
   cd backend
   python main.py
   ```

2. **启动前端**
   ```bash
   cd frontend
   npm run dev
   ```

### 数据库迁移

项目使用SQLAlchemy自动管理数据库结构，首次运行会自动创建所需表。

### WebSocket通信

项目使用WebSocket实现实时进度更新：

```python
# 后端发送进度
await websocket_manager.send_message({
    "type": "download_progress",
    "task_id": task_id,
    "progress": progress,
    "title": title
})
```

```typescript
// 前端接收进度
const { lastMessage } = useWebSocket({
    url: 'ws://localhost:8000/ws',
    onMessage: (data) => {
        // 处理进度更新
    }
});
```

## 部署说明

### Docker部署

```bash
docker-compose up -d
```

### 手动部署

1. 配置环境变量
2. 安装依赖
3. 配置反向代理（nginx）
4. 启动服务

## 注意事项

1. **Cookie管理**: 某些平台需要登录Cookie才能下载高质量视频
2. **速率限制**: 避免频繁请求导致IP被封
3. **存储空间**: 确保有足够的磁盘空间存储下载文件
4. **性能优化**: AI字幕生成需要较高的CPU/GPU资源

**注意：** 本文档会随着项目发展持续更新，请关注最新版本。 完善字幕API路由：在主后端添加完整的字幕记录管理API
统一API架构：确保所有模块都有一致的记录管理接口