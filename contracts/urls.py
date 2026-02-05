from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ContractViewSet, ReplacementViewSet, ContractDocumentViewSet

router = DefaultRouter()
router.register(r'', ContractViewSet, basename='contract')
router.register(r'replacements', ReplacementViewSet, basename='replacement')
router.register(r'documents', ContractDocumentViewSet, basename='contract-document')

urlpatterns = [
    path('', include(router.urls)),
]
