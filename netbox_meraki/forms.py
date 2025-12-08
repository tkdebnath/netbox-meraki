"""Forms for NetBox Meraki plugin"""
from django import forms
from django.core.exceptions import ValidationError
from .models import PluginSettings, SiteNameRule, PrefixFilterRule


class ScheduledSyncForm(forms.Form):
    """Form for scheduling a Meraki sync using NetBox's native ScheduledJob"""
    
    name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Daily Meraki Sync'
        }),
        help_text='Descriptive name for this scheduled job'
    )
    
    interval = forms.ChoiceField(
        choices=[
            ('0', 'Run Once'),
            ('custom', 'Custom Interval'),
            ('60', 'Hourly'),
            ('360', 'Every 6 Hours'),
            ('720', 'Every 12 Hours'),
            ('1440', 'Daily'),
            ('10080', 'Weekly'),
        ],
        initial='1440',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='How often the sync should run'
    )
    
    custom_interval = forms.IntegerField(
        required=False,
        min_value=5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Minutes',
            'min': '5'
        }),
        help_text='Custom interval in minutes (minimum 5)'
    )
    
    sync_mode = forms.ChoiceField(
        choices=[
            ('auto', 'Auto Sync - Apply changes immediately'),
            ('review', 'Sync with Review - Stage for approval'),
            ('dry_run', 'Dry Run - Preview only'),
        ],
        initial='review',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Sync mode for scheduled execution'
    )
    
    organization_id = forms.ChoiceField(
        required=False,
        choices=[('', 'All Organizations')],
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'organization_id'
        }),
        help_text='Optional: Specific organization to sync'
    )
    
    network_ids = forms.MultipleChoiceField(
        required=False,
        choices=[],
        widget=forms.CheckboxSelectMultiple(attrs={
            'style': 'display: none;'  # Hidden, we build checkboxes dynamically in JavaScript
        }),
        help_text='Optional: Specific networks to sync'
    )
    
    sync_all_networks = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'sync_all_networks_scheduled'}),
        help_text='Sync all networks in organization'
    )
    
    enabled = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Enable this scheduled job'
    )
    
    def __init__(self, *args, **kwargs):
        organizations = kwargs.pop('organizations', [])
        super().__init__(*args, **kwargs)
        
        # Set organization choices
        org_choices = [('', 'All Organizations')]
        org_choices.extend([(org['id'], org['name']) for org in organizations])
        self.fields['organization_id'].choices = org_choices
    
    def clean(self):
        cleaned_data = super().clean()
        interval = cleaned_data.get('interval')
        custom_interval = cleaned_data.get('custom_interval')
        
        if interval == 'custom' and not custom_interval:
            raise ValidationError({
                'custom_interval': 'Custom interval is required when "Custom Interval" is selected'
            })
        
        if interval == 'custom' and custom_interval and custom_interval < 5:
            raise ValidationError({
                'custom_interval': 'Interval must be at least 5 minutes'
            })
        
        return cleaned_data


class PluginSettingsForm(forms.ModelForm):
    
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


