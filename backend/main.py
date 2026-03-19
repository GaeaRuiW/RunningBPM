import os
import re
import time
import logging
import threading
import uuid
import zipfile
import asyncio
import aiofiles
import json
import shutil
import multiprocessing
from datetime import datetime
from typing import List, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from starlette.responses import JSONResponse

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from services.audio_service import AudioService
from services.format_service import FormatService
from services.progress_service import progress_service

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("runningbpm")

# ---------------------------------------------------------------------------
# Environment config
# ---------------------------------------------------------------------------
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 524288000))  # 500MB
CLEANUP_INTERVAL_HOURS = int(os.getenv("CLEANUP_INTERVAL_HOURS", 1))
CLEANUP_MAX_AGE_HOURS = int(os.getenv("CLEANUP_MAX_AGE_HOURS", 24))
MAX_GLOBAL_TASKS = int(os.getenv("MAX_GLOBAL_TASKS", 10))

# ---------------------------------------------------------------------------
# App creation
# ---------------------------------------------------------------------------
app = FastAPI(title="RunningBPM API", version="1.1.0")

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(status_code=429, content={"detail": "请求太频繁，请稍后再试"})


# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保上传和输出目录存在
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Global thread pool (reused across all tasks)
global_executor = ThreadPoolExecutor(max_workers=min(multiprocessing.cpu_count(), 8))

audio_service = AudioService()
format_service = FormatService()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def sanitize_filename(filename: str) -> str:
    """Remove potentially dangerous characters from filenames"""
    # Keep unicode chars (Chinese), alphanumeric, spaces, dots, hyphens, underscores
    name = re.sub(r'[^\w\s.\-\u4e00-\u9fff\u3400-\u4dbf]', '', filename)
    # Prevent path traversal
    name = name.replace('..', '').strip('. ')
    return name or 'unnamed'


# ---------------------------------------------------------------------------
# Background cleanup worker
# ---------------------------------------------------------------------------
def cleanup_worker():
    """Background thread for periodic file & task cleanup"""
    while True:
        time.sleep(CLEANUP_INTERVAL_HOURS * 3600)
        try:
            # Clean old files
            cutoff = time.time() - (CLEANUP_MAX_AGE_HOURS * 3600)
            for directory in [UPLOAD_DIR, OUTPUT_DIR]:
                for f in directory.iterdir():
                    if f.is_file() and f.stat().st_mtime < cutoff:
                        f.unlink(missing_ok=True)
                        logger.info(f"Cleaned up: {f.name}")
            # Clean old task progress
            cleaned = progress_service.cleanup_old_tasks(CLEANUP_MAX_AGE_HOURS)
            if cleaned:
                logger.info(f"Cleaned {cleaned} old task records")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


@app.on_event("startup")
async def startup_event():
    thread = threading.Thread(target=cleanup_worker, daemon=True)
    thread.start()
    logger.info("RunningBPM backend started")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    return {"message": "RunningBPM API is running"}


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.1.0"
    }


@app.get("/api/server-info")
async def server_info():
    """获取服务器信息，包括 CPU 核心数（用于前端并发限制）"""
    return {
        "cpu_count": multiprocessing.cpu_count(),
        "default_max_concurrent": min(multiprocessing.cpu_count(), 4)
    }


@app.post("/api/detect-bpm")
@limiter.limit("20/minute")
async def detect_bpm(request: Request, music: UploadFile = File(...)):
    """检测音频文件的 BPM"""
    temp_path = UPLOAD_DIR / f"bpm_{uuid.uuid4()}_{sanitize_filename(music.filename)}"
    try:
        content = await music.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="文件太大")
        with open(temp_path, "wb") as f:
            f.write(content)
        bpm = await run_in_threadpool(audio_service._detect_bpm, str(temp_path))
        logger.info(f"BPM detected: {bpm:.1f} for {music.filename}")
        return {"bpm": round(float(bpm), 1), "filename": music.filename}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BPM detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        temp_path.unlink(missing_ok=True)


@app.get("/api/formats/{source_format}")
async def get_available_formats(source_format: str):
    """
    获取可用的输出格式列表
    """
    available = format_service.get_available_formats(source_format)
    return {
        "source_format": source_format,
        "available_formats": available
    }


# ---------------------------------------------------------------------------
# Task cancellation
# ---------------------------------------------------------------------------
@app.post("/api/cancel/{task_id}")
async def cancel_task(task_id: str):
    success = progress_service.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="任务不存在或已完成")
    return {"success": True, "message": "任务已取消"}


# ---------------------------------------------------------------------------
# Combine audio (background worker)
# ---------------------------------------------------------------------------
def process_combine_audio(
    task_id: str,
    metronome_path: Path,
    music_paths: List[str],
    target_bpm: int,
    output_format: str,
    auto_extract_metronome: bool,
    metronome_volume: int = 0,
    max_concurrent: int = 4
):
    """后台处理音频合成"""
    try:
        progress_service.update_progress(task_id, 5, "文件上传完成，开始处理...")

        # 检测源格式
        progress_service.update_progress(task_id, 20 if auto_extract_metronome else 6, "检测音频文件格式...")
        source_formats = []
        total_files = len(music_paths)

        for idx, music_path in enumerate(music_paths):
            # Check cancellation between files
            if progress_service.is_cancelled(task_id):
                logger.info(f"Task {task_id} cancelled")
                return

            if total_files > 1:
                format_progress = (20 if auto_extract_metronome else 6) + int((idx / total_files) * 2)
                progress_service.update_progress(
                    task_id,
                    format_progress,
                    f"检测文件 {idx + 1}/{total_files} 的格式..."
                )
            source_format = format_service.detect_format(music_path) or "mp3"
            source_formats.append(source_format)

        # 使用最高质量的源格式作为基准
        max_quality_format = max(source_formats, key=lambda f: format_service.get_format_quality(f))

        progress_service.update_progress(
            task_id,
            22 if auto_extract_metronome else 8,
            f"检测到最高质量格式: {max_quality_format}"
        )

        # 验证输出格式
        progress_service.update_progress(
            task_id,
            23 if auto_extract_metronome else 9,
            f"验证输出格式: {output_format}"
        )

        if not format_service.can_convert(max_quality_format, output_format):
            progress_service.fail_task(task_id, f"无法从 {max_quality_format} 转换为 {output_format}")
            return

        # 批量处理每个音乐文件 - 使用多线程并行处理
        output_files = []
        base_progress = 24 if auto_extract_metronome else 10

        progress_service.update_progress(task_id, base_progress, f"准备并行处理 {total_files} 个音乐文件...")

        # 限制最大线程数，避免资源耗尽
        max_workers = min(total_files, multiprocessing.cpu_count(), max_concurrent)

        def process_single_file(args):
            """处理单个文件的函数，用于并行执行"""
            idx, music_path, metronome_path_str, target_bpm, output_format, task_id, base_progress, total = args

            # Check cancellation before starting
            if progress_service.is_cancelled(task_id):
                return {"success": False, "idx": idx, "error": "任务已取消"}

            # Remove UUID prefix (36 chars + 1 underscore)
            original_stem = Path(music_path).stem[37:]
            output_filename = f"{original_stem} {target_bpm}bpm.{output_format}"
            output_path = OUTPUT_DIR / output_filename

            # 创建进度回调
            def progress_callback(progress: int, message: str):
                # 单个文件的进度映射：每个文件占 (70 / total) 的进度
                file_base = base_progress + int((idx / total) * 70)
                file_progress = file_base + int((progress / 100) * (70 / total))
                progress_service.update_progress(
                    task_id,
                    file_progress,
                    f"处理文件 {idx + 1}/{total}: {message}"
                )

            try:
                audio_svc = AudioService()
                audio_svc.combine_audio(
                    metronome_path=metronome_path_str,
                    music_path=music_path,
                    target_bpm=target_bpm,
                    output_path=str(output_path),
                    output_format=output_format,
                    metronome_volume=metronome_volume,
                    progress_callback=progress_callback
                )

                return {
                    "success": True,
                    "idx": idx,
                    "output": {
                        "download_url": f"/api/download/{output_filename}",
                        "filename": output_filename
                    }
                }
            except Exception as e:
                return {
                    "success": False,
                    "idx": idx,
                    "error": str(e)
                }

        # 准备任务参数
        tasks = [
            (idx, music_path, str(metronome_path), target_bpm, output_format, task_id, base_progress, total_files)
            for idx, music_path in enumerate(music_paths)
        ]

        # 使用全局线程池并行执行
        completed_count = 0
        futures = {global_executor.submit(process_single_file, task): task for task in tasks}

        # 收集结果
        results = {}
        for future in as_completed(futures):
            completed_count += 1

            # Check cancellation
            if progress_service.is_cancelled(task_id):
                logger.info(f"Task {task_id} cancelled during processing")
                # Cancel remaining futures
                for f in futures:
                    f.cancel()
                return

            try:
                result = future.result()
                results[result["idx"]] = result

                # 更新总体进度
                overall_progress = base_progress + int((completed_count / total_files) * 70)
                progress_service.update_progress(
                    task_id,
                    overall_progress,
                    f"已完成 {completed_count}/{total_files} 个文件"
                )
            except Exception as e:
                # 处理异常
                task = futures[future]
                idx = task[0]
                results[idx] = {
                    "success": False,
                    "idx": idx,
                    "error": str(e)
                }

        # 按原始顺序整理结果
        for idx in range(total_files):
            if idx in results:
                result = results[idx]
                if result["success"]:
                    output_files.append(result["output"])
                else:
                    # 记录错误但继续处理其他文件
                    progress_service.update_progress(
                        task_id,
                        base_progress + int((idx / total_files) * 70),
                        f"文件 {idx + 1} 处理失败: {result.get('error', '未知错误')}"
                    )

        progress_service.complete_task(task_id, {
            "files": output_files,
            "count": len(output_files)
        })
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}", exc_info=True)
        progress_service.fail_task(task_id, str(e))


@app.post("/api/combine")
@limiter.limit("10/minute")
async def combine_audio(
    request: Request,
    background_tasks: BackgroundTasks,
    metronome: UploadFile = File(...),
    music_files: List[UploadFile] = File(...),
    target_bpm: int = Form(...),
    output_format: str = Form("mp3"),
    auto_extract_metronome: bool = Form(False),
    metronome_volume: int = Form(0),  # 节拍器音量调整 (dB), 默认0, 范围-20到+20
    max_concurrent: int = Form(4),  # 最大并发处理数，默认4，范围1到cpu核心数
    task_id: Optional[str] = Form(None)
):
    """
    合成节拍器和音乐（支持批量处理多个音乐文件）
    - metronome: 节拍器音频文件（如果 auto_extract_metronome 为 True，可以是带节拍器的完整音乐）
    - music_files: 音乐音频文件列表（支持多个）
    - target_bpm: 目标步频（每分钟步数）
    - output_format: 输出格式（默认 mp3）
    - auto_extract_metronome: 是否自动从节拍器文件中提取节拍器（如果上传的是带节拍器的完整音乐）
    - metronome_volume: 节拍器音量调整 (dB)，范围 -20 到 +20，默认 0
    - task_id: 可选的任务ID，用于进度跟踪
    """
    try:
        # Parameter validation
        if not 60 <= target_bpm <= 300:
            raise HTTPException(status_code=400, detail="BPM 必须在 60-300 之间")
        metronome_volume = max(-20, min(20, metronome_volume))

        # 限制 max_concurrent 范围: 1 到 CPU 核心数
        cpu_count = multiprocessing.cpu_count()
        max_concurrent = max(1, min(max_concurrent, cpu_count))

        # 创建任务ID
        if not task_id:
            task_id = progress_service.create_task()
        else:
            progress_service.create_task(task_id)

        total_files = len(music_files)
        logger.info(f"New combine task: {task_id}, {total_files} files, {target_bpm} BPM")

        progress_service.update_progress(task_id, 2, "接收文件上传...")

        # 准备文件路径
        metronome_id = str(uuid.uuid4())
        metronome_path = UPLOAD_DIR / f"{metronome_id}_{sanitize_filename(metronome.filename)}"

        # 立即保存文件 (使用线程池避免阻塞主循环)
        progress_service.update_progress(task_id, 3, "保存节拍器文件...")

        def save_file_sync(upload_file, destination):
            with open(destination, "wb") as buffer:
                shutil.copyfileobj(upload_file.file, buffer)

        await run_in_threadpool(save_file_sync, metronome, metronome_path)

        # Validate file size
        if metronome_path.stat().st_size > MAX_FILE_SIZE:
            metronome_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=f"节拍器文件过大，最大允许 {MAX_FILE_SIZE // (1024*1024)}MB")

        # 保存音乐文件
        music_paths = []
        progress_service.update_progress(task_id, 4, f"准备保存 {total_files} 个音乐文件...")

        for idx, music_file in enumerate(music_files):
            music_id = str(uuid.uuid4())
            music_path = UPLOAD_DIR / f"{music_id}_{sanitize_filename(music_file.filename)}"

            progress_service.update_progress(
                task_id,
                4 + int((idx / total_files) * 1),
                f"保存音乐文件 {idx + 1}/{total_files}: {music_file.filename}"
            )

            await run_in_threadpool(save_file_sync, music_file, music_path)

            # Validate file size
            if music_path.stat().st_size > MAX_FILE_SIZE:
                music_path.unlink(missing_ok=True)
                raise HTTPException(status_code=400, detail=f"音乐文件 {music_file.filename} 过大，最大允许 {MAX_FILE_SIZE // (1024*1024)}MB")

            music_paths.append(str(music_path))

        progress_service.update_progress(task_id, 5, "文件上传完成，开始后台处理...")

        # 添加后台任务
        # 注意：process_combine_audio 现在是同步函数，BackgroundTasks 会自动在线程池中运行它
        background_tasks.add_task(
            process_combine_audio,
            task_id=task_id,
            metronome_path=metronome_path,
            music_paths=music_paths,
            target_bpm=target_bpm,
            output_format=output_format,
            auto_extract_metronome=auto_extract_metronome,
            metronome_volume=metronome_volume,
            max_concurrent=max_concurrent
        )

        return {
            "success": True,
            "task_id": task_id,
            "message": "任务已创建，正在后台处理..."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Combine endpoint error: {e}", exc_info=True)
        if task_id:
            progress_service.fail_task(task_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Extract metronome (background worker)
# ---------------------------------------------------------------------------
def process_extract_metronome(task_id: str, music_path: Path, output_path: Path, output_format: str, output_filename: str):
    """后台处理节拍器提取任务"""
    try:
        def progress_callback(progress: int, message: str):
            progress_service.update_progress(task_id, progress, message)

        audio_service.extract_metronome(
            music_path=str(music_path),
            output_path=str(output_path),
            output_format=output_format,
            progress_callback=progress_callback
        )

        progress_service.complete_task(task_id, {
            "download_url": f"/api/download/{output_filename}",
            "filename": output_filename
        })
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}", exc_info=True)
        progress_service.fail_task(task_id, str(e))


@app.post("/api/extract")
@limiter.limit("10/minute")
async def extract_metronome(
    request: Request,
    background_tasks: BackgroundTasks,
    music: UploadFile = File(...),
    output_format: str = Form("mp3"),
    task_id: Optional[str] = Form(None)
):
    """
    从音乐中提取节拍器
    - music: 带有节拍器的音乐文件
    - output_format: 输出格式（默认 mp3）
    - task_id: 可选的任务ID，用于进度跟踪
    """
    try:
        # 创建任务ID
        if not task_id:
            task_id = progress_service.create_task()
        else:
            progress_service.create_task(task_id)

        logger.info(f"New extract task: {task_id}")

        music_id = str(uuid.uuid4())
        music_path = UPLOAD_DIR / f"{music_id}_{sanitize_filename(music.filename)}"

        progress_service.update_progress(task_id, 5, "上传文件中...")

        with open(music_path, "wb") as f:
            content = await music.read()
            f.write(content)

        # Validate file size
        if music_path.stat().st_size > MAX_FILE_SIZE:
            music_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=f"文件过大，最大允许 {MAX_FILE_SIZE // (1024*1024)}MB")

        # 检测源格式并验证输出格式
        source_format = format_service.detect_format(str(music_path)) or "mp3"
        if not format_service.can_convert(source_format, output_format):
            progress_service.fail_task(task_id, f"无法从 {source_format} 转换为 {output_format}")
            raise HTTPException(
                status_code=400,
                detail=f"无法从 {source_format} 转换为 {output_format}。只能降级或同级转换。"
            )

        output_filename = f"metronome_{uuid.uuid4()}.{output_format}"
        output_path = OUTPUT_DIR / output_filename

        # 添加后台任务
        background_tasks.add_task(
            process_extract_metronome,
            task_id,
            music_path,
            output_path,
            output_format,
            output_filename
        )

        return {
            "success": True,
            "task_id": task_id,
            "message": "任务已提交后台处理"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Extract endpoint error: {e}", exc_info=True)
        if task_id:
            progress_service.fail_task(task_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/extract-batch")
@limiter.limit("5/minute")
async def extract_metronome_batch(
    background_tasks: BackgroundTasks,
    request: Request,
    music_files: List[UploadFile] = File(...),
    output_format: str = Form("mp3"),
    task_id: Optional[str] = Form(None)
):
    """批量提取节拍器"""
    try:
        if not task_id:
            task_id = progress_service.create_task()
        else:
            progress_service.create_task(task_id)

        music_paths = []
        for idx, music_file in enumerate(music_files):
            music_id = str(uuid.uuid4())
            music_path = UPLOAD_DIR / f"{music_id}_{sanitize_filename(music_file.filename)}"
            content = await music_file.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail=f"文件 {music_file.filename} 太大")
            with open(music_path, "wb") as f:
                f.write(content)
            music_paths.append(str(music_path))

        background_tasks.add_task(
            process_extract_batch,
            task_id, music_paths, output_format
        )

        return {"success": True, "task_id": task_id, "message": "批量提取任务已提交"}
    except HTTPException:
        raise
    except Exception as e:
        if task_id:
            progress_service.fail_task(task_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


def process_extract_batch(task_id: str, music_paths: List[str], output_format: str):
    """后台批量提取节拍器"""
    try:
        output_files = []
        total = len(music_paths)
        for idx, music_path in enumerate(music_paths):
            if progress_service.is_cancelled(task_id):
                return
            progress_service.update_progress(
                task_id,
                int((idx / total) * 90),
                f"正在提取 {idx + 1}/{total}..."
            )
            original_name = Path(music_path).stem[37:]  # Remove UUID prefix
            output_filename = f"metronome_{original_name}.{output_format}"
            output_path = OUTPUT_DIR / output_filename

            def progress_callback(progress: int, message: str):
                base = int((idx / total) * 90)
                mapped = base + int((progress / 100) * (90 / total))
                progress_service.update_progress(task_id, mapped, f"文件 {idx+1}/{total}: {message}")

            audio_service.extract_metronome(
                music_path=music_path,
                output_path=str(output_path),
                output_format=output_format,
                progress_callback=progress_callback
            )
            output_files.append({
                "download_url": f"/api/download/{output_filename}",
                "filename": output_filename
            })

        progress_service.complete_task(task_id, {
            "files": output_files,
            "count": len(output_files)
        })
    except Exception as e:
        logger.error(f"Batch extract failed: {e}", exc_info=True)
        progress_service.fail_task(task_id, str(e))


# ---------------------------------------------------------------------------
# Concatenate audio (background worker)
# ---------------------------------------------------------------------------
def process_concatenate_audio(task_id: str, music_paths: List[str], target_duration: float, output_path: Path, output_format: str, output_filename: str, crossfade_ms: int = 0):
    """后台处理音频拼接任务"""
    try:
        def progress_callback(progress: int, message: str):
            progress_service.update_progress(task_id, progress, message)

        audio_service.concatenate_audio(
            music_paths=music_paths,
            target_duration=target_duration,
            output_path=str(output_path),
            output_format=output_format,
            crossfade_ms=crossfade_ms,
            progress_callback=progress_callback
        )

        progress_service.complete_task(task_id, {
            "download_url": f"/api/download/{output_filename}",
            "filename": output_filename
        })
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}", exc_info=True)
        progress_service.fail_task(task_id, str(e))


@app.post("/api/concatenate")
@limiter.limit("10/minute")
async def concatenate_audio(
    request: Request,
    background_tasks: BackgroundTasks,
    music_files: List[UploadFile] = File(...),
    target_duration: float = Form(...),
    output_format: str = Form("mp3"),
    crossfade_ms: int = Form(0),  # 淡入淡出时长(毫秒), 0-10000
    task_id: Optional[str] = Form(None)
):
    """
    拼接多个音乐文件
    - music_files: 多个音乐文件
    - target_duration: 目标总时长（秒）
    - output_format: 输出格式（默认 mp3）
    - crossfade_ms: 淡入淡出时长（毫秒），0-10000
    - task_id: 可选的任务ID，用于进度跟踪
    """
    try:
        # Parameter validation
        if not 60 <= target_duration <= 7200:
            raise HTTPException(status_code=400, detail="时长必须在 60-7200 秒之间")
        crossfade_ms = max(0, min(10000, crossfade_ms))

        # 创建任务ID
        if not task_id:
            task_id = progress_service.create_task()
        else:
            progress_service.create_task(task_id)

        logger.info(f"New concatenate task: {task_id}, {len(music_files)} files, {target_duration}s")

        music_paths = []
        source_formats = []

        progress_service.update_progress(task_id, 5, "上传文件中...")

        for idx, music_file in enumerate(music_files):
            music_id = str(uuid.uuid4())
            music_path = UPLOAD_DIR / f"{music_id}_{sanitize_filename(music_file.filename)}"

            with open(music_path, "wb") as f:
                content = await music_file.read()
                f.write(content)

            # Validate file size
            if music_path.stat().st_size > MAX_FILE_SIZE:
                music_path.unlink(missing_ok=True)
                raise HTTPException(status_code=400, detail=f"文件 {music_file.filename} 过大，最大允许 {MAX_FILE_SIZE // (1024*1024)}MB")

            music_paths.append(str(music_path))
            source_format = format_service.detect_format(str(music_path)) or "mp3"
            source_formats.append(source_format)

        # 使用最高质量的源格式作为基准
        max_quality_format = max(source_formats, key=lambda f: format_service.get_format_quality(f))

        # 验证输出格式
        if not format_service.can_convert(max_quality_format, output_format):
            progress_service.fail_task(task_id, f"无法从 {max_quality_format} 转换为 {output_format}")
            raise HTTPException(
                status_code=400,
                detail=f"无法从 {max_quality_format} 转换为 {output_format}。只能降级或同级转换。"
            )

        output_filename = f"concatenated_{uuid.uuid4()}.{output_format}"
        output_path = OUTPUT_DIR / output_filename

        # 添加后台任务
        background_tasks.add_task(
            process_concatenate_audio,
            task_id,
            music_paths,
            target_duration,
            output_path,
            output_format,
            output_filename,
            crossfade_ms
        )

        return {
            "success": True,
            "task_id": task_id,
            "message": "任务已提交后台处理"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Concatenate endpoint error: {e}", exc_info=True)
        if task_id:
            progress_service.fail_task(task_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Progress & WebSocket
# ---------------------------------------------------------------------------
@app.get("/api/progress/{task_id}")
async def get_progress(task_id: str):
    """获取任务进度"""
    progress = progress_service.get_progress(task_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Task not found")
    return progress


@app.websocket("/ws/progress/{task_id}")
async def websocket_progress(websocket: WebSocket, task_id: str):
    """WebSocket 进度更新"""
    await websocket.accept()
    try:
        while True:
            progress = progress_service.get_progress(task_id)
            if not progress:
                await websocket.send_json({"error": "Task not found"})
                break

            await websocket.send_json(progress)

            if progress['status'] in ['completed', 'failed']:
                break

            await asyncio.sleep(0.5)  # 每0.5秒更新一次
    except WebSocketDisconnect:
        pass


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------
@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """下载处理后的音频文件"""
    file_path = (OUTPUT_DIR / filename).resolve()
    # Path traversal protection
    if not str(file_path).startswith(str(OUTPUT_DIR.resolve())):
        raise HTTPException(status_code=400, detail="无效的文件名")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件未找到")

    # 检测格式
    format_name = os.path.splitext(filename)[1].lstrip('.')
    mime_type = format_service.get_format_mime_type(format_name)

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=mime_type
    )


class BatchDownloadRequest(BaseModel):
    filenames: List[str]


@app.post("/api/batch-download")
async def batch_download(request: BatchDownloadRequest):
    """
    批量下载文件（返回 ZIP 压缩包）
    - filenames: 文件名列表（数组）
    """
    try:
        # 创建临时 ZIP 文件
        zip_filename = f"batch_{uuid.uuid4()}.zip"
        zip_path = OUTPUT_DIR / zip_filename

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename in request.filenames:
                file_path = (OUTPUT_DIR / filename).resolve()
                # Path traversal protection
                if not str(file_path).startswith(str(OUTPUT_DIR.resolve())):
                    continue
                if file_path.exists():
                    zipf.write(file_path, filename)

        return FileResponse(
            path=str(zip_path),
            filename=zip_filename,
            media_type="application/zip"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
