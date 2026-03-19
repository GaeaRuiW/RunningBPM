# RunningBPM - 跑步音乐制作工具

一个开源项目，用于为跑步爱好者制作带节拍器的音乐。

## 功能特性

1. **音频合成**：用户上传节拍器音频和音乐音频（支持批量上传多个音乐文件），输入想要的步频，自动批量合成带节拍器的音乐
2. **节拍器提取**：从带有节拍器的音乐中自动提取出节拍器
3. **多音乐拼接**：一次上传多个音乐，设置目标时长，将多个音乐拼接成带节拍器的长音乐
4. **格式自定义**：支持多种音频格式（MP3, WAV, FLAC, M4A, OGG），智能格式降级（只能降级或同级，不能升级）
5. **实时进度显示**：处理过程中实时显示进度条和状态信息
6. **批量下载**：支持批量生成和下载多个文件

## 技术栈

- **后端**：FastAPI (Python)
- **前端**：React + TypeScript
- **音频处理**：pydub, librosa, numpy, scipy

## 项目结构

```
RunningBPM/
├── backend/                  # FastAPI 后端
│   ├── main.py              # 主应用入口
│   ├── services/            # 业务逻辑服务
│   │   ├── audio_service.py     # 音频处理服务
│   │   ├── format_service.py    # 格式检测与转换
│   │   └── progress_service.py  # 任务进度管理
│   ├── pyproject.toml       # Python 项目配置 (uv)
│   ├── requirements.txt     # Python 依赖
│   └── Dockerfile           # 后端容器
├── frontend/                # React 前端
│   ├── src/
│   │   ├── pages/           # 页面组件
│   │   │   ├── Dashboard.tsx    # 首页仪表盘
│   │   │   ├── Mixer.tsx        # 音频合成页面
│   │   │   ├── Extractor.tsx    # 节拍器提取页面
│   │   │   └── Stitcher.tsx     # 音乐拼接页面
│   │   ├── components/      # 共享组件
│   │   ├── App.tsx          # 路由配置
│   │   └── index.tsx        # 入口文件
│   ├── public/              # 静态资源
│   ├── nginx.conf           # Nginx 反向代理配置
│   ├── package.json         # Node.js 依赖
│   └── Dockerfile           # 前端容器
├── .github/                 # GitHub 配置
│   ├── workflows/ci.yml     # CI/CD 流水线
│   ├── ISSUE_TEMPLATE/      # Issue 模板
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── SECURITY.md          # 安全政策
├── docker-compose.yml       # Docker 编排
├── CODE_OF_CONDUCT.md       # 行为准则
├── CONTRIBUTING.md          # 贡献指南
├── CHANGELOG.md             # 更新日志
├── LICENSE                  # MIT 许可证
└── README.md
```

## 快速开始

### 方式一：使用 Docker（推荐）

1. 使用 docker-compose 一键启动：
```bash
docker-compose up -d
```

2. 访问应用：
- 前端：http://localhost:3000
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

### 方式二：本地开发

#### 环境要求

- Python 3.13+
- uv（Python 包管理器，会自动安装）
- Node.js 16+
- npm 或 yarn
- FFmpeg（用于音频处理）

#### 后端启动

1. 安装 uv（如果尚未安装）：
```bash
pip install uv
```

2. 进入后端目录并同步依赖：
```bash
cd backend
uv sync
```

3. 启动 FastAPI 服务器：
```bash
uv run uvicorn main:app --reload
```

或者使用启动脚本：
```bash
./start_backend.sh
```

后端将在 `http://localhost:8000` 运行

#### 前端启动

1. 进入前端目录并安装依赖：
```bash
cd frontend
npm install
```

2. 启动 React 开发服务器：
```bash
npm start
```

前端将在 `http://localhost:3000` 运行

## API 接口说明

### 1. 音频合成（支持批量处理）
- **端点**：`POST /api/combine`
- **参数**：
  - `metronome`: 节拍器音频文件
  - `music_files`: 音乐音频文件列表（支持多个）
  - `target_bpm`: 目标步频（整数）
  - `output_format`: 输出格式（默认 mp3）
  - `auto_extract_metronome`: 是否自动提取节拍器（布尔值，默认 false）
  - `metronome_volume`: 节拍器音量调整（dB，默认 0，范围 -20 到 +20）
  - `max_concurrent`: 最大并发处理数（默认 4，范围 1 到 CPU 核心数）
- **返回**：包含 `task_id` 和 `files` 数组的 JSON（每个文件包含 `download_url` 和 `filename`）

### 2. 节拍器提取
- **端点**：`POST /api/extract`
- **参数**：
  - `music`: 带节拍器的音乐文件
  - `output_format`: 输出格式（默认 mp3）
- **返回**：包含 `task_id` 和 `download_url` 的 JSON

### 3. 音乐拼接
- **端点**：`POST /api/concatenate`
- **参数**：
  - `music_files`: 多个音乐文件（数组）
  - `target_duration`: 目标总时长（秒，浮点数）
  - `output_format`: 输出格式（默认 mp3）
- **返回**：包含 `task_id` 和 `download_url` 的 JSON

### 4. 获取可用格式
- **端点**：`GET /api/formats/{source_format}`
- **返回**：可用的输出格式列表

### 5. 获取服务器信息
- **端点**：`GET /api/server-info`
- **返回**：服务器 CPU 核心数和默认最大并发数

### 6. 获取进度
- **端点**：`GET /api/progress/{task_id}`
- **返回**：任务进度信息（进度百分比、状态、消息）

### 7. WebSocket 进度更新
- **端点**：`WS /ws/progress/{task_id}`
- **返回**：实时进度更新（JSON）

### 8. 文件下载
- **端点**：`GET /api/download/{filename}`
- **返回**：处理后的音频文件

### 9. 批量下载
- **端点**：`POST /api/batch-download`
- **参数**：
  - `filenames`: 文件名列表（数组）
- **返回**：ZIP 压缩包

## 使用说明

1. **音频合成**：
   - 上传节拍器音频和音乐音频（支持同时上传多个音乐文件进行批量处理）
   - 如果上传的"节拍器"文件是带节拍器的完整音乐，可以勾选"自动提取节拍器"选项
   - 输入目标步频（BPM），建议范围 120-200
   - 选择输出格式（根据源文件格式自动限制可选格式）
   - 系统会自动提取节拍器（如果启用）并调整节拍器速度，然后与每个音乐文件合成
   - 支持批量下载所有生成的文件
   - 实时显示处理进度

2. **节拍器提取**：
   - 上传带有节拍器的音乐文件
   - 选择输出格式
   - 系统会使用频谱分析提取节拍器信号
   - 实时显示处理进度

3. **音乐拼接**：
   - 选择多个音乐文件（可多选）
   - 设置目标时长（秒）
   - 选择输出格式
   - 系统会循环拼接音乐直到达到目标时长
   - 支持批量下载多个生成的文件

## 注意事项

- **支持的音频格式**：MP3, WAV, FLAC, M4A, OGG 等常见格式
- **格式转换规则**：
  - 只能从高质量格式转换为低质量或同级格式
  - 例如：FLAC → MP3/WAV/FLAC ✅，MP3 → FLAC ❌
  - 系统会自动检测源文件格式并限制可选输出格式
- **处理时间**：处理大文件可能需要一些时间，请耐心等待
- **文件存储**：
  - 上传的文件会临时保存在 `backend/uploads/` 目录
  - 处理后的文件保存在 `backend/outputs/` 目录
- **进度跟踪**：使用任务ID可以查询处理进度，支持轮询和WebSocket两种方式

## 开发计划

- [x] 项目基础结构
- [x] 音频合成功能
- [x] 节拍器提取功能
- [x] 多音乐拼接功能
- [x] 前端界面开发
- [x] 音频格式自定义
- [x] 进度条显示
- [x] 批量下载功能
- [x] Docker 支持
- [ ] 音频预览功能
- [ ] 用户账户系统
- [ ] 云端存储集成

## 贡献

欢迎提交 Issue 和 Pull Request！请阅读 [贡献指南](CONTRIBUTING.md) 和 [行为准则](CODE_OF_CONDUCT.md)。

## 许可证

MIT License

