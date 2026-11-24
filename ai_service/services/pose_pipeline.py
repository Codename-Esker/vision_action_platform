from services.model_loader import load_action_model
from src.sequence_utils import sequence_feature_names


def validate_feature_order() -> None:
    """기존 전처리 코드의 특징 순서가 학습 당시 JSON과 일치하는지 확인합니다."""
    action = load_action_model()

    generated = list(sequence_feature_names(action.sequence_steps))
    expected = action.feature_columns

    if len(generated) != len(expected):
        raise ValueError(
            f"특징 개수가 다릅니다. 전처리 코드 {len(generated)}개, "
            f"학습 JSON {len(expected)}개"
        )

    for index, (actual_name, expected_name) in enumerate(zip(generated, expected)):
        if actual_name != expected_name:
            raise ValueError(
                f"{index + 1}번째 특징이 다릅니다. "
                f"전처리 코드={actual_name}, 학습 JSON={expected_name}"
            )

def extract_person_sequences(video_path):
    """영상에서 추적 ID별로 1,140개 특징을 추출합니다."""
    from collections import defaultdict
    from pathlib import Path

    from ultralytics import YOLO

    from services.model_loader import MODELS_DIR
    from src.realtime_utils import frame_feature_from_pose
    from src.sequence_utils import flatten_sequence, resample_sequence

    video_path = Path(video_path)
    if not video_path.is_file():
        raise FileNotFoundError(f"영상 파일을 찾을 수 없습니다: {video_path}")

    weights_path = MODELS_DIR / "yolo11n-pose.pt"
    if not weights_path.is_file():
        raise FileNotFoundError(f"Pose 가중치를 찾을 수 없습니다: {weights_path}")

    validate_feature_order()
    action = load_action_model()
    pose_model = YOLO(str(weights_path))
    frames_by_track = defaultdict(list)

    results = pose_model.track(
        source=str(video_path),
        stream=True,
        vid_stride=1,
        tracker="bytetrack.yaml",
        verbose=False,
    )

    for frame_index, result in enumerate(results):
        if result.boxes is None or result.boxes.id is None:
            continue
        if result.keypoints is None:
            continue

        track_ids = result.boxes.id.int().cpu().tolist()
        for person_index, track_id in enumerate(track_ids):
            person_result = result[person_index : person_index + 1]
            feature = frame_feature_from_pose(person_result)
            if feature is not None:
                frames_by_track[track_id].append((frame_index, feature))

    sequences = {}
    for track_id, observations in frames_by_track.items():
        if len(observations) < action.min_valid_frames:
            continue

        frame_ids, features = zip(*observations)
        sequence = resample_sequence(features, frame_ids, action.sequence_steps)
        vector = flatten_sequence(sequence)

        if vector.shape != (len(action.feature_columns),):
            raise ValueError(f"추적 ID {track_id}의 입력 크기 오류: {vector.shape}")

        sequences[track_id] = vector

    return sequences
