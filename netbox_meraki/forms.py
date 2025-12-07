"""
Forms for NetBox Meraki plugin
"""
from django import forms
from .models import PluginSettings, SiteNameRule, PrefixFilterRule, ScheduledSyncTask


class PluginSettingsForm(forms.ModelForm):
    """Form for editing plugin settings"""
    
    class Meta:
        model = PluginSettings
        fields = [
            'mx_device_role',
            'ms_device_role',
            'mr_device_role',
            'mg_device_role',
            'mv_device_role',
            'mt_device_role',
            'default_device_role',
            'auto_create_device_roles',
            'sync_mode',
            'device_name_transform',
            'site_name_transform',
            'vlan_name_transform',
            'ssid_name_transform',
            'site_tags',
            'device_tags',
            'vlan_tags',
            'prefix_tags',
            'process_unmatched_sites',
            'enable_scheduled_sync',
            'sync_interval_minutes',
            'scheduled_sync_mode',
            'enable_api_throttling',
            'api_requests_per_second',
            'enable_multithreading',
            'max_worker_threads',
        ]
        widgets = {
            'sync_interval_minutes': forms.NumberInput(attrs={'min': 5, 'step': 5, 'class': 'form-control'}),
            'mx_device_role': forms.TextInput(attrs={'class': 'form-control'}),
            'ms_device_role': forms.TextInput(attrs={'class': 'form-control'}),
            'mr_device_role': forms.TextInput(attrs={'class': 'form-control'}),
            'mg_device_role': forms.TextInput(attrs={'class': 'form-control'}),
            'mv_device_role': forms.TextInput(attrs={'class': 'form-control'}),
            'mt_device_role': forms.TextInput(attrs={'class': 'form-control'}),
            'default_device_role': forms.TextInput(attrs={'class': 'form-control'}),
            'auto_create_device_roles': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sync_mode': forms.Select(attrs={'class': 'form-select'}),
            'device_name_transform': forms.Select(attrs={'class': 'form-select'}),
            'site_name_transform': forms.Select(attrs={'class': 'form-select'}),
            'vlan_name_transform': forms.Select(attrs={'class': 'form-select'}),
            'ssid_name_transform': forms.Select(attrs={'class': 'form-select'}),
            'site_tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Meraki,Production'}),
            'device_tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Meraki,Network-Device'}),
            'vlan_tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Meraki,VLAN'}),
            'prefix_tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Meraki,Subnet'}),
            'process_unmatched_sites': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_scheduled_sync': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'scheduled_sync_mode': forms.Select(attrs={'class': 'form-select'}),
            'enable_api_throttling': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'api_requests_per_second': forms.NumberInput(attrs={'min': 1, 'max': 10, 'class': 'form-control'}),
            'enable_multithreading': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'max_worker_threads': forms.NumberInput(attrs={'min': 1, 'max': 10, 'class': 'form-control'}),
        }
        help_texts = {
            'mx_device_role': 'Device role for MX (Security Appliance) devices',
            'ms_device_role': 'Device role for MS (Switch) devices',
            'mr_device_role': 'Device role for MR (Wireless AP) devices',
            'mg_device_role': 'Device role for MG (Cellular Gateway) devices',
            'mv_device_role': 'Device role for MV (Camera) devices',
            'mt_device_role': 'Device role for MT (Sensor) devices',
            'default_device_role': 'Fallback role for unknown device types',
        }


class SiteNameRuleForm(forms.ModelForm):
    """Form for creating/editing site name rules"""
    
    class Meta:
        model = SiteNameRule
        fields = [
            'name',
            'regex_pattern',
            'site_name_template',
            'priority',
            'enabled',
            'description',
        ]
        help_texts = {
            'regex_pattern': 'Regular expression to match network names (e.g., "^asia-south-.*-oil$")',
            'site_name_template': 'Use {0}, {1} for regex groups or {network_name} for full name',
        }
        widgets = {
            'regex_pattern': forms.TextInput(attrs={'placeholder': '^asia-south-(.+)-oil$'}),
            'site_name_template': forms.TextInput(attrs={'placeholder': 'Asia South - {0} - Oil'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class PrefixFilterRuleForm(forms.ModelForm):
    """Form for creating/editing prefix filter rules"""
    
    class Meta:
        model = PrefixFilterRule
        fields = [
            'name',
            'filter_type',
            'prefix_pattern',
            'prefix_length_filter',
            'min_prefix_length',
            'max_prefix_length',
            'priority',
            'enabled',
            'description',
        ]
        help_texts = {
            'prefix_pattern': 'Prefix pattern to match (e.g., "192.168.0.0/16", "10.0.0.0/8"). Leave blank to match all.',
            'min_prefix_length': 'Required for "greater", "less", and "range" filters',
            'max_prefix_length': 'Required for "range" filter only',
        }
        widgets = {
            'prefix_pattern': forms.TextInput(attrs={'placeholder': '192.168.0.0/16', 'class': 'form-control'}),
            'min_prefix_length': forms.NumberInput(attrs={'min': 1, 'max': 128, 'class': 'form-control'}),
            'max_prefix_length': forms.NumberInput(attrs={'min': 1, 'max': 128, 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'filter_type': forms.Select(attrs={'class': 'form-select'}),
            'prefix_length_filter': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class ScheduledSyncTaskForm(forms.ModelForm):
    """Form for creating/editing scheduled sync tasks"""
    
    class Meta:
        model = ScheduledSyncTask
        fields = [
            'name',
            'sync_mode',
            'selected_networks',
            'sync_organizations',
            'sync_sites',
            'sync_devices',
            'sync_vlans',
            'sync_prefixes',
            'cleanup_orphaned',
            'frequency',
            'scheduled_datetime',
            'enabled',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'My Daily Sync'}),
            'sync_mode': forms.Select(attrs={'class': 'form-select'}),
            'selected_networks': forms.HiddenInput(),
            'sync_organizations': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sync_sites': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sync_devices': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sync_vlans': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sync_prefixes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cleanup_orphaned': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'frequency': forms.Select(attrs={'class': 'form-select'}),
            'scheduled_datetime': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'name': 'A descriptive name for this scheduled task',
            'sync_mode': 'Choose whether to sync all networks or select specific ones',
            'frequency': 'How often should this task run',
            'scheduled_datetime': 'When should this task first run (and repeat based on frequency)',
        }


