from pydantic import BaseModel
from typing import List, Optional, Any, Dict

class AssetRegisterResponse(BaseModel):
    asset_id: str
    title: str
    master_hash: str
    resolution: str
    duration: float
    fps: float
    frame_count: int
    registered_at: str

class WatermarkRequest(BaseModel):
    asset_id: str
    user_id: str
    platform: str

class WatermarkResponse(BaseModel):
    session_id: str
    user_id: str
    platform: str
    full_tag: str
    wm_length: int
    output_path: str
    distributed_at: str

class DetectFingerprintResponse(BaseModel):
    is_match: bool
    similarity: float
    matched_frames: int
    total_frames_checked: int
    verdict: str
    asset_id: str

class DetectWatermarkResponse(BaseModel):
    session_id: Optional[str]
    platform_code: Optional[str]
    confidence: float
    raw_tag: Optional[str]
    session_record: Optional[Dict[str, Any]]

class DetectFullResponse(BaseModel):
    fingerprint: DetectFingerprintResponse
    watermark: DetectWatermarkResponse
    detection_logged: bool
    detection_id: Optional[str]

class DmcaGenerateRequest(BaseModel):
    detection_id: str
    organization: str
    contact_email: str
    address: str
    signatory: str

class DmcaGenerateResponse(BaseModel):
    detection_id: str
    notice_text: str
    generated_at: str

class StatsResponse(BaseModel):
    total_assets: int
    total_sessions: int
    total_detections: int
    flagged: int
    platforms_affected: List[str]
