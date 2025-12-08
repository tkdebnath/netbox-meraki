"""
API serializers for NetBox Meraki plugin
"""
from rest_framework import serializers
from netbox_meraki.models import SyncLog


class SyncLogSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = SyncLog
        fields = [
            'id',
            'timestamp',
            'status',
            'message',
            'organizations_synced',
            'networks_synced',
            'devices_synced',
            'vlans_synced',
            'prefixes_synced',
            'errors',
            'duration_seconds',
        ]
