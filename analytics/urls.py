# analytics/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from analytics import views

router = DefaultRouter()
router.register(r'metrics', views.PlatformMetricViewSet, basename='metric')
router.register(r'activity-logs', views.UserActivityLogViewSet, basename='activity-log')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', views.AnalyticsDashboardView.as_view(), name='analytics-dashboard'),
]
