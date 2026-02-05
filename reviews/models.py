# reviews/models.py (already created, but adding manager)
import uuid
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from users.models import User
from contracts.models import Contract


class ReviewManager(models.Manager):
    """Custom manager for reviews"""
    
    def verified(self):
        """Get only verified reviews"""
        return self.filter(is_verified=True, is_flagged=False)
    
    def for_user(self, user):
        """Get reviews for a specific user"""
        return self.filter(reviewee=user, is_verified=True, is_flagged=False)
    
    def average_rating(self, user):
        """Calculate average rating for a user"""
        from django.db.models import Avg
        result = self.filter(
            reviewee=user,
            is_verified=True,
            is_flagged=False
        ).aggregate(avg_rating=Avg('rating'))
        return result['avg_rating'] or 0


class Review(models.Model):
    """Model for reviews and ratings"""
    
    objects = ReviewManager()
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews_given'
    )
    reviewee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews_received'
    )
    
    # Overall rating
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField()
    
    # Category ratings
    professionalism_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    punctuality_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    communication_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    quality_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    
    # Verification and Moderation
    is_verified = models.BooleanField(default=False)  # Only verified if contract completed
    is_flagged = models.BooleanField(default=False)   # For fake/inappropriate reviews
    flagged_reason = models.TextField(blank=True, null=True)
    
    # Response from reviewee
    response = models.TextField(blank=True, null=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['contract', 'reviewer']
        indexes = [
            models.Index(fields=['reviewee']),
            models.Index(fields=['contract']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_verified']),
        ]
    
    def __str__(self):
        return f"{self.rating} stars - {self.reviewer.email}"
    
    def save(self, *args, **kwargs):
        # Auto-verify if contract is completed
        if self.contract.status == 'completed' and not self.is_verified:
            self.is_verified = True
        
        # Update reviewee's average rating
        super().save(*args, **kwargs)
        
        if self.is_verified and not self.is_flagged:
            self.update_reviewee_rating()
    
    def update_reviewee_rating(self):
        """Update the reviewee's average rating"""
        from django.db.models import Avg
        from users.models import EmployerProfile, WorkerProfile
        
        verified_reviews = Review.objects.filter(
            reviewee=self.reviewee,
            is_verified=True,
            is_flagged=False
        )
        
        # Calculate overall average
        avg_rating = verified_reviews.aggregate(
            avg_rating=Avg('rating')
        )['avg_rating'] or 0
        
        # Calculate category averages
        category_avgs = verified_reviews.aggregate(
            avg_professionalism=Avg('professionalism_rating'),
            avg_punctuality=Avg('punctuality_rating'),
            avg_communication=Avg('communication_rating'),
            avg_quality=Avg('quality_rating')
        )
        
        # Update profile based on user role
        if self.reviewee.role == 'worker':
            profile = self.reviewee.workerprofile
        elif self.reviewee.role == 'employer':
            profile = self.reviewee.employerprofile
        else:
            return
        
        profile.rating_average = round(avg_rating, 2)
        profile.total_reviews = verified_reviews.count()
        
        # Save category averages if they exist
        if any(category_avgs.values()):
            profile.rating_breakdown = {
                'professionalism': round(category_avgs['avg_professionalism'] or 0, 2),
                'punctuality': round(category_avgs['avg_punctuality'] or 0, 2),
                'communication': round(category_avgs['avg_communication'] or 0, 2),
                'quality': round(category_avgs['avg_quality'] or 0, 2)
            }
        
        profile.save()