"""
Forms for NetBox Meraki plugin
"""
from django import forms
from .models import PluginSettings, SiteNameRule


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
            'enable_scheduled_sync',
            'sync_interval_minutes',
            'scheduled_sync_mode',
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
            'enable_scheduled_sync': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'scheduled_sync_mode': forms.Select(attrs={'class': 'form-select'}),
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
