# reviews/views.py
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_filters import DjangoFilterBackend
from django.db.models import Q, Avg

from reviews.models import Review
from reviews.serializers import ReviewSerializer, ReviewResponseSerializer
from users.permissions import IsEmployer, IsWorker, IsAdmin


class ReviewViewSet(viewsets.ModelViewSet):
    """ViewSet for reviews and ratings"""
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['rating', 'is_verified', 'reviewee']
    search_fields = ['comment', 'response']
    ordering_fields = ['created_at', 'rating']
    ordering = ['-created_at']
    
    def get_queryset(self):
        # Check if this is for Swagger schema generation
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset.model.objects.none()
        
        user = self.request.user
        
        if user.role in ['admin', 'super_admin']:
            return Review.objects.all()
        
        # Users can see reviews they gave or received
        return Review.objects.filter(
            Q(reviewer=user) | Q(reviewee=user)
        ).distinct()
    
    def perform_create(self, serializer):
        # Sentiment analysis (simplified)
        comment = serializer.validated_data.get('comment', '')
        
        # Simple spam detection
        if len(comment.split()) < 5:
            serializer.validated_data['is_flagged'] = True
            serializer.validated_data['flagged_reason'] = 'Review too short'
        
        super().perform_create(serializer)
    
    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        """Respond to a review"""
        review = self.get_object()
        
        # Check permission
        if review.reviewee != request.user:
            return Response(
                {"error": "You can only respond to reviews about you"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ReviewResponseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        serializer.update(review, serializer.validated_data)
        
        return Response({
            "status": "response_added",
            "response": review.response,
            "responded_at": review.responded_at
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def moderate(self, request, pk=None):
        """Moderate a review (admin only)"""
        review = self.get_object()
        action = request.data.get('action')
        
        if action == 'approve':
            review.is_flagged = False
            review.save()
            return Response({"status": "approved", "message": "Review approved"})
        
        elif action == 'reject':
            review.is_flagged = True
            review.flagged_reason = request.data.get('reason', 'Inappropriate content')
            review.save()
            return Response({"status": "rejected", "message": "Review rejected"})
        
        elif action == 'delete':
            review.delete()
            return Response({"status": "deleted", "message": "Review deleted"})
        
        else:
            return Response(
                {"error": "Invalid action"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def my_reviews(self, request):
        """Get reviews about the authenticated user"""
        reviews = Review.objects.filter(reviewee=request.user, is_verified=True)
        
        # Calculate average rating
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        
        serializer = self.get_serializer(reviews, many=True)
        
        return Response({
            "average_rating": round(avg_rating, 2),
            "total_reviews": reviews.count(),
            "reviews": serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def given(self, request):
        """Get reviews given by the authenticated user"""
        reviews = Review.objects.filter(reviewer=request.user)
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def user_reviews(self, request, user_id=None):
        """Get reviews for a specific user"""
        from users.models import User
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Only show verified, non-flagged reviews
        reviews = Review.objects.filter(
            reviewee=user,
            is_verified=True,
            is_flagged=False
        )
        
        # Calculate statistics
        total_reviews = reviews.count()
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        
        # Rating distribution
        rating_distribution = {
            5: reviews.filter(rating=5).count(),
            4: reviews.filter(rating=4).count(),
            3: reviews.filter(rating=3).count(),
            2: reviews.filter(rating=2).count(),
            1: reviews.filter(rating=1).count(),
        }
        
        serializer = self.get_serializer(reviews, many=True)
        
        return Response({
            "user": {
                "id": str(user.id),
                "name": user.get_full_name(),
                "role": user.role
            },
            "statistics": {
                "average_rating": round(avg_rating, 2),
                "total_reviews": total_reviews,
                "rating_distribution": rating_distribution
            },
            "reviews": serializer.data
        })


class AdminReviewViewSet(viewsets.ModelViewSet):
    """Admin viewset for review moderation"""
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    queryset = Review.objects.all()
    
    @action(detail=False, methods=['get'])
    def flagged(self, request):
        """Get flagged reviews for moderation"""
        flagged_reviews = Review.objects.filter(is_flagged=True)
        serializer = self.get_serializer(flagged_reviews, many=True)
        return Response(serializer.data)
