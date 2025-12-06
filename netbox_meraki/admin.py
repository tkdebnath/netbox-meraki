"""
Admin configuration for NetBox Meraki plugin
"""
from django.contrib import admin
from .models import SyncLog


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = [
        'timestamp',
        'status',
        'organizations_synced',
        'networks_synced',
        'devices_synced',
        'vlans_synced',
        'prefixes_synced',
        'duration_seconds',
    ]
    list_filter = ['status', 'timestamp']
    readonly_fields = [
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
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
