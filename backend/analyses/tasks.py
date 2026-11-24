import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from celery import shared_task
from django.core.files import File
from django.db import transaction
from django.utils import timezone

from .camera_capture import capture_camera_video
from .models import AnalysisJob, PersonPrediction
from .services import request_video_prediction

logger = logging.getLogger(__name__)


@shared_task
def run_analysis(job_id):
    # 같은 작업 메시지가 두 번 도착해도 대기 중인 작업 한 건만 시작합니다.
    started = AnalysisJob.objects.filter(
        pk=job_id,
        status=AnalysisJob.Status.PENDING,
    ).update(status=AnalysisJob.Status.STARTED)

    if not started:
        return

    try:
        job = AnalysisJob.objects.get(pk=job_id)
        if job.input_type == AnalysisJob.InputType.CAMERA:
            with TemporaryDirectory() as directory:
                path = Path(directory) / "camera.mp4"
                capture_camera_video(job.camera_id, path)
                with path.open("rb") as stream:
                    result = request_video_prediction(File(stream, name="camera.mp4"))
        else:
            result = request_video_prediction(job.video)

        predictions = [
            PersonPrediction(
                job=job,
                track_id=item["track_id"],
                action_label=item["action_label"],
                confidence=item["confidence"],
            )
            for item in result["predictions"]
        ]

        with transaction.atomic():
            PersonPrediction.objects.bulk_create(predictions)
            job.status = AnalysisJob.Status.SUCCESS
            job.processing_seconds = result["processing_seconds"]
            job.finished_at = timezone.now()
            job.save(update_fields=["status", "processing_seconds", "finished_at"])

    except Exception as exc:
        logger.exception("분석 작업 %s 처리 실패", job_id)
        AnalysisJob.objects.filter(pk=job_id).update(
            status=AnalysisJob.Status.FAILURE,
            error_message=str(exc),
            finished_at=timezone.now(),
        )
        raise
