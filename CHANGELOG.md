# 更新日志

所有重要的项目变更都会记录在这个文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [2.0.0] - 2025-03-19

### 新增功能
- **BPM 自动检测**：上传音乐后一键检测 BPM（`POST /api/detect-bpm`）
- **音频预览**：上传后直接在浏览器中试听文件
- **BPM 预设快选**：散步 100 / 慢跑 140 / 跑步 170 / 冲刺 190 一键设置
- **配速计算器**：输入配速（分/公里）自动推荐 BPM
- **拼接淡入淡出**：相邻曲目 0-10 秒平滑过渡（`crossfade_ms` 参数）
- **暗色模式切换**：手动切换 自动/亮色/暗色，localStorage 持久化
- **处理历史记录**：Dashboard 展示最近处理任务
- **批量节拍器提取**：一次上传多个文件批量提取（`POST /api/extract-batch`）
- **任务取消**：处理中可随时取消（`POST /api/cancel/{task_id}`）
- **健康检查端点**：`GET /api/health`，Docker 容器自动探活
- **服务器信息端点**：`GET /api/server-info`，返回 CPU 核心数和默认并发数
- **文件管理**：上传列表支持删除单个文件；拼接页支持调整文件顺序

### 后端改进
- 所有配置环境变量化（CORS、文件限制、清理周期、并发数）
- 结构化日志（`logging` 模块）
- 速率限制（slowapi，每 IP 10 次/分钟）
- 文件自动清理（后台线程定时删除过期文件和任务记录）
- 进度服务线程安全（`threading.Lock`）
- 全局线程池复用（不再每个任务创建新的 `ThreadPoolExecutor`）
- 安全加固：文件名清洗、下载路径穿越防护、参数校验
- 生产部署：Gunicorn 多 worker + Dockerfile HEALTHCHECK

### 前端改进
- 全中文界面（不再中英混搭）
- 自然跑道主题：翡翠绿配色 + CSS 跑步场景动画（山丘、云朵、太阳、麦穗、跑者）
- 移动端响应式：侧栏折叠、单列网格、44px 触控目标
- 网络错误处理：连续失败提示、30 分钟超时保护
- 输入校验反馈：BPM/时长超范围实时提示
- 文件大小校验：500MB 限制，超出前端拦截
- 设置保留：重新处理时保留 BPM、格式等设置

### 部署改进
- Docker Compose 环境变量传递 + 资源限制（4GB）+ 健康检查依赖
- Nginx 安全头 + gzip 压缩 + 500MB 上传限制 + 静态缓存
- `.env.example` 配置模板（后端 + 前端）
- GitHub Actions CI/CD：打 tag 自动构建 Docker 镜像推送到 ghcr.io
- GitHub Actions 云端处理：无需部署，直接在 Actions 中处理音频

### 项目结构
- 删除 10 个根目录独立调试脚本
- 删除测试数据、样本音乐、构建日志等无用文件
- 新增 `CODE_OF_CONDUCT.md`、`.github/SECURITY.md`
- CI 升级到 Python 3.13 + GitHub Actions v4

## [1.0.0] - 2024-01-XX

### 新增
- 音频合成功能（节拍器 + 音乐）
- 节拍器提取功能（Demucs AI 分离）
- 多音乐拼接功能
- React 前端界面
- FastAPI 后端服务
- 音频格式自定义（降级/同级转换）
- 进度显示（WebSocket 实时更新）
- 批量下载（ZIP 打包）
- Docker 支持
