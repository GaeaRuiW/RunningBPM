from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import os
import uuid
import zipfile
import asyncio
import aiofiles
from typing import List, Optional
from pathlib import Path
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
import shutil
from fastapi.concurrency import run_in_threadpool
from services.audio_service import AudioService
from services.format_service import FormatService
from services.progress_service import progress_service

app = FastAPI(title="RunningBPM API", version="1.0.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React 开发服务器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保上传和输出目录存在
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

audio_service = AudioService()
format_service = FormatService()


@app.get("/")
async def root():
    return {"message": "RunningBPM API is running"}


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


def process_combine_audio(
    task_id: str,
    metronome_path: Path,
    music_paths: List[str],
    target_bpm: int,
    output_format: str,
    auto_extract_metronome: bool,
    metronome_volume: int = 0
):
    """后台处理音频合成"""
    try:
        progress_service.update_progress(task_id, 5, "文件上传完成，开始处理...")
        
        # 如果需要自动提取节拍器
        # if auto_extract_metronome:
        #     progress_service.update_progress(task_id, 6, "准备提取节拍器...")
        #     metronome_id = metronome_path.stem.split('_')[0]
        #     extracted_metronome_path = UPLOAD_DIR / f"extracted_{metronome_id}.{output_format}"
            
        #     progress_service.update_progress(task_id, 7, "从上传文件中提取节拍器...")
            
        #     def extract_progress_callback(progress: int, message: str):
        #         # 提取进度映射到 7-18%
        #         mapped_progress = 7 + int(progress * 0.11)
        #         progress_service.update_progress(task_id, mapped_progress, f"提取节拍器: {message}")
            
        #     audio_service.extract_metronome(
        #         music_path=str(metronome_path),
        #         output_path=str(extracted_metronome_path),
        #         output_format=output_format,
        #         progress_callback=extract_progress_callback
        #     )
        #     metronome_path = extracted_metronome_path
        #     progress_service.update_progress(task_id, 19, "节拍器提取完成")
        
        # 检测源格式
        progress_service.update_progress(task_id, 20 if auto_extract_metronome else 6, "检测音频文件格式...")
        source_formats = []
        total_files = len(music_paths)
        
        for idx, music_path in enumerate(music_paths):
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
        
        # 使用线程池并行处理多个文件
        # 限制最大线程数，避免资源耗尽
        max_workers = min(total_files, multiprocessing.cpu_count(), 4)  # 最多4个线程
        
        def process_single_file(args):
            """处理单个文件的函数，用于并行执行"""
            idx, music_path, metronome_path_str, target_bpm, output_format, task_id, base_progress, total = args
            
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
                audio_service = AudioService()
                audio_service.combine_audio(
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
        
        # 使用线程池并行执行
        completed_count = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_task = {executor.submit(process_single_file, task): task for task in tasks}
            
            # 收集结果
            results = {}
            for future in as_completed(future_to_task):
                completed_count += 1
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
                    task = future_to_task[future]
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
        progress_service.fail_task(task_id, str(e))


@app.post("/api/combine")
async def combine_audio(
    background_tasks: BackgroundTasks,
    metronome: UploadFile = File(...),
    music_files: List[UploadFile] = File(...),
    target_bpm: int = Form(...),
    output_format: str = Form("mp3"),
    auto_extract_metronome: bool = Form(False),
    metronome_volume: int = Form(0),  # 节拍器音量调整 (dB), 默认0, 范围-20到+20
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
        # 创建任务ID
        if not task_id:
            task_id = progress_service.create_task()
        else:
            progress_service.create_task(task_id)
        
        progress_service.update_progress(task_id, 2, "接收文件上传...")
        
        # 准备文件路径
        metronome_id = str(uuid.uuid4())
        metronome_path = UPLOAD_DIR / f"{metronome_id}_{metronome.filename}"
        
        # 立即保存文件 (使用线程池避免阻塞主循环)
        progress_service.update_progress(task_id, 3, "保存节拍器文件...")
        
        def save_file_sync(upload_file, destination):
            with open(destination, "wb") as buffer:
                shutil.copyfileobj(upload_file.file, buffer)
                
        await run_in_threadpool(save_file_sync, metronome, metronome_path)
        
        # 保存音乐文件
        music_paths = []
        total_files = len(music_files)
        progress_service.update_progress(task_id, 4, f"准备保存 {total_files} 个音乐文件...")
        
        for idx, music_file in enumerate(music_files):
            music_id = str(uuid.uuid4())
            music_path = UPLOAD_DIR / f"{music_id}_{music_file.filename}"
            
            progress_service.update_progress(
                task_id, 
                4 + int((idx / total_files) * 1), 
                f"保存音乐文件 {idx + 1}/{total_files}: {music_file.filename}"
            )
            
            await run_in_threadpool(save_file_sync, music_file, music_path)
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
            metronome_volume=metronome_volume
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "任务已创建，正在后台处理..."
        }
    except Exception as e:
        if task_id:
            progress_service.fail_task(task_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


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
        progress_service.fail_task(task_id, str(e))

@app.post("/api/extract")
async def extract_metronome(
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
        
        music_id = str(uuid.uuid4())
        music_path = UPLOAD_DIR / f"{music_id}_{music.filename}"
        
        progress_service.update_progress(task_id, 5, "上传文件中...")
        
        with open(music_path, "wb") as f:
            content = await music.read()
            f.write(content)
        
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
    except Exception as e:
        if task_id:
            progress_service.fail_task(task_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


def process_concatenate_audio(task_id: str, music_paths: List[str], target_duration: float, output_path: Path, output_format: str, output_filename: str):
    """后台处理音频拼接任务"""
    try:
        def progress_callback(progress: int, message: str):
            progress_service.update_progress(task_id, progress, message)
        
        audio_service.concatenate_audio(
            music_paths=music_paths,
            target_duration=target_duration,
            output_path=str(output_path),
            output_format=output_format,
            progress_callback=progress_callback
        )
        
        progress_service.complete_task(task_id, {
            "download_url": f"/api/download/{output_filename}",
            "filename": output_filename
        })
    except Exception as e:
        progress_service.fail_task(task_id, str(e))

@app.post("/api/concatenate")
async def concatenate_audio(
    background_tasks: BackgroundTasks,
    music_files: List[UploadFile] = File(...),
    target_duration: float = Form(...),
    output_format: str = Form("mp3"),
    task_id: Optional[str] = Form(None)
):
    """
    拼接多个音乐文件
    - music_files: 多个音乐文件
    - target_duration: 目标总时长（秒）
    - output_format: 输出格式（默认 mp3）
    - task_id: 可选的任务ID，用于进度跟踪
    """
    try:
        # 创建任务ID
        if not task_id:
            task_id = progress_service.create_task()
        else:
            progress_service.create_task(task_id)
        
        music_paths = []
        source_formats = []
        
        progress_service.update_progress(task_id, 5, "上传文件中...")
        
        for idx, music_file in enumerate(music_files):
            music_id = str(uuid.uuid4())
            music_path = UPLOAD_DIR / f"{music_id}_{music_file.filename}"
            
            with open(music_path, "wb") as f:
                content = await music_file.read()
                f.write(content)
            
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
            output_filename
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "任务已提交后台处理"
        }
    except Exception as e:
        if task_id:
            progress_service.fail_task(task_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


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


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """下载处理后的音频文件"""
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
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
                file_path = OUTPUT_DIR / filename
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
