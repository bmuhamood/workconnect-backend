# reviews/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from reviews import views

router = DefaultRouter()
router.register(r'reviews', views.ReviewViewSet, basename='review')
router.register(r'admin-reviews', views.AdminReviewViewSet, basename='admin-review')

urlpatterns = [
    path('', include(router.urls)),
    path('user/<uuid:user_id>/', 
         views.ReviewViewSet.as_view({'get': 'user_reviews'}),
         name='user-reviews'),
]
