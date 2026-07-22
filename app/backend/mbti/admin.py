from django.contrib import admin

from mbti.models import MbtiMonthlyAnalysisJob


@admin.register(MbtiMonthlyAnalysisJob)
class MbtiMonthlyAnalysisJobAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user_id',
        'period_key',
        'status',
        'trigger_source',
        'retry_count',
        'scheduled_at',
        'finished_at',
    )
    list_filter = ('status', 'trigger_source', 'period_key')
    search_fields = ('user_id', 'input_hash')
    readonly_fields = (
        'input_hash',
        'created_at',
        'updated_at',
        'started_at',
        'finished_at',
    )
