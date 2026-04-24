from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.concurrency import run_in_threadpool
import tempfile
import os
from typing import List, Optional

from api.schemas import DetectFingerprintResponse, DetectWatermarkResponse, DetectFullResponse
from watermark.fingerprint import VideoFingerprinter
from watermark.embedder import VideoWatermarker
from watermark.registry import get_asset, lookup_session, log_detection, _load, _DETECTIONS_FILE

router = APIRouter()

# Implement list_detections since it wasn't in registry.py explicitly
def list_detections(asset_id: Optional[str] = None) -> list:
    detections = _load(_DETECTIONS_FILE)
    if asset_id:
        return [d for d in detections if d.get("asset_id") == asset_id]
    return detections

@router.post("/fingerprint", response_model=DetectFingerprintResponse)
async def api_detect_fingerprint(asset_id: str = Form(...), file: UploadFile = File(...)):
    asset = get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    try:
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
        
        fp = VideoFingerprinter()
        uploaded_fp = await run_in_threadpool(fp.fingerprint, temp_file.name)
        
        original_fp = asset.get("fingerprint")
        result = await run_in_threadpool(fp.compare, original_fp, uploaded_fp)
        
        return DetectFingerprintResponse(
            is_match=result["is_match"],
            similarity=result["similarity"],
            matched_frames=result["matched_frames"],
            total_frames_checked=len(uploaded_fp.get("frame_hashes", [])),
            verdict=result["verdict"],
            asset_id=asset_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

@router.post("/watermark", response_model=DetectWatermarkResponse)
async def api_detect_watermark(file: UploadFile = File(...)):
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    try:
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
        
        embedder = VideoWatermarker()
        result = await run_in_threadpool(embedder.extract, temp_file.name, 160)
        
        session_record = None
        if result.get("session_id"):
            session_record = lookup_session(result["session_id"])
            
        return DetectWatermarkResponse(
            session_id=result.get("session_id"),
            platform_code=result.get("platform_code"),
            confidence=result.get("confidence", 0.0),
            raw_tag=result.get("raw_tag"),
            session_record=session_record
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

@router.post("/full", response_model=DetectFullResponse)
async def api_detect_full(asset_id: str = Form(None), file: UploadFile = File(...)):
    from watermark.registry import list_assets
    assets = list_assets()
    if not assets:
        raise HTTPException(status_code=400, detail="No registered assets to scan against")
        
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    try:
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
        
        # 1. Fingerprint
        fp = VideoFingerprinter()
        uploaded_fp = await run_in_threadpool(fp.fingerprint, temp_file.name)
        
        best_match = None
        best_asset_id = None
        best_similarity = -1.0
        
        for asset in assets:
            original_fp = asset.get("fingerprint")
            if not original_fp:
                continue
            fp_result = await run_in_threadpool(fp.compare, original_fp, uploaded_fp)
            if fp_result["similarity"] > best_similarity:
                best_similarity = fp_result["similarity"]
                best_match = fp_result
                best_asset_id = asset["asset_id"]
                
        if not best_match:
            best_match = {
                "is_match": False, "similarity": 0.0, 
                "matched_frames": 0, "verdict": "NO MATCH - content differs significantly"
            }
            best_asset_id = asset_id or "unknown"
        elif best_match["similarity"] >= 0.98:
            # Almost identical means this is the original authorized clean copy, not a pirated distributed stream
            best_match["is_match"] = False
            best_match["verdict"] = "AUTHORIZED COPY (ORIGINAL) - Clean file"
            
        fp_response = DetectFingerprintResponse(
            is_match=best_match["is_match"],
            similarity=best_match["similarity"],
            matched_frames=best_match["matched_frames"],
            total_frames_checked=len(uploaded_fp.get("frame_hashes", [])),
            verdict=best_match["verdict"],
            asset_id=best_asset_id
        )
        
        # 2. Watermark
        embedder = VideoWatermarker()
        wm_result = await run_in_threadpool(embedder.extract, temp_file.name, 160)
        
        session_record = None
        if wm_result.get("session_id"):
            session_record = lookup_session(wm_result["session_id"])
            
        wm_response = DetectWatermarkResponse(
            session_id=wm_result.get("session_id"),
            platform_code=wm_result.get("platform_code"),
            confidence=wm_result.get("confidence", 0.0),
            raw_tag=wm_result.get("raw_tag"),
            session_record=session_record
        )
        
        # 3. Log detection if match
        detection_id = None
        if best_match["is_match"]:
            platform = session_record.get("platform", "Unknown") if session_record else "Unknown"
            detection = log_detection(
                asset_id=best_asset_id,
                source_url="Uploaded via API",
                platform=platform,
                session_data=session_record or {},
                fingerprint_match=best_match
            )
            detection_id = detection["detection_id"]
            
        return DetectFullResponse(
            fingerprint=fp_response,
            watermark=wm_response,
            detection_logged=best_match["is_match"],
            detection_id=detection_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

@router.get("/detections", response_model=List[dict])
async def api_list_detections(asset_id: Optional[str] = None):
    return list_detections(asset_id)
