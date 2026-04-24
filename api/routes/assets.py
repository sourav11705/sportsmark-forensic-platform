from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.concurrency import run_in_threadpool
import os
import tempfile
import uuid
from typing import List

from api.schemas import AssetRegisterResponse, StatsResponse
from watermark.fingerprint import VideoFingerprinter
from watermark.registry import register_asset, get_asset, list_assets, get_stats

router = APIRouter()

@router.post("/register", response_model=AssetRegisterResponse)
async def api_register_asset(title: str = Form(...), file: UploadFile = File(...)):
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    try:
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
            
        fp = VideoFingerprinter()
        fingerprint = await run_in_threadpool(fp.fingerprint, temp_file.name)
        
        asset_id = "ASSET-" + uuid.uuid4().hex[:8].upper()
        # Not deleting the file here because register_asset stores original_path
        # and distribute/watermark uses it later.
        record = await run_in_threadpool(
            register_asset, asset_id, title, fingerprint, temp_file.name
        )
        
        return AssetRegisterResponse(
            asset_id=record["asset_id"],
            title=record["title"],
            master_hash=fingerprint["master_hash"],
            resolution=fingerprint["resolution"],
            duration=fingerprint["duration"],
            fps=fingerprint["fps"],
            frame_count=len(fingerprint.get("frame_hashes", [])),
            registered_at=record["registered_at"]
        )
    except Exception as e:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[dict])
async def api_list_assets():
    return list_assets()

@router.get("/stats", response_model=StatsResponse)
async def api_get_stats():
    stats = get_stats()
    return StatsResponse(**stats)

@router.get("/{asset_id}")
async def api_get_asset(asset_id: str):
    asset = get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset
