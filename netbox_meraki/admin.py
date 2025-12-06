"""
Admin configuration for NetBox Meraki plugin
"""
from django.contrib import admin
from .models import SyncLog, PluginSettings, SiteNameRule, SyncReview, ReviewItem


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


@admin.register(PluginSettings)
class PluginSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'mx_device_role',
        'ms_device_role',
        'mr_device_role',
        'auto_create_device_roles',
    ]
    fieldsets = (
        ('Device Role Mappings', {
            'fields': (
                'mx_device_role',
                'ms_device_role',
                'mr_device_role',
                'mg_device_role',
                'mv_device_role',
                'mt_device_role',
                'default_device_role',
            )
        }),
        ('Options', {
            'fields': ('auto_create_device_roles',)
        }),
    )
    
    def has_add_permission(self, request):
        # Only allow one settings instance
        return not PluginSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SiteNameRule)
class SiteNameRuleAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'priority',
        'enabled',
        'regex_pattern',
        'site_name_template',
    ]
    list_filter = ['enabled']
    list_editable = ['enabled', 'priority']
    ordering = ['priority', 'name']
    search_fields = ['name', 'regex_pattern', 'site_name_template']
    fieldsets = (
        (None, {
            'fields': ('name', 'enabled', 'priority')
        }),
        ('Transformation Rule', {
            'fields': ('regex_pattern', 'site_name_template', 'description')
        }),
    )


@admin.register(SyncReview)
class SyncReviewAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'created',
        'status',
        'items_total',
        'items_approved',
        'items_rejected',
    ]
    list_filter = ['status', 'created']
    readonly_fields = [
        'created',
        'items_total',
        'items_approved',
        'items_rejected',
    ]
    
    def has_add_permission(self, request):
        return False


@admin.register(ReviewItem)
class ReviewItemAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'review',
        'item_type',
        'action_type',
        'object_name',
        'status',
    ]
    list_filter = ['item_type', 'action_type', 'status']
    readonly_fields = [
        'review',
        'item_type',
        'action_type',
        'object_name',
        'proposed_data',
        'current_data',
    ]
    search_fields = ['object_name']
    
    def has_add_permission(self, request):
        return False
