from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import AnalysisJob
from .tasks import run_analysis


class AnalysisTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(username="owner")
        cls.other = User.objects.create_user(username="other")

        cls.job = AnalysisJob.objects.create(
            user=cls.owner,
            input_type=AnalysisJob.InputType.UPLOAD,
            video="analyses/test.mp4",
        )
        cls.other_job = AnalysisJob.objects.create(
            user=cls.other,
            input_type=AnalysisJob.InputType.CAMERA,
            camera_id="phone",
        )

    def test_list_only_shows_my_jobs(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("analysis-job-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [self.job.pk])

    def test_other_users_job_returns_404(self):
        self.client.force_login(self.owner)
        url = reverse("analysis-job-detail", args=[self.other_job.pk])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    @patch("analyses.tasks.request_video_prediction")
    def test_success_saves_prediction_once(self, predict):
        predict.return_value = {
            "processing_seconds": 0.9,
            "predictions": [
                {"track_id": 1, "action_label": "wave", "confidence": 0.75}
            ],
        }

        # 같은 작업이 두 번 전달돼도 결과는 한 번만 저장돼야 합니다.
        run_analysis.run(self.job.pk)
        run_analysis.run(self.job.pk)

        self.job.refresh_from_db()
        self.assertEqual(self.job.status, AnalysisJob.Status.SUCCESS)
        self.assertEqual(self.job.processing_seconds, 0.9)
        self.assertIsNotNone(self.job.finished_at)
        self.assertEqual(self.job.predictions.count(), 1)

        result = self.job.predictions.get()
        self.assertEqual(result.track_id, 1)
        self.assertEqual(result.action_label, "wave")
        self.assertEqual(result.confidence, 0.75)
        predict.assert_called_once()

    @patch("analyses.tasks.request_video_prediction")
    def test_failure_saves_error(self, predict):
        predict.side_effect = RuntimeError("테스트용 추론 실패")

        with self.assertLogs("analyses.tasks", level="ERROR"):
            with self.assertRaisesMessage(RuntimeError, "테스트용 추론 실패"):
                run_analysis.run(self.job.pk)

        self.job.refresh_from_db()
        self.assertEqual(self.job.status, AnalysisJob.Status.FAILURE)
        self.assertIn("테스트용 추론 실패", self.job.error_message)
        self.assertIsNotNone(self.job.finished_at)
        self.assertFalse(self.job.predictions.exists())


class AnalysisMemoTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username="memo_owner")
        self.other = User.objects.create_user(username="memo_other")
        self.job = AnalysisJob.objects.create(
            user=self.owner,
            input_type=AnalysisJob.InputType.UPLOAD,
            status=AnalysisJob.Status.SUCCESS,
            memo="기존 메모",
        )
        self.url = reverse("analysis-job-detail", args=[self.job.pk])

    def test_owner_can_update_and_read_memo(self):
        self.client.force_login(self.owner)
        response = self.client.patch(self.url, {"memo": "검토 완료"}, format="json")
        self.assertEqual(response.status_code, 200)

        detail = self.client.get(self.url)
        self.assertEqual(detail.data["memo"], "검토 완료")
        self.assertEqual(detail.data["status"], AnalysisJob.Status.SUCCESS)

    def test_other_user_cannot_edit_memo(self):
        self.client.force_login(self.other)
        response = self.client.patch(self.url, {"memo": "다른 사용자"}, format="json")
        self.assertEqual(response.status_code, 404)

        self.job.refresh_from_db()
        self.assertEqual(self.job.memo, "기존 메모")

    def test_status_change_rejects_entire_request(self):
        self.client.force_login(self.owner)
        response = self.client.patch(
            self.url,
            {"memo": "변경 시도", "status": "FAILURE"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

        self.job.refresh_from_db()
        self.assertEqual(self.job.memo, "기존 메모")
        self.assertEqual(self.job.status, AnalysisJob.Status.SUCCESS)


class AnalysisDeleteTests(APITestCase):
    def setUp(self):
        from tempfile import TemporaryDirectory
        from django.core.files.base import ContentFile
        from django.test import override_settings

        # 실제 backend/media 대신 테스트 전용 임시 폴더를 사용합니다.
        temp_media = TemporaryDirectory()
        self.addCleanup(temp_media.cleanup)
        media_settings = override_settings(MEDIA_ROOT=temp_media.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)

        User = get_user_model()
        self.owner = User.objects.create_user(username="delete_owner")
        self.other = User.objects.create_user(username="delete_other")

        self.job = AnalysisJob.objects.create(
            user=self.owner,
            input_type=AnalysisJob.InputType.UPLOAD,
            status=AnalysisJob.Status.SUCCESS,
        )
        self.job.video.save("delete_test.mp4", ContentFile(b"test video"))
        self.prediction = self.job.predictions.create(
            track_id=1, action_label="wave", confidence=0.75
        )
        self.url = reverse("analysis-job-detail", args=[self.job.pk])

    def test_owner_can_delete_job_predictions_and_file(self):
        self.client.force_login(self.owner)
        storage = self.job.video.storage
        video_name = self.job.video.name
        self.assertTrue(storage.exists(video_name))

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(AnalysisJob.objects.filter(pk=self.job.pk).exists())
        self.assertFalse(type(self.prediction).objects.filter(pk=self.prediction.pk).exists())
        self.assertFalse(storage.exists(video_name))

    def test_other_user_cannot_delete_job(self):
        self.client.force_login(self.other)
        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 404)
        self.assertTrue(AnalysisJob.objects.filter(pk=self.job.pk).exists())
        self.assertTrue(self.job.video.storage.exists(self.job.video.name))

    def test_running_job_cannot_be_deleted(self):
        self.job.status = AnalysisJob.Status.STARTED
        self.job.save(update_fields=["status"])
        self.client.force_login(self.owner)

        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, 409)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, AnalysisJob.Status.STARTED)
        self.assertTrue(self.job.video.storage.exists(self.job.video.name))
