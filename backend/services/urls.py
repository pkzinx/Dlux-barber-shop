from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import ServiceViewSet, PublicServiceListView, UpdateServiceOrderView

router = DefaultRouter()
router.register(r'', ServiceViewSet, basename='services')

urlpatterns = [
    path('public/', PublicServiceListView.as_view(), name='public_services'),
    path('update-order/', UpdateServiceOrderView.as_view(), name='update_service_order'),
]

urlpatterns += router.urls