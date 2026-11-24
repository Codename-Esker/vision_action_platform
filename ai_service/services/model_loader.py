import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestClassifier


# 이 파일의 위치를 기준으로 ai_service/models 폴더를 찾습니다.
MODELS_DIR = Path(__file__).resolve().parents[1] / "models"


@dataclass
class ActionModel:
    model: RandomForestClassifier
    feature_columns: list[str]
    classes: list[str]
    sequence_steps: int
    min_valid_frames: int


@lru_cache(maxsize=1)
def load_action_model() -> ActionModel:
    """교과10 모델과 학습 설정을 읽고, 검증한 결과를 재사용합니다."""
    model = joblib.load(MODELS_DIR / "rf_action_baseline.joblib")

    with (MODELS_DIR / "rf_feature_columns.json").open(encoding="utf-8") as file:
        feature_columns = json.load(file)

    with (MODELS_DIR / "rf_training_info.json").open(encoding="utf-8") as file:
        training_info = json.load(file)

    if not isinstance(model, RandomForestClassifier):
        raise ValueError("학습 모델의 종류가 RandomForestClassifier와 다릅니다.")

    sequence_steps = training_info["sequence_steps"]
    min_valid_frames = training_info["min_valid_frames"]

    if sequence_steps != 30:
        raise ValueError("교과10 모델의 시퀀스 길이는 30이어야 합니다.")

    if not 1 <= min_valid_frames <= sequence_steps:
        raise ValueError("최소 유효 프레임 수가 시퀀스 길이 범위를 벗어났습니다.")

    # 한 시점의 특징 38개 × 30개 시점 = 모델 입력 1,140개
    expected_count = sequence_steps * 38

    if not (
        model.n_features_in_ == training_info["feature_count"] == expected_count
    ):
        raise ValueError("모델 입력 차원과 학습 정보의 특징 수가 일치하지 않습니다.")

    if not isinstance(feature_columns, list) or len(feature_columns) != expected_count:
        raise ValueError("특징 이름 파일에 1,140개의 이름이 필요합니다.")

    if not all(isinstance(name, str) and name for name in feature_columns):
        raise ValueError("특징 이름에 비어 있거나 문자열이 아닌 값이 있습니다.")

    if len(set(feature_columns)) != expected_count:
        raise ValueError("특징 이름 파일에 중복된 이름이 있습니다.")

    # 모델에도 학습 당시 열 이름이 저장되어 있으면 순서까지 대조합니다.
    if hasattr(model, "feature_names_in_"):
        if model.feature_names_in_.tolist() != feature_columns:
            raise ValueError("모델과 JSON의 특징 이름 또는 순서가 다릅니다.")

    # 이후 predict_proba()의 각 열을 해석할 때 모델의 클래스 순서를 사용합니다.
    classes = model.classes_.tolist()
    if len(classes) != 6 or sorted(classes) != sorted(training_info["classes"]):
        raise ValueError("모델의 동작 클래스와 학습 정보가 일치하지 않습니다.")

    return ActionModel(
        model=model,
        feature_columns=feature_columns,
        classes=classes,
        sequence_steps=sequence_steps,
        min_valid_frames=min_valid_frames,
    )