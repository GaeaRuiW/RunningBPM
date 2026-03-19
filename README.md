<div align="center">

# RunningBPM

**跑步音乐制作工具 — 让每一步都踩在节拍上**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://python.org)
[![React 18](https://img.shields.io/badge/React-18-61dafb.svg)](https://reactjs.org)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ed.svg)](docker-compose.yml)

一个开源的跑步音乐制作工具，支持音频合成、节拍器提取和多曲目拼接。
上传你的音乐，设置目标 BPM，一键生成专属跑步歌单。

[快速开始](#-快速开始) · [功能特性](#-功能特性) · [部署指南](#-部署指南) · [API 文档](#-api-接口) · [贡献](#-贡献)

</div>

---

## ✨ 功能特性

### 核心功能

| 功能 | 说明 |
|------|------|
| **音频合成** | 上传节拍器 + 音乐，指定 BPM，自动合成跑步音乐。支持批量处理多个文件 |
| **节拍器提取** | 从已有跑步音乐中，通过 AI（Demucs）自动分离提取节拍器音轨 |
| **音乐拼接** | 多首曲目拼接为指定时长的连续音乐，支持文件排序 |

### 体验特性

- **实时进度** — 跑者动画 + 进度条，处理过程一目了然
- **任务取消** — 长时间处理可随时取消，释放资源
- **文件管理** — 上传列表支持删除单个文件；拼接页支持调整顺序
- **格式智能降级** — 支持 MP3、WAV、FLAC、M4A、OGG，只允许同级或降级转换
- **批量下载** — 多文件一键打包 ZIP 下载
- **移动端适配** — 响应式布局，手机平板均可使用
- **亮/暗色主题** — 跟随系统自动切换

### 后端特性

- **自动清理** — 上传文件和输出文件定时清理，不占磁盘
- **速率限制** — 防止恶意请求，保护服务器资源
- **并发控制** — 可配置最大并发数，合理分配 CPU
- **安全防护** — 文件名过滤、路径校验、安全头、CORS 环境变量化
- **健康检查** — `/api/health` 端点，容器编排自动探活
- **结构化日志** — 方便排查问题和监控运行状态

## 🛠 技术栈

| 层 | 技术 |
|----|------|
| **前端** | React 18 + TypeScript + Framer Motion |
| **后端** | FastAPI + Gunicorn + Uvicorn |
| **音频处理** | Demucs (AI 分离) + librosa + pydub + scipy |
| **容器化** | Docker + Docker Compose + Nginx |
| **代码质量** | Black + Flake8 + pre-commit hooks |

## 🚀 快速开始

### 一键 Docker 部署（推荐）

```bash
git clone https://github.com/yourusername/RunningBPM.git
cd RunningBPM
docker-compose up -d
```

打开浏览器访问 **http://localhost:3000** 即可使用。

> 首次启动需要下载 AI 模型（约 1GB），请耐心等待。

### 本地开发

#### 环境要求

- Python 3.13+ + [uv](https://github.com/astral-sh/uv)
- Node.js 18+ + npm
- FFmpeg

#### 后端

```bash
cd backend
cp .env.example .env    # 按需修改配置
uv sync
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端

```bash
cd frontend
cp .env.example .env    # 配置 API 地址
npm install
npm start
```

前端 http://localhost:3000 · 后端 http://localhost:8000 · API 文档 http://localhost:8000/docs

## 📐 项目结构

```
RunningBPM/
├── backend/
│   ├── main.py                 # FastAPI 应用 (路由、中间件、安全)
│   ├── services/
│   │   ├── audio_service.py    # 音频处理核心 (Demucs AI 分离)
│   │   ├── format_service.py   # 格式检测与降级转换
│   │   └── progress_service.py # 任务进度管理 (线程安全)
│   ├── .env.example            # 环境变量模板
│   ├── Dockerfile              # Gunicorn 多 worker 部署
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── config.ts           # API 地址集中配置
│   │   ├── pages/              # 页面: 首页、合成、拼接、提取
│   │   └── components/         # 组件: 跑步场景动画、向导、上传区
│   ├── nginx.conf              # 反向代理 + 安全头 + gzip
│   ├── .env.example            # 环境变量模板
│   └── Dockerfile
├── docker-compose.yml          # 一键编排 (资源限制 + 健康检查)
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── LICENSE                     # MIT
└── README.md
```

## ⚙️ 部署指南

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS 允许的源 (逗号分隔) |
| `MAX_FILE_SIZE` | `524288000` | 单文件大小上限 (字节, 默认 500MB) |
| `CLEANUP_INTERVAL_HOURS` | `1` | 文件清理间隔 (小时) |
| `CLEANUP_MAX_AGE_HOURS` | `24` | 文件最大保留时间 (小时) |
| `MAX_GLOBAL_TASKS` | `10` | 全局最大并发任务数 |
| `REACT_APP_API_URL` | _(空)_ | 前端 API 地址 (Docker 部署留空) |

### Docker 资源建议

| 服务 | 最低内存 | 建议内存 | 说明 |
|------|----------|----------|------|
| backend | 1 GB | 4 GB | Demucs AI 模型需要较多内存 |
| frontend | 64 MB | 128 MB | Nginx 静态资源服务 |

### 生产部署清单

- [ ] 修改 `ALLOWED_ORIGINS` 为你的域名
- [ ] 配置 Nginx HTTPS (Let's Encrypt)
- [ ] 调整 `docker-compose.yml` 中的端口映射
- [ ] 根据服务器配置调整内存限制
- [ ] 确保有足够磁盘空间存放临时音频文件

## 📡 API 接口

所有接口以 `/api` 为前缀。完整文档访问 `/docs` (Swagger UI)。

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/combine` | 音频合成 (支持批量) |
| `POST` | `/api/extract` | 节拍器提取 |
| `POST` | `/api/concatenate` | 音乐拼接 |
| `GET` | `/api/progress/{task_id}` | 查询任务进度 |
| `POST` | `/api/cancel/{task_id}` | 取消任务 |
| `GET` | `/api/download/{filename}` | 下载文件 |
| `POST` | `/api/batch-download` | 批量下载 (ZIP) |
| `GET` | `/api/formats/{format}` | 查询可用格式 |
| `GET` | `/api/server-info` | 服务器信息 |
| `GET` | `/api/health` | 健康检查 |
| `WS` | `/ws/progress/{task_id}` | WebSocket 进度推送 |

## 🗺 路线图

- [x] 音频合成 + 批量处理
- [x] AI 节拍器提取 (Demucs)
- [x] 多音乐拼接
- [x] 实时进度 + 任务取消
- [x] 文件管理 (删除/排序)
- [x] 移动端响应式
- [x] Docker 一键部署
- [x] 速率限制 + 安全防护
- [x] 自动文件清理
- [x] 上传后音频预览试听
- [x] BPM 自动检测
- [x] 拼接淡入淡出过渡
- [x] 处理历史记录
- [x] 配速计算器
- [x] 暗色模式手动切换
- [x] 批量节拍器提取
- [x] GitHub Actions 云端处理
- [ ] 用户账户系统

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

请阅读 [贡献指南](CONTRIBUTING.md) 和 [行为准则](CODE_OF_CONDUCT.md)。

## 📄 许可证

[MIT License](LICENSE) - 自由使用、修改和分发。
