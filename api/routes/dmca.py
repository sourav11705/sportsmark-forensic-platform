from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from fastapi.concurrency import run_in_threadpool
from datetime import datetime, timezone
import os

from api.schemas import DmcaGenerateRequest, DmcaGenerateResponse
from watermark.dmca import generate_dmca
from watermark.registry import get_asset, lookup_session
from api.routes.detect import list_detections

router = APIRouter()

@router.post("/generate", response_model=DmcaGenerateResponse)
async def api_dmca_generate(request: DmcaGenerateRequest):
    detections = list_detections()
    detection = next((d for d in detections if d.get("detection_id") == request.detection_id), None)
    
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
        
    asset = get_asset(detection.get("asset_id"))
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    session_id = detection.get("session_data", {}).get("session_id")
    session = lookup_session(session_id) if session_id else None
    
    notice_text = await run_in_threadpool(
        generate_dmca,
        detection,
        asset,
        session,
        request.organization,
        request.contact_email,
        request.address,
        request.signatory
    )
    
    return DmcaGenerateResponse(
        detection_id=request.detection_id,
        notice_text=notice_text,
        generated_at=datetime.now(timezone.utc).isoformat()
    )

@router.get("/download/{detection_id}")
async def api_dmca_download_pdf(detection_id: str):
    request = DmcaGenerateRequest(
        detection_id=detection_id,
        organization='SportsMark Global',
        contact_email='legal@sportsmark.com',
        address='123 IP Lane, Tech City',
        signatory='Chief Legal Officer'
    )
    response = await api_dmca_generate(request)
    
    filename = f"dmca_{detection_id}.pdf"
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(0, 5, txt=response.notice_text.encode('latin-1', 'replace').decode('latin-1'))
        pdf.output(filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF file: {e}")
        
    return FileResponse(filename, media_type="application/pdf", filename=filename)
