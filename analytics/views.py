# analytics/views.py
from rest_framework import viewsets, status, permissions, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta

from analytics.models import PlatformMetric, UserActivityLog
from analytics.serializers import (
    PlatformMetricSerializer, UserActivityLogSerializer,
    DateRangeSerializer, MetricsSummarySerializer
)
from users.permissions import IsAdmin


class PlatformMetricViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for platform metrics (Admin only)"""
    serializer_class = PlatformMetricSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    queryset = PlatformMetric.objects.all().order_by('-metric_date')
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's metrics"""
        today = timezone.now().date()
        
        # Calculate or get today's metrics
        from analytics.models import PlatformMetric
        metrics, created = PlatformMetric.calculate_daily_metrics(today)
        
        serializer = self.get_serializer(metrics)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def range(self, request):
        """Get metrics for a date range"""
        serializer = DateRangeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        start_date = data['start_date']
        end_date = data['end_date']
        
        metrics = PlatformMetric.objects.filter(
            metric_date__gte=start_date,
            metric_date__lte=end_date
        ).order_by('metric_date')
        
        serializer = self.get_serializer(metrics, many=True)
        
        # Calculate totals
        totals = metrics.aggregate(
            total_revenue=Sum('total_revenue'),
            total_users=Sum('new_registrations'),
            total_contracts=Sum('new_contracts')
        )
        
        return Response({
            "metrics": serializer.data,
            "totals": totals,
            "date_range": {
                "start": start_date,
                "end": end_date,
                "days": (end_date - start_date).days + 1
            }
        })
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get platform summary"""
        # Calculate various time periods
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        last_week = today - timedelta(days=7)
        last_month = today - timedelta(days=30)
        
        # Today's metrics
        today_metrics, _ = PlatformMetric.calculate_daily_metrics(today)
        
        # Yesterday's metrics
        yesterday_metrics, _ = PlatformMetric.calculate_daily_metrics(yesterday)
        
        # Weekly metrics
        weekly_metrics = PlatformMetric.objects.filter(
            metric_date__gte=last_week,
            metric_date__lte=today
        )
        weekly_totals = weekly_metrics.aggregate(
            revenue=Sum('total_revenue'),
            new_users=Sum('new_registrations'),
            new_contracts=Sum('new_contracts')
        )
        
        # Monthly metrics
        monthly_metrics = PlatformMetric.objects.filter(
            metric_date__gte=last_month,
            metric_date__lte=today
        )
        monthly_totals = monthly_metrics.aggregate(
            revenue=Sum('total_revenue'),
            new_users=Sum('new_registrations'),
            new_contracts=Sum('new_contracts')
        )
        
        # Get current counts
        from users.models import User
        from contracts.models import Contract
        from job_postings.models import JobPosting
        
        current_counts = {
            'total_users': User.objects.filter(is_active=True).count(),
            'active_employers': User.objects.filter(role='employer', is_active=True).count(),
            'active_workers': User.objects.filter(role='worker', is_active=True).count(),
            'active_contracts': Contract.objects.filter(status='active').count(),
            'active_jobs': JobPosting.objects.filter(status='active').count(),
        }
        
        return Response({
            "today": {
                "revenue": today_metrics.total_revenue,
                "new_users": today_metrics.new_registrations,
                "new_contracts": today_metrics.new_contracts
            },
            "yesterday": {
                "revenue": yesterday_metrics.total_revenue if yesterday_metrics else 0,
                "new_users": yesterday_metrics.new_registrations if yesterday_metrics else 0,
                "new_contracts": yesterday_metrics.new_contracts if yesterday_metrics else 0
            },
            "weekly": weekly_totals,
            "monthly": monthly_totals,
            "current": current_counts
        })
    
    @action(detail=False, methods=['get'])
    def revenue(self, request):
        """Get revenue analytics"""
        # Last 30 days revenue
        last_30_days = timezone.now().date() - timedelta(days=30)
        
        daily_revenue = PlatformMetric.objects.filter(
            metric_date__gte=last_30_days
        ).values('metric_date').annotate(
            revenue=Sum('total_revenue')
        ).order_by('metric_date')
        
        # Format for chart
        revenue_data = {
            'labels': [str(item['metric_date']) for item in daily_revenue],
            'datasets': [{
                'label': 'Revenue (UGX)',
                'data': [float(item['revenue']) for item in daily_revenue]
            }]
        }
        
        return Response({
            "revenue_data": revenue_data,
            "total_revenue_30d": sum(item['revenue'] for item in daily_revenue),
            "average_daily_revenue": sum(item['revenue'] for item in daily_revenue) / 30
        })


class UserActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for user activity logs (Admin only)"""
    serializer_class = UserActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    queryset = UserActivityLog.objects.all().order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent activity"""
        recent_activity = UserActivityLog.objects.all().order_by('-created_at')[:100]
        serializer = self.get_serializer(recent_activity, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def user_activity(self, request, user_id=None):
        """Get activity for a specific user"""
        from users.models import User
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        activity_logs = UserActivityLog.objects.filter(user=user).order_by('-created_at')[:50]
        serializer = self.get_serializer(activity_logs, many=True)
        
        # Activity summary
        summary = activity_logs.values('action_type').annotate(
            count=Count('id'),
            last_activity=Max('created_at')
        ).order_by('-count')
        
        return Response({
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
                "joined": user.date_joined
            },
            "activity_logs": serializer.data,
            "summary": summary
        })


class AnalyticsDashboardView(generics.GenericAPIView):
    """Comprehensive analytics dashboard"""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    def get(self, request):
        """Get dashboard data"""
        # User growth
        from users.models import User
        from django.db.models.functions import TruncDay
        
        last_30_days = timezone.now() - timedelta(days=30)
        user_growth = User.objects.filter(
            date_joined__gte=last_30_days
        ).annotate(
            day=TruncDay('date_joined')
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')
        
        # Contract analytics
        from contracts.models import Contract
        contract_status = Contract.objects.values('status').annotate(
            count=Count('id')
        )
        
        # Revenue by category
        from payments.models import PaymentTransaction
        revenue_by_category = PaymentTransaction.objects.filter(
            status='completed',
            created_at__gte=last_30_days
        ).values('transaction_type').annotate(
            total=Sum('amount')
        )
        
        # Top performing workers
        from reviews.models import Review
        top_workers = User.objects.filter(
            role='worker',
            reviews_received__is_verified=True
        ).annotate(
            avg_rating=Avg('reviews_received__rating'),
            review_count=Count('reviews_received')
        ).filter(
            review_count__gte=3
        ).order_by('-avg_rating')[:10]
        
        # Top employers
        top_employers = User.objects.filter(
            role='employer'
        ).annotate(
            contracts_count=Count('employerprofile__contracts'),
            total_spent=Sum('employerprofile__contracts__total_monthly_cost')
        ).filter(
            contracts_count__gte=1
        ).order_by('-total_spent')[:10]
        
        return Response({
            "user_growth": list(user_growth),
            "contract_status": list(contract_status),
            "revenue_by_category": list(revenue_by_category),
            "top_workers": [
                {
                    "id": str(user.id),
                    "name": user.get_full_name(),
                    "avg_rating": user.avg_rating,
                    "review_count": user.review_count
                }
                for user in top_workers
            ],
            "top_employers": [
                {
                    "id": str(user.id),
                    "name": user.get_full_name(),
                    "contracts_count": user.contracts_count,
                    "total_spent": user.total_spent or 0
                }
                for user in top_employers
            ]
        })
