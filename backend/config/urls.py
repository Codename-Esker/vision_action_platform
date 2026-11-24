from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from analyses import page_views
from analyses.urls import router

urlpatterns = [
    path("admin/", admin.site.urls),
    path("dashboard/", page_views.dashboard, name="dashboard"),
    path("accounts/", include("accounts.urls")),
    path("analyses/", include("analyses.urls")),
    path("api/v1/", include(router.urls)),
    path("", RedirectView.as_view(pattern_name="analyses:index"), name="home"),
]
