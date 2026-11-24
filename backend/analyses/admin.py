from django.contrib import admin

from .models import AnalysisJob, PersonPrediction


class PersonPredictionInline(admin.TabularInline):
    model = PersonPrediction
    extra = 0
    fields = ("track_id", "action_label", "confidence")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(AnalysisJob)
class AnalysisJobAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "input_type", "status", "created_at", "finished_at")
    list_filter = ("status", "input_type", "created_at")
    search_fields = ("user__username", "task_id")
    readonly_fields = ("created_at",)
    list_select_related = ("user",)
    inlines = (PersonPredictionInline,)


@admin.register(PersonPrediction)
class PersonPredictionAdmin(admin.ModelAdmin):
    list_display = ("job_id", "track_id", "action_label", "confidence", "created_at")
    list_filter = ("action_label",)
    search_fields = ("action_label", "job__user__username")
    readonly_fields = ("created_at",)
