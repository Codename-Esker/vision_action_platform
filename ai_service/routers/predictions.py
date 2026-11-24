from pathlib import Path
from shutil import copyfileobj
from tempfile import TemporaryDirectory
from time import perf_counter

import cv2
from fastapi import APIRouter, File, HTTPException, UploadFile

from services.action_inference import predict_video


router = APIRouter()


@router.post("/predict/video")
def predict_uploaded_video(file: UploadFile = File(...)):
    started_at = perf_counter()

    if Path(file.filename or "").suffix.lower() != ".mp4":
        raise HTTPException(status_code=415, detail="MP4 영상을 업로드해 주세요.")

    with TemporaryDirectory() as temp_dir:
        video_path = Path(temp_dir) / "input.mp4"

        with video_path.open("wb") as output:
            copyfileobj(file.file, output)

        capture = cv2.VideoCapture(str(video_path))
        try:
            readable, _ = capture.read()
        finally:
            capture.release()

        if not readable:
            raise HTTPException(
                status_code=422,
                detail="영상의 첫 프레임을 읽을 수 없습니다. 파일을 확인해 주세요.",
            )

        result = predict_video(video_path)

    result["processing_seconds"] = round(perf_counter() - started_at, 3)
    return result
