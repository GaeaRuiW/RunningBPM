# 更新日志

所有重要的项目变更都会记录在这个文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [未发布]

### 新增
- 音频格式自定义功能（支持降级/同级格式转换）
- 进度显示功能（WebSocket实时更新）
- 批量下载功能
- Docker 支持（Dockerfile 和 docker-compose.yml）
- 音频合成页面支持自动提取节拍器（如果上传的是带节拍器的完整音乐）
- 音频合成页面支持同时上传多个音乐文件进行批量生成

### 改进
- 优化音频处理性能
- 改进用户界面体验

### 升级
- 升级到 Python 3.13（Python 3.14 的依赖包支持尚不完整）
- 升级所有依赖包到最新版本以支持 Python 3.13：
  - FastAPI >= 0.115.0
  - Uvicorn >= 0.32.0
  - NumPy >= 2.1.0
  - SciPy >= 1.14.0
  - Pydantic >= 2.9.0
  - 以及其他所有依赖包

## [1.0.0] - 2024-01-XX

### 新增
- 音频合成功能（节拍器 + 音乐）
- 节拍器提取功能
- 多音乐拼接功能
- React 前端界面
- FastAPI 后端服务

