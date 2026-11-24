from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render

from .models import AnalysisJob, PersonPrediction


@login_required
def index(request):
    recent_jobs = (
        AnalysisJob.objects
        .filter(user=request.user)
        .order_by("-created_at", "-id")[:10]
    )
    return render(request, "analyses/index.html", {
        "recent_jobs": recent_jobs,
        "camera_ids": list(settings.CAMERA_SOURCES),
    })


@staff_member_required
def dashboard(request):
    action_names = {
        "bend_return": "몸 굽혔다 펴기",
        "drink_return": "마시고 돌아오기",
        "leg_raise_lower": "다리 들었다 내리기",
        "sit_stand": "앉았다 일어서기",
        "walk_turn_walk": "걷고 돌아서 걷기",
        "wave": "손 흔들기",
    }

    action_counts = dict(
        PersonPrediction.objects.order_by()
        .values("action_label")
        .annotate(total=Count("pk"))
        .values_list("action_label", "total")
    )
    status_counts = dict(
        AnalysisJob.objects.order_by()
        .values("status")
        .annotate(total=Count("pk"))
        .values_list("status", "total")
    )

    actions = [
        {"label": label, "count": action_counts.get(code, 0)}
        for code, label in action_names.items()
    ]
    statuses = [
        {"label": label, "count": status_counts.get(code, 0)}
        for code, label in AnalysisJob.Status.choices
    ]

    recent_jobs = (
        AnalysisJob.objects.select_related("user")
        .order_by("-created_at", "-id")[:10]
    )
    return render(request, "analyses/dashboard.html", {
        "actions": actions,
        "statuses": statuses,
        "recent_jobs": recent_jobs,
    })
