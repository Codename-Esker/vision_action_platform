from pathlib import Path

import numpy as np

from services.model_loader import load_action_model
from services.pose_pipeline import extract_person_sequences


def predict_video(video_path: str | Path) -> dict:
    """영상에서 추적한 사람별로 동작 이름과 모델의 예측 확률을 반환합니다."""
    sequences = extract_person_sequences(video_path)

    if not sequences:
        return {
            "predictions": [],
            "message": "분석에 필요한 유효 프레임을 확보한 추적 ID가 없습니다.",
        }

    action = load_action_model()
    track_ids = sorted(sequences)

    # 한 행이 한 사람의 특징 1,140개입니다.
    features = np.stack([sequences[track_id] for track_id in track_ids])
    probabilities = action.model.predict_proba(features)

    predictions = []
    for track_id, scores in zip(track_ids, probabilities):
        best_index = int(np.argmax(scores))
        predictions.append({
            "track_id": track_id,
            "action_label": action.classes[best_index],
            "confidence": float(scores[best_index]),
        })

    return {"predictions": predictions}
