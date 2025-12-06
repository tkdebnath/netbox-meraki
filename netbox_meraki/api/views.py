"""
API views for NetBox Meraki plugin
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from netbox_meraki.models import SyncLog
from .serializers import SyncLogSerializer
from netbox_meraki.sync_service import MerakiSyncService


class SyncLogViewSet(viewsets.ReadOnlyModelViewSet):
    """API viewset for SyncLog"""
    
    queryset = SyncLog.objects.all()
    serializer_class = SyncLogSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def trigger_sync(self, request):
        """Trigger a new synchronization"""
        try:
            sync_service = MerakiSyncService()
            sync_log = sync_service.sync_all()
            serializer = self.get_serializer(sync_log)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=500
            )
