from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import ServiceViewSet, PublicServiceListView

router = DefaultRouter()
router.register(r'', ServiceViewSet, basename='services')

urlpatterns = [
    path('public/', PublicServiceListView.as_view(), name='public_services'),
]

urlpatterns += router.urls