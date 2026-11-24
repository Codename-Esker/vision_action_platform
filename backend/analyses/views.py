from django.shortcuts import get_object_or_404
from uuid import uuid4

from django.db import transaction
from django.utils import timezone
from kombu.exceptions import OperationalError
from rest_framework import mixins, viewsets
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated

from .models import AnalysisJob
from rest_framework.response import Response
from .serializers import AnalysisJobSerializer, AnalysisMemoSerializer
from .tasks import run_analysis


class QueueUnavailable(APIException):
    status_code = 503
    default_detail = "분석 작업을 대기열에 등록하지 못했습니다."


class AnalysisJobViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = AnalysisJobSerializer

    def get_queryset(self):
        return (
            AnalysisJob.objects
            .filter(user=self.request.user)
            .prefetch_related("predictions")
            .order_by("-created_at", "-id")
        )

    def destroy(self, request, *args, **kwargs):
        with transaction.atomic():
            # 삭제 여부를 판단하는 동안 Worker가 같은 작업을 시작하지 못하게 합니다.
            queryset = self.get_queryset().select_for_update()
            job = get_object_or_404(queryset, pk=kwargs["pk"])
            self.check_object_permissions(request, job)

            if job.status == AnalysisJob.Status.STARTED:
                return Response(
                    {"detail": "처리 중인 작업은 완료된 뒤 삭제할 수 있습니다."},
                    status=409,
                )

            video_name = job.video.name
            storage = job.video.storage
            job.delete()

            if video_name:
                transaction.on_commit(
                    lambda: storage.delete(video_name),
                    robust=True,
                )

        return Response(status=204)

    def partial_update(self, request, *args, **kwargs):
        job = self.get_object()
        serializer = AnalysisMemoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        job.memo = serializer.validated_data["memo"]
        job.save(update_fields=["memo"])
        return Response({"id": job.pk, "memo": job.memo})

    def perform_create(self, serializer):
        task_id = str(uuid4())

        with transaction.atomic():
            job = serializer.save(
                user=self.request.user,
                task_id=task_id,
            )

            def enqueue():
                try:
                    run_analysis.apply_async(args=[job.pk], task_id=task_id)
                except OperationalError as exc:
                    AnalysisJob.objects.filter(
                        pk=job.pk,
                        status=AnalysisJob.Status.PENDING,
                    ).update(
                        status=AnalysisJob.Status.FAILURE,
                        error_message="Redis 대기열에 작업을 등록하지 못했습니다.",
                        finished_at=timezone.now(),
                    )
                    raise QueueUnavailable() from exc

            transaction.on_commit(enqueue)
