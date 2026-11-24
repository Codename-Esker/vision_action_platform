from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class AnalysisJob(models.Model):
    class InputType(models.TextChoices):
        UPLOAD = "upload", "영상 업로드"
        CAMERA = "camera", "IP Webcam"

    class Status(models.TextChoices):
        PENDING = "PENDING", "대기"
        STARTED = "STARTED", "처리 중"
        SUCCESS = "SUCCESS", "완료"
        FAILURE = "FAILURE", "실패"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="analysis_jobs",
        verbose_name="요청 사용자",
    )
    input_type = models.CharField("입력 방식", max_length=10, choices=InputType.choices)
    video = models.FileField("영상 파일", upload_to="analyses/%Y/%m/%d/", blank=True)
    camera_id = models.CharField("카메라 식별자", max_length=64, blank=True)

    status = models.CharField(
        "처리 상태",
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    memo = models.TextField("분석 메모", blank=True, default="")
    task_id = models.CharField("Celery 작업 ID", max_length=255, blank=True)
    error_message = models.TextField("오류 내용", blank=True)
    processing_seconds = models.FloatField("추론 처리 시간(초)", null=True, blank=True)
    created_at = models.DateTimeField("요청 시각", auto_now_add=True)
    finished_at = models.DateTimeField("종료 시각", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "분석 작업"
        verbose_name_plural = "분석 작업"

    def __str__(self):
        return f"작업 {self.pk} · {self.get_status_display()}"


class PersonPrediction(models.Model):
    job = models.ForeignKey(
        AnalysisJob,
        on_delete=models.CASCADE,
        related_name="predictions",
        verbose_name="분석 작업",
    )
    track_id = models.PositiveIntegerField("추적 ID")
    action_label = models.CharField("예측 동작", max_length=40)
    confidence = models.FloatField(
        "신뢰도",
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    created_at = models.DateTimeField("결과 저장 시각", auto_now_add=True)

    class Meta:
        ordering = ["job_id", "track_id"]
        verbose_name = "사람별 예측"
        verbose_name_plural = "사람별 예측"
        constraints = [
            models.UniqueConstraint(
                fields=["job", "track_id"],
                name="unique_track_per_analysis_job",
            ),
            models.CheckConstraint(
                condition=models.Q(confidence__gte=0.0, confidence__lte=1.0),
                name="prediction_confidence_between_0_and_1",
            ),
        ]

    def __str__(self):
        return f"작업 {self.job_id} · 추적 {self.track_id} · {self.action_label}"
