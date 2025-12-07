"""
Views for NetBox Meraki plugin
"""
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
    SyncReview, ReviewItem, ScheduledSyncTask
)
from .forms import (
    PluginSettingsForm, SiteNameRuleForm, PrefixFilterRuleForm,
    ScheduledSyncTaskForm
)


logger = logging.getLogger('netbox_meraki')


class DashboardView(LoginRequiredMixin, View):
    """Dashboard view showing sync status and recent logs"""
    
    def get(self, request):
        recent_logs = SyncLog.objects.all()[:10]
        
        latest_sync = SyncLog.objects.filter(status='success').first()
        
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
        network_ids = request.POST.getlist('network_ids[]')
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
        # Django forms expect 'false' string or absence for False boolean values
        post_data = request.POST.copy()
        
        # For boolean fields, if not present in POST, it means unchecked
        # We need to ensure they're not in the data so the form treats them as False
        checkbox_fields = [
            'process_unmatched_sites',
            'auto_create_device_roles',
            'enable_scheduled_sync',
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
            sync_log.cancel_requested = True
            sync_log.save()
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
        
        return JsonResponse({'networks': network_list})
    except Exception as e:
        logger.error(f"Failed to fetch networks for org {org_id}: {e}")
        return JsonResponse({'error': str(e)}, status=500)


class ScheduledSyncListView(LoginRequiredMixin, View):
    """View for listing and managing scheduled sync tasks"""
    
    def get(self, request):
        tasks = ScheduledSyncTask.objects.all().order_by('next_run', 'scheduled_datetime')
        
        # Get available networks for the create form
        try:
            sync_service = MerakiSyncService()
            organizations = sync_service.client.get_organizations()
            
            available_networks = {}
            for org in organizations:
                networks = sync_service.client.get_networks(org['id'])
                available_networks[org['name']] = [
                    {'id': net['id'], 'name': net['name']}
                    for net in networks
                ]
        except Exception as e:
            logger.error(f"Failed to fetch networks: {e}")
            available_networks = {}
        
        form = ScheduledSyncTaskForm()
        
        context = {
            'tasks': tasks,
            'form': form,
            'available_networks': available_networks,
        }
        
        return render(request, 'netbox_meraki/scheduled_sync.html', context)


class ScheduledSyncTaskCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Create a new scheduled sync task"""
    
    permission_required = 'dcim.add_device'
    
    def post(self, request):
        # Handle checkbox fields
        post_data = request.POST.copy()
        checkbox_fields = [
            'sync_organizations', 'sync_sites', 'sync_devices',
            'sync_vlans', 'sync_prefixes', 'cleanup_orphaned', 'enabled'
        ]
        for field in checkbox_fields:
            if field not in request.POST:
                post_data[field] = ''
        
        # Parse selected networks from JSON
        if 'selected_networks' in post_data:
            try:
                post_data['selected_networks'] = json.loads(post_data['selected_networks'])
            except json.JSONDecodeError:
                post_data['selected_networks'] = []
        
        form = ScheduledSyncTaskForm(post_data)
        
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user.username
            
            # Calculate next run based on frequency and scheduled datetime
            task.next_run = task.scheduled_datetime
            
            task.save()
            
            messages.success(
                request,
                f'Scheduled task "{task.name}" created successfully. '
                f'Next run: {task.next_run.strftime("%Y-%m-%d %H:%M")}'
            )
            return redirect('plugins:netbox_meraki:scheduled_sync')
        
        # If form is invalid, reload the page with errors
        tasks = ScheduledSyncTask.objects.all()
        
        try:
            sync_service = MerakiSyncService()
            organizations = sync_service.client.get_organizations()
            available_networks = {}
            for org in organizations:
                networks = sync_service.client.get_networks(org['id'])
                available_networks[org['name']] = [
                    {'id': net['id'], 'name': net['name']}
                    for net in networks
                ]
        except Exception:
            available_networks = {}
        
        context = {
            'tasks': tasks,
            'form': form,
            'available_networks': available_networks,
        }
        
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
        
        return render(request, 'netbox_meraki/scheduled_sync.html', context)


class ScheduledSyncTaskEditView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Edit an existing scheduled sync task"""
    
    permission_required = 'dcim.change_device'
    
    def get(self, request, pk):
        task = get_object_or_404(ScheduledSyncTask, pk=pk)
        
        # Get available networks
        try:
            sync_service = MerakiSyncService()
            organizations = sync_service.client.get_organizations()
            available_networks = {}
            for org in organizations:
                networks = sync_service.client.get_networks(org['id'])
                available_networks[org['name']] = [
                    {'id': net['id'], 'name': net['name']}
                    for net in networks
                ]
        except Exception:
            available_networks = {}
        
        form = ScheduledSyncTaskForm(instance=task)
        
        context = {
            'task': task,
            'form': form,
            'available_networks': available_networks,
        }
        
        return render(request, 'netbox_meraki/scheduled_task_edit.html', context)
    
    def post(self, request, pk):
        task = get_object_or_404(ScheduledSyncTask, pk=pk)
        
        # Handle checkbox fields
        post_data = request.POST.copy()
        checkbox_fields = [
            'sync_organizations', 'sync_sites', 'sync_devices',
            'sync_vlans', 'sync_prefixes', 'cleanup_orphaned', 'enabled'
        ]
        for field in checkbox_fields:
            if field not in request.POST:
                post_data[field] = ''
        
        # Parse selected networks from JSON
        if 'selected_networks' in post_data:
            try:
                post_data['selected_networks'] = json.loads(post_data['selected_networks'])
            except json.JSONDecodeError:
                post_data['selected_networks'] = []
        
        form = ScheduledSyncTaskForm(post_data, instance=task)
        
        if form.is_valid():
            task = form.save(commit=False)
            
            # Recalculate next run if schedule changed
            if task.scheduled_datetime != task.next_run:
                task.next_run = task.scheduled_datetime
            
            task.save()
            
            messages.success(request, f'Task "{task.name}" updated successfully.')
            return redirect('plugins:netbox_meraki:scheduled_sync')
        
        # If form is invalid, show errors
        try:
            sync_service = MerakiSyncService()
            organizations = sync_service.client.get_organizations()
            available_networks = {}
            for org in organizations:
                networks = sync_service.client.get_networks(org['id'])
                available_networks[org['name']] = [
                    {'id': net['id'], 'name': net['name']}
                    for net in networks
                ]
        except Exception:
            available_networks = {}
        
        context = {
            'task': task,
            'form': form,
            'available_networks': available_networks,
        }
        
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
        
        return render(request, 'netbox_meraki/scheduled_task_edit.html', context)


class ScheduledSyncTaskToggleView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Toggle enable/disable status of a scheduled task"""
    
    permission_required = 'dcim.change_device'
    
    def post(self, request, pk):
        task = get_object_or_404(ScheduledSyncTask, pk=pk)
        task.enabled = not task.enabled
        task.save()
        
        status = "enabled" if task.enabled else "disabled"
        messages.success(request, f'Task "{task.name}" {status}.')
        
        return redirect('plugins:netbox_meraki:scheduled_sync')


class ScheduledSyncTaskDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Delete a scheduled sync task"""
    
    permission_required = 'dcim.delete_device'
    
    def post(self, request, pk):
        task = get_object_or_404(ScheduledSyncTask, pk=pk)
        task_name = task.name
        task.delete()
        
        messages.success(request, f'Task "{task_name}" deleted successfully.')
        return redirect('plugins:netbox_meraki:scheduled_sync')

