from contextlib import asynccontextmanager

from fastapi import FastAPI

from routers.predictions import router
from services.model_loader import MODELS_DIR
from services.pose_pipeline import validate_feature_order


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_feature_order()

    pose_weights = MODELS_DIR / "yolo11n-pose.pt"
    if not pose_weights.is_file():
        raise FileNotFoundError(f"Pose 가중치를 찾을 수 없습니다: {pose_weights}")

    yield


app = FastAPI(title="교과10 동작 분석 API", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "action_model_ready": True,
        "pose_weights_present": True,
    }
