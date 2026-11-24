from django.urls import path
from rest_framework.routers import SimpleRouter

from . import page_views
from .views import AnalysisJobViewSet

app_name = "analyses"

router = SimpleRouter()
router.register("analyses", AnalysisJobViewSet, basename="analysis-job")

urlpatterns = [
    path("", page_views.index, name="index"),
]
