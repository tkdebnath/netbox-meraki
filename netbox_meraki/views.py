"""Views for NetBox Meraki plugin"""
import logging
import json
from datetime import datetime, timedelta
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View, ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.conf import settings
from django.urls import reverse_lazy
from django.utils import timezone

from .sync_service import MerakiSyncService
from .models import (
    SyncLog, PluginSettings, SiteNameRule, PrefixFilterRule, 
    SyncReview, ReviewItem
)
from .forms import (
    PluginSettingsForm, SiteNameRuleForm, PrefixFilterRuleForm,
    ScheduledSyncForm
)


logger = logging.getLogger('netbox_meraki')


class DashboardView(LoginRequiredMixin, View):
    
    def get(self, request):
        recent_logs = SyncLog.objects.all()[:10]
        
        # For logs with status='pending_review', check if review actually has pending items
        for log in recent_logs:
            if log.status == 'pending_review':
                # Check if review exists and has pending items
                from .models import SyncReview
                try:
                    review = SyncReview.objects.get(sync_log=log)
                    pending_count = review.items.filter(status='pending').count()
                    if pending_count == 0:
                        # No pending items, update status to completed
                        log.status = 'success'
                        log.message = f"Review completed - {review.items.count()} items processed"
                        log.save()
                except SyncReview.DoesNotExist:
                    pass
        
        latest_sync = SyncLog.objects.filter(status='success').first()
        
        # Get running syncs
        running_syncs = SyncLog.objects.filter(status='running').order_by('-timestamp')
        
        # Get scheduled jobs
        scheduled_jobs = []
        scheduled_jobs_count = 0
        try:
            from core.models.jobs import Job as ScheduledJob
            from .jobs import MerakiSyncJob
            # In NetBox 4.4+, filter by job name instead of job_class
            scheduled_jobs = ScheduledJob.objects.filter(
                name__icontains='Meraki',
                interval__isnull=False  # Only recurring jobs
            ).order_by('-created')[:5]
            scheduled_jobs_count = ScheduledJob.objects.filter(
                name__icontains='Meraki',
                interval__isnull=False
            ).count()
        except ImportError:
            pass
        
        plugin_config = settings.PLUGINS_CONFIG.get('netbox_meraki', {})
        api_key_configured = bool(plugin_config.get('meraki_api_key'))
        
        # Check for device role configuration overrides
        role_fields = [
            'mx_device_role', 'ms_device_role', 'mr_device_role',
            'mg_device_role', 'mv_device_role', 'mt_device_role',
            'default_device_role'
        ]
        device_roles_configured = any(field in plugin_config for field in role_fields)
        configured_roles = [field for field in role_fields if field in plugin_config]
        
        # Check for other configuration parameters
        config_params = [
            'auto_create_sites', 'auto_create_device_types', 
            'auto_create_device_roles', 'auto_create_manufacturers',
            'default_site_group', 'default_manufacturer', 'meraki_base_url'
        ]
        other_configs = [param for param in config_params if param in plugin_config]
        
        context = {
            'recent_logs': recent_logs,
            'latest_sync': latest_sync,
            'running_syncs': running_syncs,
            'scheduled_jobs': scheduled_jobs,
            'scheduled_jobs_count': scheduled_jobs_count,
            'api_key_configured': api_key_configured,
            'device_roles_configured': device_roles_configured,
            'configured_roles_count': len(configured_roles),
            'other_configs_count': len(other_configs),
            'has_additional_config': len(other_configs) > 0,
        }
        
        return render(request, 'netbox_meraki/dashboard.html', context)


class SyncView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """View to trigger manual synchronization"""
    
    permission_required = 'dcim.add_device'
    
    def get(self, request):
        plugin_settings = PluginSettings.get_settings()
        
        try:
            sync_service = MerakiSyncService()
            organizations = sync_service.client.get_organizations()
        except Exception as e:
            logger.error(f"Failed to fetch organizations: {e}")
            organizations = []
        
        context = {
            'title': 'Sync from Meraki',
            'sync_modes': [
                ('auto', 'Auto Sync', 'Automatically apply all changes'),
                ('review', 'Sync with Review', 'Review changes before applying'),
                ('dry_run', 'Dry Run', 'Preview changes without applying'),
            ],
            'default_mode': plugin_settings.sync_mode,
            'organizations': organizations,
        }
        return render(request, 'netbox_meraki/sync.html', context)
    
    def post(self, request):
        sync_mode = request.POST.get('sync_mode', 'review')
        organization_id = request.POST.get('organization_id', '')
        network_ids = request.POST.getlist('network_ids')
        sync_all_networks = request.POST.get('sync_all_networks') == 'true'
        
        try:
            logger.info(f"Manual sync triggered by user {request.user} (mode: {sync_mode}, org: {organization_id})")
            
            sync_service = MerakiSyncService(sync_mode=sync_mode)
            sync_log = sync_service.sync_all(
                organization_id=organization_id if organization_id else None,
                network_ids=network_ids if network_ids and not sync_all_networks else None
            )
            
            # Show results based on mode
            if sync_log.status == 'dry_run':
                messages.info(
                    request,
                    f"Dry run completed. View the results to see what would be changed."
                )
                return redirect('plugins:netbox_meraki:synclog', pk=sync_log.pk)
            elif sync_log.status == 'pending_review':
                messages.info(
                    request,
                    f"Sync completed. {sync_log.review.items_total if hasattr(sync_log, 'review') else 0} items pending review."
                )
                return redirect('plugins:netbox_meraki:review_detail', pk=sync_log.review.pk)
            elif sync_log.status == 'success':
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
    """View to display and edit plugin configuration"""
    
    def get(self, request):
        settings_instance = PluginSettings.get_settings()
        form = PluginSettingsForm(instance=settings_instance)
        site_rules = SiteNameRule.objects.all()
        prefix_filter_rules = PrefixFilterRule.objects.all()
        
        # Get static plugin configuration
        plugin_config = settings.PLUGINS_CONFIG.get('netbox_meraki', {})
        
        # Hide API key for security
        config_display = dict(plugin_config)
        if config_display.get('meraki_api_key'):
            api_key = config_display['meraki_api_key']
            config_display['meraki_api_key'] = '****' + api_key[-4:] if len(api_key) > 4 else '****'
        
        context = {
            'form': form,
            'settings': settings_instance,
            'site_rules': site_rules,
            'prefix_filter_rules': prefix_filter_rules,
            'static_config': config_display,
        }
        
        return render(request, 'netbox_meraki/config.html', context)
    
    def post(self, request):
        settings_instance = PluginSettings.get_settings()
        
        # Debug: Log ALL POST data to see what's being submitted
        logger.info(f"=== FULL POST DATA ===")
        for key, value in request.POST.items():
            logger.info(f"  {key}: {value}")
        logger.info(f"======================")
        
        # Debug: Log incoming POST data for device roles
        logger.info(f"POST data received - MX: {request.POST.get('mx_device_role')}, MS: {request.POST.get('ms_device_role')}, MR: {request.POST.get('mr_device_role')}")
        logger.info(f"Current DB values - MX: {settings_instance.mx_device_role}, MS: {settings_instance.ms_device_role}")
        
        # Handle checkbox fields explicitly - unchecked checkboxes don't send data
        post_data = request.POST.copy()
        
        # Add missing fields that aren't in the template but required by form
        if 'sync_mode' not in post_data:
            post_data['sync_mode'] = settings_instance.sync_mode
        
        # For boolean fields, if not present in POST, it means unchecked
        checkbox_fields = [
            'process_unmatched_sites',
            'auto_create_device_roles',
            'enable_api_throttling',
            'enable_multithreading',
        ]
        
        # Remove any checkbox fields that aren't checked (not in POST data)
        # This ensures the form will set them to False
        for field in checkbox_fields:
            if field not in request.POST:
                # Explicitly set to empty string or 'false' to ensure it's treated as False
                post_data[field] = ''
        
        form = PluginSettingsForm(post_data, instance=settings_instance)
        
        if form.is_valid():
            saved_instance = form.save()
            # Debug: Log what was actually saved
            logger.info(f"Settings saved - MX Role: {saved_instance.mx_device_role}, MS Role: {saved_instance.ms_device_role}")
            # Verify it was actually persisted
            reloaded = PluginSettings.get_settings()
            logger.info(f"Settings reloaded from DB - MX Role: {reloaded.mx_device_role}, MS Role: {reloaded.ms_device_role}")
            messages.success(request, 'Settings updated successfully.')
            return redirect('plugins:netbox_meraki:config')
        else:
            # Debug: Log form errors
            logger.error(f"Form validation failed: {form.errors}")
            messages.error(request, 'Failed to save settings. Please check the form for errors.')
        
        site_rules = SiteNameRule.objects.all()
        prefix_filter_rules = PrefixFilterRule.objects.all()
        plugin_config = settings.PLUGINS_CONFIG.get('netbox_meraki', {})
        config_display = dict(plugin_config)
        if config_display.get('meraki_api_key'):
            api_key = config_display['meraki_api_key']
            config_display['meraki_api_key'] = '****' + api_key[-4:] if len(api_key) > 4 else '****'
        
        context = {
            'form': form,
            'settings': settings_instance,
            'site_rules': site_rules,
            'prefix_filter_rules': prefix_filter_rules,
            'static_config': config_display,
        }
        
        return render(request, 'netbox_meraki/config.html', context)


class SiteNameRuleListView(LoginRequiredMixin, ListView):
    """List all site name rules"""
    model = SiteNameRule
    template_name = 'netbox_meraki/sitenamerule_list.html'
    context_object_name = 'rules'
    paginate_by = 50


class SiteNameRuleCreateView(LoginRequiredMixin, CreateView):
    """Create a new site name rule"""
    model = SiteNameRule
    form_class = SiteNameRuleForm
    template_name = 'netbox_meraki/sitenamerule_form.html'
    success_url = reverse_lazy('plugins:netbox_meraki:config')
    
    def form_valid(self, form):
        messages.success(self.request, f'Site name rule "{form.instance.name}" created successfully.')
        return super().form_valid(form)


class SiteNameRuleUpdateView(LoginRequiredMixin, UpdateView):
    """Edit an existing site name rule"""
    model = SiteNameRule
    form_class = SiteNameRuleForm
    template_name = 'netbox_meraki/sitenamerule_form.html'
    success_url = reverse_lazy('plugins:netbox_meraki:config')
    
    def form_valid(self, form):
        messages.success(self.request, f'Site name rule "{form.instance.name}" updated successfully.')
        return super().form_valid(form)


class SiteNameRuleDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a site name rule"""
    model = SiteNameRule
    template_name = 'netbox_meraki/sitenamerule_confirm_delete.html'
    success_url = reverse_lazy('plugins:netbox_meraki:config')
    
    def delete(self, request, *args, **kwargs):
        rule = self.get_object()
        messages.success(request, f'Site name rule "{rule.name}" deleted successfully.')
        return super().delete(request, *args, **kwargs)


class PrefixFilterRuleListView(LoginRequiredMixin, ListView):
    """List all prefix filter rules"""
    model = PrefixFilterRule
    template_name = 'netbox_meraki/prefixfilterrule_list.html'
    context_object_name = 'rules'
    paginate_by = 50


class PrefixFilterRuleCreateView(LoginRequiredMixin, CreateView):
    """Create a new prefix filter rule"""
    model = PrefixFilterRule
    form_class = PrefixFilterRuleForm
    template_name = 'netbox_meraki/prefixfilterrule_form.html'
    success_url = reverse_lazy('plugins:netbox_meraki:config')
    
    def form_valid(self, form):
        messages.success(self.request, f'Prefix filter rule "{form.instance.name}" created successfully.')
        return super().form_valid(form)


class PrefixFilterRuleUpdateView(LoginRequiredMixin, UpdateView):
    """Edit an existing prefix filter rule"""
    model = PrefixFilterRule
    form_class = PrefixFilterRuleForm
    template_name = 'netbox_meraki/prefixfilterrule_form.html'
    success_url = reverse_lazy('plugins:netbox_meraki:config')
    
    def form_valid(self, form):
        messages.success(self.request, f'Prefix filter rule "{form.instance.name}" updated successfully.')
        return super().form_valid(form)


class PrefixFilterRuleDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a prefix filter rule"""
    model = PrefixFilterRule
    template_name = 'netbox_meraki/prefixfilterrule_confirm_delete.html'
    success_url = reverse_lazy('plugins:netbox_meraki:config')
    
    def delete(self, request, *args, **kwargs):
        rule = self.get_object()
        messages.success(request, f'Prefix filter rule "{rule.name}" deleted successfully.')
        return super().delete(request, *args, **kwargs)


class ReviewDetailView(LoginRequiredMixin, View):
    """View sync review details"""
    
    def get(self, request, pk):
        review = get_object_or_404(SyncReview, pk=pk)
        items = review.items.all()
        
        # Group items by type
        site_items = items.filter(item_type='site')
        device_items = items.filter(item_type='device')
        device_type_items = items.filter(item_type='device_type')
        vlan_items = items.filter(item_type='vlan')
        prefix_items = items.filter(item_type='prefix')
        interface_items = items.filter(item_type='interface')
        ssid_items = items.filter(item_type='ssid')
        
        context = {
            'review': review,
            'items': items,
            'site_items': site_items,
            'device_items': device_items,
            'device_type_items': device_type_items,
            'vlan_items': vlan_items,
            'prefix_items': prefix_items,
            'interface_items': interface_items,
            'ssid_items': ssid_items,
            'sync_log': review.sync_log,
        }
        
        return render(request, 'netbox_meraki/review_detail_new.html', context)
    
    def post(self, request, pk):
        review = get_object_or_404(SyncReview, pk=pk)
        action = request.POST.get('action')
        
        if action == 'approve_all':
            review.items.update(status='approved')
            review.status = 'approved'
            review.items_approved = review.items.count()
            review.save()
            messages.success(request, 'All items approved.')
            
        elif action == 'reject_all':
            review.items.update(status='rejected')
            review.status='rejected'
            review.items_rejected = review.items.count()
            review.save()
            messages.info(request, 'All items rejected.')
            
        elif action == 'apply':
            if review.status not in ['approved', 'partially_approved']:
                messages.error(request, 'Cannot apply changes without approval.')
                return redirect('plugins:netbox_meraki:review_detail', pk=pk)
            
            try:
                review.apply_approved_items()
                messages.success(request, f'Applied {review.items_approved} approved items.')
                return redirect('plugins:netbox_meraki:synclog', pk=review.sync_log.pk)
            except Exception as e:
                messages.error(request, f'Error applying changes: {str(e)}')
        
        return redirect('plugins:netbox_meraki:review_detail', pk=pk)


class ReviewItemActionView(LoginRequiredMixin, View):
    """Approve or reject individual review items"""
    
    def post(self, request, pk, item_pk):
        review = get_object_or_404(SyncReview, pk=pk)
        item = get_object_or_404(ReviewItem, pk=item_pk, review=review)
        action = request.POST.get('action')
        
        if action == 'approve':
            item.status = 'approved'
            item.save()
            review.items_approved = review.items.filter(status='approved').count()
            review.items_rejected = review.items.filter(status='rejected').count()
            
            # Update review status
            if review.items_approved > 0 and review.items_rejected > 0:
                review.status = 'partially_approved'
            elif review.items_approved == review.items_total:
                review.status = 'approved'
            review.save()
            
            messages.success(request, f'Approved: {item.object_name}')
            
        elif action == 'reject':
            item.status = 'rejected'
            item.notes = request.POST.get('notes', '')
            item.save()
            review.items_approved = review.items.filter(status='approved').count()
            review.items_rejected = review.items.filter(status='rejected').count()
            
            # Update review status
            if review.items_rejected == review.items_total:
                review.status = 'rejected'
            elif review.items_approved > 0:
                review.status = 'partially_approved'
            review.save()
            
            messages.info(request, f'Rejected: {item.object_name}')
        
        return redirect('plugins:netbox_meraki:review_detail', pk=pk)


class ReviewItemEditView(LoginRequiredMixin, View):
    """Edit review item data before applying"""
    
    def get(self, request, pk, item_pk):
        review = get_object_or_404(SyncReview, pk=pk)
        item = get_object_or_404(ReviewItem, pk=item_pk, review=review)
        
        # Use editable_data if exists, otherwise proposed_data
        data_to_edit = item.editable_data if item.editable_data else item.proposed_data.copy()
        
        context = {
            'review': review,
            'item': item,
            'data_to_edit': data_to_edit,
        }
        
        return render(request, 'netbox_meraki/review_item_edit.html', context)
    
    def post(self, request, pk, item_pk):
        review = get_object_or_404(SyncReview, pk=pk)
        item = get_object_or_404(ReviewItem, pk=item_pk, review=review)
        
        editable_data = {}
        
        # Common fields based on item type
        if item.item_type == 'site':
            editable_data = {
                'name': request.POST.get('name', ''),
                'slug': request.POST.get('slug', ''),
                'description': request.POST.get('description', ''),
            }
        elif item.item_type == 'device':
            editable_data = {
                'name': request.POST.get('name', ''),
                'serial': request.POST.get('serial', ''),
                'model': request.POST.get('model', ''),
                'manufacturer': request.POST.get('manufacturer', ''),
                'role': request.POST.get('role', ''),
                'site': request.POST.get('site', ''),
                'status': request.POST.get('status', ''),
            }
            # Keep other fields from proposed_data
            for key in item.proposed_data:
                if key not in editable_data:
                    editable_data[key] = item.proposed_data[key]
        elif item.item_type == 'vlan':
            editable_data = {
                'name': request.POST.get('name', ''),
                'vid': request.POST.get('vid', ''),
                'description': request.POST.get('description', ''),
            }
            # Keep other fields
            for key in item.proposed_data:
                if key not in editable_data:
                    editable_data[key] = item.proposed_data[key]
        else:
            # For other types, keep proposed_data and update specific fields
            editable_data = item.proposed_data.copy()
            editable_data['name'] = request.POST.get('name', editable_data.get('name', ''))
            if 'description' in editable_data:
                editable_data['description'] = request.POST.get('description', editable_data.get('description', ''))
        
        # Save editable data
        item.editable_data = editable_data
        item.save()
        
        messages.success(request, f'Updated {item.item_type}: {item.object_name}')
        return redirect('plugins:netbox_meraki:review_detail', pk=pk)


class ReviewListView(LoginRequiredMixin, ListView):
    """List all sync reviews"""
    model = SyncReview
    template_name = 'netbox_meraki/review_list.html'
    context_object_name = 'reviews'
    paginate_by = 50
    ordering = ['-created']


from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


class SyncProgressAPIView(LoginRequiredMixin, View):
    """API endpoint to get sync progress"""
    
    def get(self, request, pk):
        sync_log = get_object_or_404(SyncLog, pk=pk)
        
        data = {
            'status': sync_log.status,
            'progress_percent': sync_log.progress_percent or 0,
            'current_operation': sync_log.current_operation or '',
            'progress_logs': sync_log.progress_logs or [],
        }
        
        return JsonResponse(data)


class SyncCancelAPIView(LoginRequiredMixin, View):
    """API endpoint to cancel a running sync"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, pk):
        sync_log = get_object_or_404(SyncLog, pk=pk)
        
        if sync_log.status == 'running':
            sync_log.request_cancel()
            return JsonResponse({'status': 'success', 'message': 'Cancellation requested'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Sync is not running'}, status=400)


@require_http_methods(["GET"])
def get_networks_for_org(request, org_id):
    """API endpoint to get networks for a specific organization"""
    try:
        sync_service = MerakiSyncService()
        networks = sync_service.client.get_networks(org_id)
        
        network_list = [
            {
                'id': net['id'],
                'name': net['name'],
                'tags': net.get('tags', []),
                'productTypes': net.get('productTypes', [])
            }
            for net in networks
        ]
        
        return JsonResponse({
            'networks': network_list,
            'total': len(network_list)
        })
    except Exception as e:
        logger.error(f"Failed to fetch networks for org {org_id}: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_organizations(request):
    """API endpoint to get all organizations with network counts"""
    try:
        sync_service = MerakiSyncService()
        organizations = sync_service.client.get_organizations()
        
        # Add network count for each organization
        org_list = []
        for org in organizations:
            try:
                networks = sync_service.client.get_networks(org['id'])
                org_data = {
                    'id': org['id'],
                    'name': org['name'],
                    'network_count': len(networks)
                }
                org_list.append(org_data)
            except Exception as e:
                logger.error(f"Failed to get networks for org {org['id']}: {e}")
                org_list.append({
                    'id': org['id'],
                    'name': org['name'],
                    'network_count': 0
                })
        
        return JsonResponse({'organizations': org_list})
    except Exception as e:
        logger.error(f"Failed to fetch organizations: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_sync_progress(request, pk):
    """API endpoint to get real-time sync progress for a specific sync log"""
    try:
        from .models import SyncLog
        
        sync_log = get_object_or_404(SyncLog, pk=pk)
        
        # Get recent progress logs (last 10 entries)
        recent_logs = sync_log.progress_logs[-10:] if sync_log.progress_logs else []
        
        response_data = {
            'id': sync_log.pk,
            'status': sync_log.status,
            'progress_percent': sync_log.progress_percent,
            'current_operation': sync_log.current_operation,
            'devices_synced': sync_log.devices_synced,
            'vlans_synced': sync_log.vlans_synced,
            'prefixes_synced': sync_log.prefixes_synced,
            'networks_synced': sync_log.networks_synced,
            'organizations_synced': sync_log.organizations_synced,
            'recent_logs': recent_logs,
            'is_running': sync_log.status == 'running',
            'cancel_requested': sync_log.cancel_requested,
        }
        
        return JsonResponse(response_data)
    except Exception as e:
        logger.error(f"Failed to fetch sync progress: {e}")
        return JsonResponse({'error': str(e)}, status=500)


class JobHistoryView(LoginRequiredMixin, View):
    """View for displaying all sync jobs (manual and scheduled) with pagination"""
    
    def get(self, request):
        from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
        
        # Get all sync logs ordered by most recent first
        all_logs = SyncLog.objects.all().order_by('-timestamp')
        
        # Apply filters if provided
        status_filter = request.GET.get('status')
        mode_filter = request.GET.get('mode')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        if status_filter and status_filter != 'all':
            all_logs = all_logs.filter(status=status_filter)
        
        if mode_filter and mode_filter != 'all':
            all_logs = all_logs.filter(sync_mode=mode_filter)
        
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d')
                all_logs = all_logs.filter(timestamp__gte=from_date)
            except ValueError:
                pass
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d')
                # Add one day to include the entire end date
                to_date = to_date + timedelta(days=1)
                all_logs = all_logs.filter(timestamp__lt=to_date)
            except ValueError:
                pass
        
        # Pagination
        page = request.GET.get('page', 1)
        per_page = request.GET.get('per_page', 25)
        
        try:
            per_page = int(per_page)
            if per_page not in [10, 25, 50, 100]:
                per_page = 25
        except ValueError:
            per_page = 25
        
        paginator = Paginator(all_logs, per_page)
        
        try:
            logs = paginator.page(page)
        except PageNotAnInteger:
            logs = paginator.page(1)
        except EmptyPage:
            logs = paginator.page(paginator.num_pages)
        
        # Get statistics
        stats = {
            'total': all_logs.count(),
            'success': all_logs.filter(status='success').count(),
            'failed': all_logs.filter(status='failed').count(),
            'pending_review': all_logs.filter(status='pending_review').count(),
            'running': all_logs.filter(status='running').count(),
            'partial': all_logs.filter(status='partial').count(),
            'dry_run': all_logs.filter(status='dry_run').count(),
        }
        
        context = {
            'logs': logs,
            'stats': stats,
            'status_filter': status_filter,
            'mode_filter': mode_filter,
            'date_from': date_from,
            'date_to': date_to,
            'per_page': per_page,
        }
        
        return render(request, 'netbox_meraki/job_history.html', context)


class ScheduledSyncView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """View for managing scheduled syncs using NetBox's native ScheduledJob"""
    
    permission_required = 'extras.view_scheduledjob'
    
    def get(self, request):
        scheduled_jobs = []
        organizations = []
        
        # Try to import ScheduledJob - try multiple paths for different NetBox versions
        can_schedule = False
        import_error_msg = None
        exception_details = []  # Collect all exceptions for debugging
        
        # Debug: Log NetBox version
        try:
            import netbox
            netbox_version = netbox.settings.VERSION
            logger.info(f"NetBox version: {netbox_version}")
            exception_details.append(f"✓ NetBox version: {netbox_version}")
        except Exception as e:
            logger.warning(f"Could not determine NetBox version: {e}")
            exception_details.append(f"⚠ Version check failed: {str(e)}")
        
        try:
            logger.info("Attempting to import ScheduledJob from core.models.jobs...")
            from core.models.jobs import Job as ScheduledJob
            logger.info("✓ Successfully imported ScheduledJob from core.models.jobs")
            exception_details.append("✓ Import: core.models.jobs.Job")
            
            from .jobs import MerakiSyncJob
            logger.info("✓ Successfully imported MerakiSyncJob")
            exception_details.append("✓ Import: MerakiSyncJob")
            can_schedule = True
            
            # In NetBox 4.4+, filter by name instead of job_class
            try:
                logger.info("Fetching scheduled Meraki jobs...")
                scheduled_jobs = ScheduledJob.objects.filter(
                    name__icontains='Meraki',
                    interval__isnull=False  # Only recurring jobs
                ).order_by('-created')
                logger.info(f"Found {len(scheduled_jobs)} scheduled jobs")
                exception_details.append(f"✓ Query: Found {len(scheduled_jobs)} jobs")
            except Exception as query_error:
                logger.error(f"Error querying scheduled jobs: {query_error}", exc_info=True)
                messages.warning(request, f'Error loading scheduled jobs: {str(query_error)}')
                exception_details.append(f"✗ Query error: {str(query_error)}")
                # Keep can_schedule=True since imports worked
                
        except ImportError as e:
            # Try alternate import path
            import_error_msg = str(e)
            logger.warning(f"✗ Failed to import from core.models.jobs: {e}")
            exception_details.append(f"✗ core.models.jobs import failed: {str(e)}")
            
            try:
                logger.info("Attempting to import ScheduledJob from extras.models...")
                from extras.models import ScheduledJob
                logger.info("✓ Successfully imported ScheduledJob from extras.models")
                exception_details.append("✓ Import: extras.models.ScheduledJob")
                
                from .jobs import MerakiSyncJob
                can_schedule = True
                exception_details.append("✓ Import: MerakiSyncJob (alternate path)")
                
                # In NetBox 4.4+, filter by name instead of job_class
                try:
                    scheduled_jobs = ScheduledJob.objects.filter(
                        name__icontains='Meraki',
                        interval__isnull=False
                    ).order_by('-created')
                    exception_details.append(f"✓ Query: Found {len(scheduled_jobs)} jobs (alternate)")
                except Exception as query_error:
                    logger.error(f"Error querying scheduled jobs: {query_error}", exc_info=True)
                    exception_details.append(f"✗ Query error (alternate): {str(query_error)}")
                    # Keep can_schedule=True since imports worked
                    
            except ImportError as e2:
                logger.error(f"✗ Failed to import from extras.models: {e2}")
                logger.error(f"SCHEDULING DISABLED - Import errors: core.models ({e}) / extras.models ({e2})")
                exception_details.append(f"✗ extras.models import failed: {str(e2)}")
                exception_details.append("✗ SCHEDULING DISABLED - All import paths failed")
                can_schedule = False
        except Exception as e:
            logger.error(f"Unexpected error in ScheduledSyncView.get(): {e}", exc_info=True)
            exception_details.append(f"✗ Unexpected error: {type(e).__name__}: {str(e)}")
            # Don't change can_schedule here - it may have been set to True already
        
        # Fetch organizations for dropdown even if scheduling not available
        try:
            from .sync_service import MerakiSyncService
            sync_service = MerakiSyncService()
            organizations = sync_service.client.get_organizations()
            logger.info(f"Loaded {len(organizations)} organizations")
        except Exception as e:
            logger.error(f"Failed to fetch organizations: {e}")
            messages.warning(request, f'Could not load organizations: {str(e)}')
        
        form = ScheduledSyncForm(organizations=organizations)
        
        logger.info(f"DEBUG: can_schedule = {can_schedule}")
        logger.info(f"DEBUG: scheduled_jobs count = {len(scheduled_jobs)}")
        
        context = {
            'scheduled_jobs': scheduled_jobs,
            'form': form,
            'can_schedule': can_schedule,
            'exception_details': exception_details,  # Pass to template for debugging
        }
        
        return render(request, 'netbox_meraki/scheduled_sync.html', context)
    
    def post(self, request):
        # Fetch organizations for form validation
        organizations = []
        try:
            from .sync_service import MerakiSyncService
            sync_service = MerakiSyncService()
            organizations = sync_service.client.get_organizations()
        except Exception as e:
            logger.error(f"Failed to fetch organizations: {e}")
        
        form = ScheduledSyncForm(request.POST, organizations=organizations)
        
        logger.info(f"Form is_valid: {form.is_valid()}")
        if not form.is_valid():
            logger.error(f"Form validation errors: {form.errors}")
        
        if form.is_valid():
            try:
                from .jobs import MerakiSyncJob
                
                # Get interval
                interval = form.cleaned_data['interval']
                if interval == 'custom':
                    interval_minutes = form.cleaned_data['custom_interval']
                elif interval == '0':
                    interval_minutes = None  # Run once
                else:
                    interval_minutes = int(interval)
                
                # Build job kwargs
                job_kwargs = {
                    'sync_mode': form.cleaned_data['sync_mode'],
                }
                
                if form.cleaned_data.get('organization_id'):
                    job_kwargs['organization_id'] = form.cleaned_data['organization_id']
                
                # Handle network selection - get from POST directly since we build checkboxes dynamically
                network_ids = request.POST.getlist('network_ids')
                sync_all_networks = form.cleaned_data.get('sync_all_networks', True)
                
                # Only add network_ids to job kwargs if specific networks are selected
                if not sync_all_networks and network_ids:
                    # Filter out empty strings and ensure we have valid IDs
                    filtered_ids = [nid.strip() for nid in network_ids if nid and nid.strip()]
                    if filtered_ids:
                        job_kwargs['network_ids'] = filtered_ids
                        logger.info(f"Scheduling job with {len(filtered_ids)} specific networks")
                    else:
                        logger.warning("Network IDs list is empty after filtering, will sync all networks")
                # If sync_all_networks is True or no valid network IDs, don't add network_ids (means sync all)
                
                # Debug logging
                logger.info(f"=== DEBUG: Job kwargs prepared ===")
                logger.info(f"sync_mode: {job_kwargs.get('sync_mode')}")
                logger.info(f"organization_id: {job_kwargs.get('organization_id')}")
                logger.info(f"network_ids: {job_kwargs.get('network_ids')}")
                logger.info(f"network_ids type: {type(job_kwargs.get('network_ids'))}")
                
                # Get scheduled time if provided
                scheduled_time = form.cleaned_data.get('scheduled_time')
                
                # Use enqueue_once() for scheduled jobs or enqueue() for run once
                if interval_minutes is None:
                    # Run once immediately or at scheduled time
                    # Pass sync parameters directly as kwargs (not nested)
                    enqueue_kwargs = {
                        'name': form.cleaned_data['name'],
                        'user': request.user,
                        **job_kwargs  # Unpack job_kwargs directly into enqueue call
                    }
                    if scheduled_time:
                        enqueue_kwargs['schedule_at'] = scheduled_time
                    
                    logger.info(f"Calling enqueue with: {enqueue_kwargs}")
                    try:
                        job = MerakiSyncJob.enqueue(**enqueue_kwargs)
                    except TypeError as te:
                        logger.error(f"TypeError during enqueue: {te}", exc_info=True)
                        logger.error(f"enqueue_kwargs: {enqueue_kwargs}")
                        raise
                    except Exception as e:
                        logger.error(f"Unexpected error during enqueue: {e}", exc_info=True)
                        raise
                    
                    if scheduled_time:
                        messages.success(
                            request,
                            f'Job "{form.cleaned_data["name"]}" scheduled to run at {scheduled_time.strftime("%Y-%m-%d %H:%M")}.'
                        )
                    else:
                        messages.success(
                            request,
                            f'Job "{form.cleaned_data["name"]}" queued successfully and will run immediately.'
                        )
                else:
                    # Schedule recurring job
                    # Pass sync parameters directly as kwargs (not nested)
                    enqueue_kwargs = {
                        'interval': interval_minutes,
                        'name': form.cleaned_data['name'],
                        'user': request.user,
                        **job_kwargs  # Unpack job_kwargs directly into enqueue_once call
                    }
                    if scheduled_time:
                        enqueue_kwargs['schedule_at'] = scheduled_time
                    
                    logger.info(f"Calling enqueue_once with: {enqueue_kwargs}")
                    try:
                        job = MerakiSyncJob.enqueue_once(**enqueue_kwargs)
                    except TypeError as te:
                        logger.error(f"TypeError during enqueue_once: {te}", exc_info=True)
                        logger.error(f"enqueue_kwargs: {enqueue_kwargs}")
                        raise
                    except Exception as e:
                        logger.error(f"Unexpected error during enqueue_once: {e}", exc_info=True)
                        raise
                    
                    # Build description for the job
                    mode_label = form.cleaned_data['sync_mode'].replace('_', ' ').title()
                    description = f"Mode: {mode_label}"
                    if job_kwargs.get('organization_id'):
                        description += f" | Org: {job_kwargs['organization_id']}"
                    if job_kwargs.get('network_ids'):
                        description += f" | Networks: {len(job_kwargs['network_ids'])}"
                    
                    # In NetBox 4.4.7, enqueue_once() returns the Job instance directly
                    # Update job properties (the job object itself is the scheduled job)
                    if job:
                        try:
                            # Try to access scheduled_job attribute (older NetBox versions)
                            if hasattr(job, 'scheduled_job') and job.scheduled_job:
                                job.scheduled_job.description = description
                                job.scheduled_job.enabled = form.cleaned_data['enabled']
                                job.scheduled_job.save()
                            else:
                                # In NetBox 4.4.7+, the job IS the scheduled job
                                job.description = description
                                job.enabled = form.cleaned_data['enabled']
                                job.save()
                        except AttributeError as e:
                            logger.warning(f"Could not set job properties: {e}")
                    
                    # Build success message
                    success_msg = f'Scheduled job "{form.cleaned_data["name"]}" created successfully. '
                    if scheduled_time:
                        success_msg += f'First run: {scheduled_time.strftime("%Y-%m-%d %H:%M")}. '
                    success_msg += f'Runs every {interval_minutes} minutes.'
                    
                    messages.success(request, success_msg)
                
                return redirect('plugins:netbox_meraki:scheduled_sync')
                
            except ImportError:
                messages.error(request, 'Scheduled sync requires NetBox 4.0 or higher.')
                return redirect('plugins:netbox_meraki:sync')
            except Exception as e:
                messages.error(request, f'Failed to create scheduled job: {str(e)}')
                logger.error(f"Failed to create scheduled job: {e}", exc_info=True)
        
        # If form invalid, reload page with errors
        can_schedule = False
        scheduled_jobs = []
        try:
            from core.models.jobs import Job as ScheduledJob
            from .jobs import MerakiSyncJob
            can_schedule = True
            # In NetBox 4.4+, filter by name instead of job_class
            scheduled_jobs = ScheduledJob.objects.filter(
                name__icontains='Meraki',
                interval__isnull=False
            ).order_by('-created')
        except ImportError:
            try:
                from extras.models import ScheduledJob
                from .jobs import MerakiSyncJob
                can_schedule = True
                scheduled_jobs = ScheduledJob.objects.filter(
                    name__icontains='Meraki',
                    interval__isnull=False
                ).order_by('-created')
            except:
                can_schedule = False
        except:
            pass
        
        context = {
            'scheduled_jobs': scheduled_jobs,
            'form': form,
            'can_schedule': can_schedule,
        }
        
        return render(request, 'netbox_meraki/scheduled_sync.html', context)


class ScheduledSyncDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Delete a scheduled sync job"""
    
    permission_required = 'extras.delete_scheduledjob'
    
    def post(self, request, pk):
        try:
            from core.models.jobs import Job as ScheduledJob
            
            job = get_object_or_404(ScheduledJob, pk=pk)
            job_name = job.name
            job.delete()
            
            messages.success(request, f'Scheduled job "{job_name}" deleted successfully.')
        except ImportError:
            messages.error(request, 'NetBox ScheduledJob model not available.')
        except Exception as e:
            messages.error(request, f'Failed to delete scheduled job: {str(e)}')
        
        return redirect('plugins:netbox_meraki:scheduled_sync')


class ScheduledSyncToggleView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Toggle enable/disable status of a scheduled job"""
    
    permission_required = 'extras.change_scheduledjob'
    
    def post(self, request, pk):
        try:
            from core.models.jobs import Job as ScheduledJob
            
            job = get_object_or_404(ScheduledJob, pk=pk)
            job.enabled = not job.enabled
            job.save()
            
            status = "enabled" if job.enabled else "disabled"
            messages.success(request, f'Scheduled job "{job.name}" {status}.')
        except ImportError:
            messages.error(request, 'NetBox ScheduledJob model not available.')
        except Exception as e:
            messages.error(request, f'Failed to toggle scheduled job: {str(e)}')
        
        return redirect('plugins:netbox_meraki:scheduled_sync')


