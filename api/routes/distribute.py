from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from fastapi.concurrency import run_in_threadpool
from typing import List, Optional
import os

from api.schemas import WatermarkRequest, WatermarkResponse
from watermark.embedder import VideoWatermarker
from watermark.registry import get_asset, register_session, lookup_session, list_sessions

router = APIRouter()

@router.post("/watermark", response_model=WatermarkResponse)
async def api_watermark(request: WatermarkRequest):
    asset = get_asset(request.asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    original_path = asset.get("original_path")
    if not original_path or not os.path.exists(original_path):
        raise HTTPException(status_code=400, detail="Original asset file not found on disk")
        
    embedder = VideoWatermarker()
    
    # Generate session id to determine output path
    session_data = embedder.generate_session_id(request.user_id, request.platform)
    session_id = session_data["session_id"]
    output_path = f"wm_{request.user_id}_{session_id}.mp4"
    
    try:
        session = await run_in_threadpool(
            embedder.embed,
            original_path,
            request.user_id,
            request.platform,
            output_path,
            session_data
        )
        
        record = await run_in_threadpool(
            register_session, session, request.asset_id
        )
        
        # Add output_path to response manually since it's not in the base session dict
        return WatermarkResponse(
            session_id=record["session_id"],
            user_id=record["user_id"],
            platform=record["platform"],
            full_tag=record["full_tag"],
            wm_length=record["wm_length"],
            output_path=output_path,
            distributed_at=record["timestamp"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions", response_model=List[dict])
async def api_list_sessions(asset_id: Optional[str] = None):
    return list_sessions(asset_id)

@router.get("/sessions/{session_id}")
async def api_get_session(session_id: str):
    session = lookup_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.get("/watermark/download/{session_id}")
async def api_download_watermark(session_id: str):
    session = lookup_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    output_path = f"wm_{session['user_id']}_{session_id}.mp4"
    if not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="Watermarked video file not found")
        
    return FileResponse(output_path, media_type="video/mp4", filename=output_path)
