FROM python:3.13-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
RUN pip install uv

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 使用 uv 安装依赖到系统 Python
# 使用 --no-cache 减少镜像大小
RUN uv pip install --system --no-cache -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p uploads outputs

# 创建 Demucs 模型缓存目录
# 这样模型会在构建时下载,而不是运行时
ENV TORCH_HOME=/app/.cache/torch
RUN mkdir -p /app/.cache/torch

# 预下载 Demucs 模型 (可选,加快首次运行)
# 取消注释以下行以在构建时下载模型
# RUN python -c "from demucs.pretrained import get_model; get_model('htdemucs')"

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
