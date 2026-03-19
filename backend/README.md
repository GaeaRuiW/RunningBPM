# RunningBPM 后端

FastAPI 后端服务，提供音频处理 API。

## 环境要求

- Python 3.13+
- FFmpeg
- [uv](https://github.com/astral-sh/uv)（推荐）或 pip

## 快速启动

```bash
# 安装依赖
cp .env.example .env    # 按需修改配置
uv sync

# 启动开发服务器
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API 文档：http://localhost:8000/docs

## 环境变量

参见 `.env.example`，支持以下配置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS 允许的源 |
| `MAX_FILE_SIZE` | `524288000` | 单文件上限 (500MB) |
| `CLEANUP_INTERVAL_HOURS` | `1` | 清理间隔 |
| `CLEANUP_MAX_AGE_HOURS` | `24` | 文件保留时长 |
| `MAX_GLOBAL_TASKS` | `10` | 全局最大并发 |

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/combine` | 音频合成（支持批量） |
| `POST` | `/api/extract` | 节拍器提取（单文件） |
| `POST` | `/api/extract-batch` | 节拍器提取（批量） |
| `POST` | `/api/concatenate` | 音乐拼接（支持淡入淡出） |
| `POST` | `/api/detect-bpm` | BPM 自动检测 |
| `GET` | `/api/progress/{task_id}` | 查询任务进度 |
| `POST` | `/api/cancel/{task_id}` | 取消任务 |
| `GET` | `/api/download/{filename}` | 下载文件 |
| `POST` | `/api/batch-download` | 批量下载 (ZIP) |
| `GET` | `/api/formats/{format}` | 查询可用格式 |
| `GET` | `/api/server-info` | 服务器信息 |
| `GET` | `/api/health` | 健康检查 |
| `WS` | `/ws/progress/{task_id}` | WebSocket 进度推送 |

## 项目结构

```
backend/
├── main.py                 # FastAPI 应用（路由、中间件、安全）
├── services/
│   ├── audio_service.py    # 音频处理核心（Demucs AI、librosa）
│   ├── format_service.py   # 格式检测与降级转换
│   └── progress_service.py # 任务进度管理（线程安全）
├── .env.example            # 环境变量模板
├── pyproject.toml          # uv 项目配置
├── requirements.txt        # pip 依赖
└── Dockerfile              # Gunicorn + Uvicorn 生产部署
```

## 生产部署

使用 Gunicorn 多 worker 模式：

```bash
gunicorn -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 600 main:app
```

或使用 Docker：

```bash
docker build -t runningbpm-backend .
docker run -p 8000:8000 -v uploads:/app/uploads -v outputs:/app/outputs runningbpm-backend
```
