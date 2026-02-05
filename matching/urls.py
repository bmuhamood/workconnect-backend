# matching/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from matching import views

router = DefaultRouter()
router.register(r'', views.MatchingViewSet, basename='matching')

urlpatterns = [
    path('', include(router.urls)),
    path('explain-match/<uuid:worker_id>/', 
         views.MatchingViewSet.as_view({'get': 'explain_match'}),
         name='explain-match'),
]
