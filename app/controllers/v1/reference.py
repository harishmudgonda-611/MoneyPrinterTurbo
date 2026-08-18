from fastapi import File, HTTPException, UploadFile

from app.controllers.v1.base import new_router
from app.models.reference_video import ReferenceVideoAnalysis
from app.services.reference_video import analyze_reference_video, save_reference_upload

router = new_router()


@router.post(
    "/reference-videos/analyze",
    response_model=ReferenceVideoAnalysis,
    summary="Analyze and retain a reference Reel for generation",
)
def analyze_reference_video_upload(file: UploadFile = File(...)):
    try:
        reference_id, path = save_reference_upload(file.file, file.filename or "reference.mp4")
        return analyze_reference_video(path, reference_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to analyze reference video") from exc
