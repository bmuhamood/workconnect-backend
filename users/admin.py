# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import (
    User, EmployerProfile, WorkerProfile, JobCategory, WorkerSkill,
    Verification, WorkerReference, AuditLog
)


class UserAdmin(BaseUserAdmin):
    """Custom admin interface for User model"""
    
    list_display = ('email', 'phone', 'first_name', 'last_name', 'role', 'status', 'is_verified', 'is_active')
    list_filter = ('role', 'status', 'is_verified', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('email', 'phone', 'first_name', 'last_name')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('email', 'phone', 'password')}),
        (_('Personal Info'), {'fields': ('first_name', 'last_name')}),
        (_('Role and Status'), {'fields': ('role', 'status')}),
        (_('Verification'), {'fields': ('is_verified', 'email_verified', 'phone_verified')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important Dates'), {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'phone', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'last_login')


class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'company_name', 'city', 'id_verified', 'subscription_tier')
    list_filter = ('city', 'id_verified', 'subscription_tier')
    search_fields = ('user__email', 'user__phone', 'first_name', 'last_name', 'company_name')
    raw_id_fields = ('user',)


class WorkerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'city', 'verification_status', 
                   'availability', 'rating_average', 'trust_score')
    list_filter = ('verification_status', 'availability', 'city', 'subscription_tier')
    search_fields = ('user__email', 'user__phone', 'first_name', 'last_name', 'national_id')
    raw_id_fields = ('user',)


class JobCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')


class WorkerSkillAdmin(admin.ModelAdmin):
    list_display = ('worker', 'skill_name', 'proficiency_level', 'years_of_experience', 'is_primary')
    list_filter = ('proficiency_level', 'is_primary', 'category')
    search_fields = ('worker__first_name', 'worker__last_name', 'skill_name')
    raw_id_fields = ('worker', 'category')


class VerificationAdmin(admin.ModelAdmin):
    list_display = ('worker', 'verification_type', 'status', 'verified_by', 'verified_at')
    list_filter = ('verification_type', 'status')
    search_fields = ('worker__first_name', 'worker__last_name', 'verification_notes')
    raw_id_fields = ('worker', 'verified_by')


class WorkerReferenceAdmin(admin.ModelAdmin):
    list_display = ('worker', 'referee_name', 'relationship', 'company_name', 'is_verified')
    list_filter = ('is_verified', 'relationship')
    search_fields = ('worker__first_name', 'worker__last_name', 'referee_name', 'referee_phone')
    raw_id_fields = ('worker', 'verified_by')


class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'entity_type', 'timestamp')
    list_filter = ('action', 'entity_type', 'timestamp')
    search_fields = ('user__email', 'user__phone', 'entity_type')
    readonly_fields = ('user', 'action', 'entity_type', 'entity_id', 'ip_address', 
                      'user_agent', 'old_values', 'new_values', 'timestamp')
    date_hierarchy = 'timestamp'


# Register models
admin.site.register(User, UserAdmin)
admin.site.register(EmployerProfile, EmployerProfileAdmin)
admin.site.register(WorkerProfile, WorkerProfileAdmin)
admin.site.register(JobCategory, JobCategoryAdmin)
admin.site.register(WorkerSkill, WorkerSkillAdmin)
admin.site.register(Verification, VerificationAdmin)
admin.site.register(WorkerReference, WorkerReferenceAdmin)
admin.site.register(AuditLog, AuditLogAdmin)
