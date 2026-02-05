# job_postings/admin.py
from django.contrib import admin
from job_postings.models import JobPosting, JobApplication


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ('title', 'employer', 'category', 'status', 'salary_min', 'salary_max', 'created_at')
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('title', 'description', 'employer__company_name')
    readonly_fields = ('views_count', 'applications_count', 'published_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('employer', 'category', 'title', 'description', 'requirements')
        }),
        ('Salary and Location', {
            'fields': ('salary_min', 'salary_max', 'location', 'work_schedule', 'start_date')
        }),
        ('Status and Metadata', {
            'fields': ('status', 'is_featured', 'views_count', 'applications_count', 'published_at', 'expires_at')
        }),
    )


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('worker', 'job_posting', 'status', 'ai_match_score', 'applied_at')
    list_filter = ('status', 'applied_at')
    search_fields = ('worker__first_name', 'worker__last_name', 'job_posting__title')
    readonly_fields = ('applied_at', 'reviewed_at', 'ai_match_score', 'ai_recommendation')
    fieldsets = (
        ('Application Details', {
            'fields': ('worker', 'job_posting', 'cover_letter', 'expected_salary', 'availability_date')
        }),
        ('Status and AI', {
            'fields': ('status', 'ai_match_score', 'ai_recommendation', 'applied_at', 'reviewed_at')
        }),
    )
