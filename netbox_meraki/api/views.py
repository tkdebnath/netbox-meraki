"""
API views for NetBox Meraki plugin
"""
from rest_framework import viewsets, status
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
    
    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """Get live progress updates for a sync operation"""
        try:
            sync_log = self.get_object()
            return Response({
                'id': sync_log.id,
                'status': sync_log.status,
                'current_operation': sync_log.current_operation,
                'progress_percent': sync_log.progress_percent,
                'progress_logs': sync_log.progress_logs,
                'cancel_requested': sync_log.cancel_requested,
                'organizations_synced': sync_log.organizations_synced,
                'networks_synced': sync_log.networks_synced,
                'devices_synced': sync_log.devices_synced,
                'vlans_synced': sync_log.vlans_synced,
                'prefixes_synced': sync_log.prefixes_synced,
                'ssids_synced': sync_log.ssids_synced,
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=500
            )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an ongoing sync operation"""
        try:
            sync_log = self.get_object()
            if sync_log.status not in ['running', 'pending_review']:
                return Response(
                    {'error': 'Cannot cancel a sync that is not running'},
                    status=400
                )
            sync_log.request_cancel()
            return Response({
                'message': 'Cancellation requested',
                'cancelled_at': sync_log.cancelled_at
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=500
            )

