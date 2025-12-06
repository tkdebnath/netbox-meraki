from django.db import models
from django.urls import reverse
from django.core.exceptions import ValidationError
import re


class PluginSettings(models.Model):
    """Plugin configuration settings"""
    
    # Device Role Mappings for different Meraki product types
    mx_device_role = models.CharField(
        max_length=100,
        default='Security Appliance',
        verbose_name='MX Device Role',
        help_text='Device role for MX (Security Appliance) devices'
    )
    ms_device_role = models.CharField(
        max_length=100,
        default='Switch',
        verbose_name='MS Device Role',
        help_text='Device role for MS (Switch) devices'
    )
    mr_device_role = models.CharField(
        max_length=100,
        default='Wireless AP',
        verbose_name='MR Device Role',
        help_text='Device role for MR (Wireless AP) devices'
    )
    mg_device_role = models.CharField(
        max_length=100,
        default='Cellular Gateway',
        verbose_name='MG Device Role',
        help_text='Device role for MG (Cellular Gateway) devices'
    )
    mv_device_role = models.CharField(
        max_length=100,
        default='Camera',
        verbose_name='MV Device Role',
        help_text='Device role for MV (Camera) devices'
    )
    mt_device_role = models.CharField(
        max_length=100,
        default='Sensor',
        verbose_name='MT Device Role',
        help_text='Device role for MT (Sensor) devices'
    )
    default_device_role = models.CharField(
        max_length=100,
        default='Network Device',
        verbose_name='Default Device Role',
        help_text='Default device role for unknown product types'
    )
    
    # Other settings
    auto_create_device_roles = models.BooleanField(
        default=True,
        help_text='Automatically create device roles if they do not exist'
    )
    sync_mode = models.CharField(
        max_length=20,
        choices=[
            ('auto', 'Auto Sync'),
            ('review', 'Sync with Review'),
            ('dry_run', 'Dry Run Only'),
        ],
        default='review',
        verbose_name='Default Sync Mode',
        help_text='Default synchronization mode: Auto (immediate), Review (requires approval), or Dry Run (preview only)'
    )
    
    class Meta:
        verbose_name = 'Plugin Settings'
        verbose_name_plural = 'Plugin Settings'
    
    def __str__(self):
        return "Meraki Plugin Settings"
    
    @classmethod
    def get_settings(cls):
        """Get or create settings instance"""
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings
    
    def get_device_role_for_product(self, product_type: str) -> str:
        """Get device role name for a Meraki product type"""
        if not product_type:
            return self.default_device_role
        
        product_prefix = product_type[:2].upper() if len(product_type) >= 2 else ''
        
        role_mapping = {
            'MX': self.mx_device_role,
            'MS': self.ms_device_role,
            'MR': self.mr_device_role,
            'MG': self.mg_device_role,
            'MV': self.mv_device_role,
            'MT': self.mt_device_role,
        }
        
        return role_mapping.get(product_prefix, self.default_device_role)


class SiteNameRule(models.Model):
    """Rules for transforming Meraki network names to NetBox site names"""
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text='Descriptive name for this rule'
    )
    regex_pattern = models.CharField(
        max_length=500,
        verbose_name='Regex Pattern',
        help_text='Regular expression pattern to match network names (e.g., "asia-south-.*-oil")'
    )
    site_name_template = models.CharField(
        max_length=200,
        verbose_name='Site Name Template',
        help_text='Template for site name. Use {0}, {1}, etc. for regex groups, or {network_name} for full name'
    )
    priority = models.IntegerField(
        default=100,
        help_text='Rule priority (lower values are evaluated first)'
    )
    enabled = models.BooleanField(
        default=True,
        help_text='Enable or disable this rule'
    )
    description = models.TextField(
        blank=True,
        help_text='Optional description of what this rule does'
    )
    
    class Meta:
        ordering = ['priority', 'name']
        verbose_name = 'Site Name Rule'
        verbose_name_plural = 'Site Name Rules'
    
    def __str__(self):
        return f"{self.name} (Priority: {self.priority})"
    
    def clean(self):
        """Validate regex pattern"""
        try:
            re.compile(self.regex_pattern)
        except re.error as e:
            raise ValidationError({
                'regex_pattern': f'Invalid regular expression: {str(e)}'
            })
    
    def apply(self, network_name: str) -> str:
        """Apply this rule to a network name"""
        if not self.enabled:
            return network_name
        
        try:
            match = re.match(self.regex_pattern, network_name)
            if match:
                # Replace numbered groups {0}, {1}, etc.
                result = self.site_name_template
                for i, group in enumerate(match.groups()):
                    result = result.replace(f'{{{i}}}', group or '')
                
                # Replace named placeholders
                result = result.replace('{network_name}', network_name)
                
                return result.strip()
        except Exception as e:
            logger.error(f"Error applying site name rule {self.name}: {e}")
        
        return network_name
    
    @classmethod
    def transform_network_name(cls, network_name: str) -> str:
        """Apply all enabled rules to transform a network name"""
        rules = cls.objects.filter(enabled=True).order_by('priority')
        
        for rule in rules:
            transformed = rule.apply(network_name)
            if transformed != network_name:
                logger.info(f"Applied rule '{rule.name}': '{network_name}' -> '{transformed}'")
                return transformed
        
        return network_name


class SyncLog(models.Model):
    """Track synchronization history"""
    
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('success', 'Success'),
            ('partial', 'Partial Success'),
            ('failed', 'Failed'),
            ('running', 'Running'),
            ('dry_run', 'Dry Run'),
            ('pending_review', 'Pending Review'),
        ]
    )
    message = models.TextField(blank=True)
    organizations_synced = models.IntegerField(default=0)
    networks_synced = models.IntegerField(default=0)
    devices_synced = models.IntegerField(default=0)
    vlans_synced = models.IntegerField(default=0)
    prefixes_synced = models.IntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    sync_mode = models.CharField(
        max_length=20,
        default='auto',
        choices=[
            ('auto', 'Auto Sync'),
            ('review', 'Sync with Review'),
            ('dry_run', 'Dry Run'),
        ]
    )
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Sync Log'
        verbose_name_plural = 'Sync Logs'
    
    def __str__(self):
        return f"Sync {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {self.status}"
    
    def get_absolute_url(self):
        return reverse('plugins:netbox_meraki:synclog', args=[self.pk])


class SyncReview(models.Model):
    """Review session for sync operations"""
    
    sync_log = models.OneToOneField(
        SyncLog,
        on_delete=models.CASCADE,
        related_name='review'
    )
    created = models.DateTimeField(auto_now_add=True)
    reviewed = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Review'),
            ('approved', 'Approved'),
            ('partially_approved', 'Partially Approved'),
            ('rejected', 'Rejected'),
            ('applied', 'Applied'),
        ],
        default='pending'
    )
    items_total = models.IntegerField(default=0)
    items_approved = models.IntegerField(default=0)
    items_rejected = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created']
        verbose_name = 'Sync Review'
        verbose_name_plural = 'Sync Reviews'
    
    def __str__(self):
        return f"Review for Sync {self.sync_log.id} - {self.status}"
    
    def get_absolute_url(self):
        return reverse('plugins:netbox_meraki:review_detail', args=[self.pk])
    
    def apply_approved_items(self):
        """Apply all approved review items"""
        from .sync_service import MerakiSyncService
        
        approved_items = self.items.filter(status='approved')
        service = MerakiSyncService()
        
        for item in approved_items:
            try:
                service.apply_review_item(item)
                item.status = 'applied'
                item.save()
            except Exception as e:
                item.status = 'failed'
                item.error_message = str(e)
                item.save()
        
        self.status = 'applied'
        self.save()


class ReviewItem(models.Model):
    """Individual item in a sync review"""
    
    ITEM_TYPES = [
        ('site', 'Site'),
        ('device', 'Device'),
        ('vlan', 'VLAN'),
        ('prefix', 'Prefix'),
        ('interface', 'Interface'),
        ('ip_address', 'IP Address'),
    ]
    
    ACTION_TYPES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('skip', 'Skip (Already Exists)'),
    ]
    
    review = models.ForeignKey(
        SyncReview,
        on_delete=models.CASCADE,
        related_name='items'
    )
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES)
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    object_name = models.CharField(max_length=255)
    object_identifier = models.CharField(
        max_length=255,
        help_text='Serial number, network ID, or other unique identifier'
    )
    current_data = models.JSONField(
        null=True,
        blank=True,
        help_text='Current data in NetBox (for updates)'
    )
    proposed_data = models.JSONField(
        help_text='Data to be synced from Meraki'
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('applied', 'Applied'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    error_message = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['item_type', 'object_name']
        verbose_name = 'Review Item'
        verbose_name_plural = 'Review Items'
    
    def __str__(self):
        return f"{self.action_type} {self.item_type}: {self.object_name}"
    
    def get_changes(self):
        """Get dictionary of changes between current and proposed data"""
        if not self.current_data or self.action_type == 'create':
            return self.proposed_data
        
        changes = {}
        for key, new_value in self.proposed_data.items():
            old_value = self.current_data.get(key)
            if old_value != new_value:
                changes[key] = {
                    'old': old_value,
                    'new': new_value
                }
        return changes
