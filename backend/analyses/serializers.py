from pathlib import Path

from django.conf import settings
from rest_framework import serializers

from .models import AnalysisJob, PersonPrediction


class PersonPredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonPrediction
        fields = ("track_id", "action_label", "confidence")


class AnalysisJobSerializer(serializers.ModelSerializer):
    input_type = serializers.ChoiceField(
        choices=AnalysisJob.InputType.choices,
        default=AnalysisJob.InputType.UPLOAD,
    )
    video = serializers.FileField(write_only=True, required=False)
    camera_id = serializers.CharField(required=False, allow_blank=True)
    predictions = PersonPredictionSerializer(many=True, read_only=True)

    class Meta:
        model = AnalysisJob
        fields = (
            "id", "memo", "input_type", "video", "camera_id", "status", "created_at",
            "finished_at", "processing_seconds", "error_message", "predictions",
        )
        read_only_fields = (
            "id", "memo", "status", "created_at", "finished_at",
            "processing_seconds", "error_message",
        )

    def validate_video(self, video):
        if Path(video.name).suffix.lower() != ".mp4":
            raise serializers.ValidationError("MP4 파일을 선택해 주세요.")
        return video

    def validate(self, attrs):
        video = attrs.get("video")
        camera_id = attrs.get("camera_id", "")

        if attrs["input_type"] == AnalysisJob.InputType.UPLOAD:
            if not video:
                raise serializers.ValidationError({"video": "MP4 파일을 선택해 주세요."})
            if camera_id:
                raise serializers.ValidationError({"camera_id": "업로드 시에는 비워 두세요."})
        else:
            if camera_id not in settings.CAMERA_SOURCES:
                raise serializers.ValidationError({"camera_id": "등록된 카메라 ID를 입력해 주세요."})
            if video:
                raise serializers.ValidationError({"video": "카메라 촬영 시에는 파일을 비워 두세요."})

        return attrs


class AnalysisMemoSerializer(serializers.Serializer):
    memo = serializers.CharField(allow_blank=True)

    def validate(self, attrs):
        if set(self.initial_data) != {"memo"}:
            raise serializers.ValidationError("수정할 수 있는 항목은 memo 하나입니다.")
        return attrs
