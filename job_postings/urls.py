# job_postings/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from job_postings import views

router = DefaultRouter()
router.register(r'job-postings', views.JobPostingViewSet, basename='job-posting')
router.register(r'applications', views.JobApplicationViewSet, basename='application')
router.register(r'matching', views.MatchingView, basename='matching')

urlpatterns = [
    path('', include(router.urls)),
]
