# documents/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from documents import views

router = DefaultRouter()
router.register(r'documents', views.WorkerDocumentViewSet, basename='document')
router.register(r'verification-requests', views.DocumentVerificationRequestViewSet, basename='verification-request')
router.register(r'document-types', views.DocumentTypeConfigViewSet, basename='document-type')
router.register(r'admin-documents', views.AdminDocumentViewSet, basename='admin-document')

urlpatterns = [
    path('', include(router.urls)),
]
