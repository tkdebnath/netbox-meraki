"""
Views for NetBox Meraki plugin
"""
import logging
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.conf import settings

from .sync_service import MerakiSyncService
from .models import SyncLog


logger = logging.getLogger('netbox_meraki')


class DashboardView(LoginRequiredMixin, View):
    """Dashboard view showing sync status and recent logs"""
    
    def get(self, request):
        recent_logs = SyncLog.objects.all()[:10]
        
        # Get latest successful sync
        latest_sync = SyncLog.objects.filter(status='success').first()
        
        # Get plugin configuration
        plugin_config = settings.PLUGINS_CONFIG.get('netbox_meraki', {})
        api_key_configured = bool(plugin_config.get('meraki_api_key'))
        
        context = {
            'recent_logs': recent_logs,
            'latest_sync': latest_sync,
            'api_key_configured': api_key_configured,
        }
        
        return render(request, 'netbox_meraki/dashboard.html', context)


class SyncView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """View to trigger manual synchronization"""
    
    permission_required = 'dcim.add_device'
    
    def get(self, request):
        context = {
            'title': 'Sync from Meraki'
        }
        return render(request, 'netbox_meraki/sync.html', context)
    
    def post(self, request):
        try:
            logger.info(f"Manual sync triggered by user {request.user}")
            
            # Start sync
            sync_service = MerakiSyncService()
            sync_log = sync_service.sync_all()
            
            # Show results
            if sync_log.status == 'success':
                messages.success(
                    request,
                    f"Synchronization completed successfully. "
                    f"Synced {sync_log.devices_synced} devices, "
                    f"{sync_log.vlans_synced} VLANs, "
                    f"{sync_log.prefixes_synced} prefixes."
                )
            elif sync_log.status == 'partial':
                messages.warning(
                    request,
                    f"Synchronization completed with errors. "
                    f"Synced {sync_log.devices_synced} devices. "
                    f"Check logs for details."
                )
            else:
                messages.error(
                    request,
                    f"Synchronization failed: {sync_log.message}"
                )
            
            return redirect('plugins:netbox_meraki:synclog', pk=sync_log.pk)
            
        except Exception as e:
            logger.error(f"Sync failed: {str(e)}")
            messages.error(request, f"Synchronization failed: {str(e)}")
            return redirect('plugins:netbox_meraki:dashboard')


class SyncLogView(LoginRequiredMixin, View):
    """View to display sync log details"""
    
    def get(self, request, pk):
        sync_log = get_object_or_404(SyncLog, pk=pk)
        
        context = {
            'sync_log': sync_log,
        }
        
        return render(request, 'netbox_meraki/synclog.html', context)


class ConfigView(LoginRequiredMixin, View):
    """View to display plugin configuration"""
    
    def get(self, request):
        plugin_config = settings.PLUGINS_CONFIG.get('netbox_meraki', {})
        
        # Hide API key for security
        config_display = dict(plugin_config)
        if config_display.get('meraki_api_key'):
            config_display['meraki_api_key'] = '****' + config_display['meraki_api_key'][-4:]
        
        context = {
            'config': config_display,
        }
        
        return render(request, 'netbox_meraki/config.html', context)
