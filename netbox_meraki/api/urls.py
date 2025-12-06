"""
API URLs for NetBox Meraki plugin
"""
from rest_framework import routers
from .views import SyncLogViewSet


router = routers.DefaultRouter()
router.register('sync-logs', SyncLogViewSet)

urlpatterns = router.urls
