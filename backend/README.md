# RunningBPM 后端

## Python 版本要求

本项目需要 **Python 3.13+**。

## 使用 uv 管理依赖

本项目使用 [uv](https://github.com/astral-sh/uv) 作为 Python 包管理器。

### 安装 uv

```bash
pip install uv
```

或者使用官方安装脚本：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 开发环境设置

1. 同步依赖（会自动创建虚拟环境）：
```bash
uv sync
```

2. 运行应用：
```bash
uv run uvicorn main:app --reload
```

或者激活虚拟环境后直接运行：
```bash
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows

uvicorn main:app --reload
```

### 添加新依赖

```bash
uv add package-name
```

### 更新依赖

```bash
uv sync
```

### 查看依赖

依赖定义在 `pyproject.toml` 文件中。

## 传统方式（使用 requirements.txt）

如果需要使用传统的 `requirements.txt`，可以运行：

```bash
uv pip compile pyproject.toml -o requirements.txt
```

这会从 `pyproject.toml` 生成 `requirements.txt` 文件。

