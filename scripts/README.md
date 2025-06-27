# AVD Web版本 - 启动停止脚本使用指南

本目录包含了AVD Web版本的一键启动停止脚本，支持不同操作系统和部署方式。

## 🚀 快速开始

### Linux/Mac用户

```bash
# 最简单的方式 - 快速启动
./scripts/quick-start.sh

# 完整功能启动
./scripts/start.sh

# 停止服务
./scripts/stop.sh
```

### Windows用户

```batch
REM 启动服务
scripts\start.bat

REM 停止服务
scripts\stop.bat
```

## 📋 脚本清单

### 主要脚本

| 脚本名称 | 适用系统 | 功能描述 |
|---------|---------|---------|
| `start.sh` | Linux/Mac | 完整功能的启动脚本 |
| `start.bat` | Windows | Windows版启动脚本 |
| `stop.sh` | Linux/Mac | 停止服务脚本 |
| `stop.bat` | Windows | Windows版停止脚本 |
| `quick-start.sh` | Linux/Mac | 简化的快速启动脚本 |
| `docker-manager.sh` | Linux/Mac | Docker专用管理脚本 |

## 🔧 详细使用说明

### 1. 启动脚本 (`start.sh` / `start.bat`)

功能最完整的启动脚本，支持多种模式和完整的环境检查。

#### 基本用法
```bash
# Linux/Mac
./scripts/start.sh [command] [mode]

# Windows
scripts\start.bat [command] [mode]
```

#### 支持的命令
- `start` - 启动服务（默认）
- `stop` - 停止服务
- `restart` - 重启服务
- `status` - 检查服务状态
- `help` - 显示帮助信息

#### 支持的模式
- `dev` - 开发模式（默认），支持热重载
- `prod` - 生产模式，会构建优化版本
- `docker` - Docker容器模式

#### 示例命令
```bash
# 开发模式启动
./scripts/start.sh start dev

# 生产模式启动
./scripts/start.sh start prod

# Docker模式启动
./scripts/start.sh start docker

# 检查服务状态
./scripts/start.sh status

# 重启服务
./scripts/start.sh restart dev
```

### 2. 停止脚本 (`stop.sh` / `stop.bat`)

专门用于停止服务的脚本，支持强制停止和选择性停止。

#### 基本用法
```bash
# Linux/Mac
./scripts/stop.sh [选项]

# Windows
scripts\stop.bat [选项]
```

#### 支持的选项
- 无参数 - 正常停止所有服务
- `--force` / `-f` - 强制停止所有相关进程
- `--docker` / `-d` - 仅停止Docker服务
- `--help` / `-h` - 显示帮助信息

#### 示例命令
```bash
# 正常停止
./scripts/stop.sh

# 强制停止
./scripts/stop.sh --force

# 仅停止Docker
./scripts/stop.sh --docker
```

### 3. 快速启动脚本 (`quick-start.sh`)

最简化的启动脚本，适合日常快速启动使用。

#### 特点
- 🚀 一键启动，无需参数
- ✅ 智能检测服务状态
- 📦 自动安装依赖
- 🔄 跳过已运行的服务

#### 使用方法
```bash
./scripts/quick-start.sh
```

### 4. Docker管理脚本 (`docker-manager.sh`)

专门用于管理Docker容器化部署的完整解决方案。

#### 基本用法
```bash
./scripts/docker-manager.sh <command> [options]
```

#### 基础命令
```bash
# 启动服务
./scripts/docker-manager.sh start [-d]

# 停止服务
./scripts/docker-manager.sh stop [--remove-orphans]

# 重启服务
./scripts/docker-manager.sh restart

# 查看状态
./scripts/docker-manager.sh status

# 查看日志
./scripts/docker-manager.sh logs [service] [-f]
```

#### 构建命令
```bash
# 构建镜像
./scripts/docker-manager.sh build [--no-cache]

# 更新镜像
./scripts/docker-manager.sh update
```

#### 管理命令
```bash
# 进入容器
./scripts/docker-manager.sh enter backend
./scripts/docker-manager.sh enter frontend

# 清理资源
./scripts/docker-manager.sh cleanup [--images|--all]
```

#### 数据管理
```bash
# 备份数据
./scripts/docker-manager.sh backup [目录]

# 恢复数据
./scripts/docker-manager.sh restore <备份目录>
```

## 🌟 使用场景推荐

### 日常开发
```bash
# 第一次启动
./scripts/start.sh start dev

# 日常快速启动
./scripts/quick-start.sh

# 停止服务
./scripts/stop.sh
```

### 生产部署
```bash
# Docker方式（推荐）
./scripts/docker-manager.sh start -d

# 或传统方式
./scripts/start.sh start prod
```

### 开发调试
```bash
# 查看服务状态
./scripts/start.sh status

# 查看Docker日志
./scripts/docker-manager.sh logs backend -f

# 进入容器调试
./scripts/docker-manager.sh enter backend
```

## 🔍 故障排除

### 端口被占用
```bash
# 强制停止所有服务
./scripts/stop.sh --force

# 检查端口使用情况
netstat -tulpn | grep -E "(3000|8000)"
```

### Docker问题
```bash
# 清理Docker资源
./scripts/docker-manager.sh cleanup --all

# 重新构建镜像
./scripts/docker-manager.sh build --no-cache
```

### 依赖问题
```bash
# 删除node_modules重新安装
rm -rf frontend/node_modules
./scripts/start.sh start dev

# 删除Python虚拟环境重新创建
rm -rf backend/venv
./scripts/start.sh start dev
```

## 📂 生成的文件说明

### 日志文件
- `logs/backend.log` - 后端服务日志
- `logs/frontend.log` - 前端服务日志

### 进程文件
- `.pids.backend` - 后端进程ID
- `.pids.frontend` - 前端进程ID

### 临时文件
- `.lock` - 运行锁文件
- `backend/.lock` - 后端锁文件
- `frontend/.lock` - 前端锁文件

## 🎯 最佳实践

### 开发环境
1. 使用 `quick-start.sh` 进行日常启动
2. 使用开发模式以获得热重载功能
3. 定期使用 `status` 命令检查服务状态

### 生产环境
1. 优先使用Docker部署方式
2. 使用生产模式启动以获得最佳性能
3. 定期备份数据和配置

### 维护操作
1. 定期清理Docker资源避免磁盘空间不足
2. 监控日志文件大小，必要时清理
3. 保持依赖包的更新

## 🚨 注意事项

1. **权限问题**：Linux/Mac系统需要确保脚本有执行权限
2. **端口冲突**：确保3000和8000端口没有被其他应用占用
3. **环境依赖**：需要预先安装Python 3.8+和Node.js 16+
4. **Docker环境**：使用Docker模式需要安装Docker和Docker Compose
5. **防火墙设置**：确保防火墙允许相应端口的访问

## 📞 获取帮助

每个脚本都支持 `--help` 参数来获取详细的使用说明：

```bash
./scripts/start.sh --help
./scripts/stop.sh --help
./scripts/docker-manager.sh --help
```

如果遇到问题，请按以下顺序检查：
1. 查看脚本的帮助信息
2. 检查日志文件内容
3. 验证环境依赖是否正确安装
4. 尝试强制停止后重新启动 