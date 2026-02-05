# reviews/admin.py
from django.contrib import admin
from reviews.models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('reviewee', 'reviewer', 'rating', 'is_verified', 'is_flagged', 'created_at')
    list_filter = ('is_verified', 'is_flagged', 'rating', 'created_at')
    search_fields = ('comment', 'reviewer__email', 'reviewee__email')
    readonly_fields = ('created_at', 'updated_at', 'responded_at')
    fieldsets = (
        ('Review Details', {
            'fields': ('contract', 'reviewer', 'reviewee', 'rating', 'comment')
        }),
        ('Category Ratings', {
            'fields': ('professionalism_rating', 'punctuality_rating', 
                      'communication_rating', 'quality_rating'),
            'classes': ('collapse',)
        }),
        ('Moderation', {
            'fields': ('is_verified', 'is_flagged', 'flagged_reason', 'response')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at', 'responded_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_reviews', 'flag_reviews']
    
    def approve_reviews(self, request, queryset):
        """Admin action to approve selected reviews"""
        queryset.update(is_verified=True, is_flagged=False)
        self.message_user(request, f"{queryset.count()} reviews approved.")
    approve_reviews.short_description = "Approve selected reviews"
    
    def flag_reviews(self, request, queryset):
        """Admin action to flag selected reviews"""
        queryset.update(is_flagged=True, flagged_reason="Flagged by admin")
        self.message_user(request, f"{queryset.count()} reviews flagged.")
    flag_reviews.short_description = "Flag selected reviews"
