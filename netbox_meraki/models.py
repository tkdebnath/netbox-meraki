from django.db import models
from django.urls import reverse
from django.core.exceptions import ValidationError
import re
import logging

logger = logging.getLogger(__name__)


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
    
    # Name transformation settings
    device_name_transform = models.CharField(
        max_length=20,
        choices=[
            ('keep', 'Keep Original'),
            ('upper', 'UPPERCASE'),
            ('lower', 'lowercase'),
            ('title', 'Title Case'),
        ],
        default='keep',
        verbose_name='Device Name Transform',
        help_text='How to transform device names from Meraki'
    )
    site_name_transform = models.CharField(
        max_length=20,
        choices=[
            ('keep', 'Keep Original'),
            ('upper', 'UPPERCASE'),
            ('lower', 'lowercase'),
            ('title', 'Title Case'),
        ],
        default='keep',
        verbose_name='Site Name Transform',
        help_text='How to transform site names from Meraki'
    )
    vlan_name_transform = models.CharField(
        max_length=20,
        choices=[
            ('keep', 'Keep Original'),
            ('upper', 'UPPERCASE'),
            ('lower', 'lowercase'),
            ('title', 'Title Case'),
        ],
        default='keep',
        verbose_name='VLAN Name Transform',
        help_text='How to transform VLAN names from Meraki'
    )
    ssid_name_transform = models.CharField(
        max_length=20,
        choices=[
            ('keep', 'Keep Original'),
            ('upper', 'UPPERCASE'),
            ('lower', 'lowercase'),
            ('title', 'Title Case'),
        ],
        default='keep',
        verbose_name='SSID Name Transform',
        help_text='How to transform SSID names from Meraki'
    )
    
    # Tag settings - comma-separated tag names
    site_tags = models.CharField(
        max_length=500,
        blank=True,
        default='Meraki',
        verbose_name='Site Tags',
        help_text='Comma-separated list of tags to apply to sites (e.g., "Meraki,Production")'
    )
    device_tags = models.CharField(
        max_length=500,
        blank=True,
        default='Meraki',
        verbose_name='Device Tags',
        help_text='Comma-separated list of tags to apply to devices (e.g., "Meraki,Network-Device")'
    )
    vlan_tags = models.CharField(
        max_length=500,
        blank=True,
        default='Meraki',
        verbose_name='VLAN Tags',
        help_text='Comma-separated list of tags to apply to VLANs (e.g., "Meraki,VLAN")'
    )
    prefix_tags = models.CharField(
        max_length=500,
        blank=True,
        default='Meraki',
        verbose_name='Prefix/Subnet Tags',
        help_text='Comma-separated list of tags to apply to prefixes/subnets (e.g., "Meraki,Subnet")'
    )
    
    # Scheduling Settings
    enable_scheduled_sync = models.BooleanField(
        default=False,
        verbose_name='Enable Scheduled Sync',
        help_text='Enable automatic scheduled synchronization'
    )
    sync_interval_minutes = models.IntegerField(
        default=60,
        verbose_name='Sync Interval (minutes)',
        help_text='Interval between automatic syncs in minutes (minimum 5)'
    )
    scheduled_sync_mode = models.CharField(
        max_length=20,
        default='auto',
        choices=[
            ('auto', 'Auto Sync'),
            ('review', 'Sync with Review'),
            ('dry_run', 'Dry Run'),
        ],
        verbose_name='Scheduled Sync Mode',
        help_text='Mode to use for scheduled synchronization'
    )
    last_scheduled_sync = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Last Scheduled Sync',
        help_text='Timestamp of last scheduled sync execution'
    )
    next_scheduled_sync = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Next Scheduled Sync',
        help_text='Timestamp of next scheduled sync'
    )
    
    # API Performance Settings
    enable_api_throttling = models.BooleanField(
        default=True,
        verbose_name='Enable API Throttling',
        help_text='Enable rate limiting to avoid overwhelming Meraki Dashboard API (recommended)'
    )
    api_requests_per_second = models.IntegerField(
        default=5,
        verbose_name='API Requests Per Second',
        help_text='Maximum API requests per second (Meraki limit is 10/sec, recommended: 5)'
    )
    enable_multithreading = models.BooleanField(
        default=False,
        verbose_name='Enable Multithreading',
        help_text='Use multiple threads to fetch data from Meraki API in parallel (faster but may hit rate limits)'
    )
    max_worker_threads = models.IntegerField(
        default=3,
        verbose_name='Max Worker Threads',
        help_text='Maximum number of concurrent threads for API requests (recommended: 2-5)'
    )
    
    class Meta:
        verbose_name = 'Plugin Settings'
        verbose_name_plural = 'Plugin Settings'
    
    def __str__(self):
        return "Meraki Plugin Settings"
    
    def clean(self):
        """Validate settings"""
        if self.sync_interval_minutes and self.sync_interval_minutes < 5:
            raise ValidationError('Sync interval must be at least 5 minutes')
    
    def update_next_sync_time(self):
        """Calculate and update next scheduled sync time"""
        from django.utils import timezone
        from datetime import timedelta
        
        if self.enable_scheduled_sync:
            now = timezone.now()
            self.last_scheduled_sync = now
            self.next_scheduled_sync = now + timedelta(minutes=self.sync_interval_minutes)
            self.save()
    
    def should_run_scheduled_sync(self):
        """Check if scheduled sync should run now"""
        from django.utils import timezone
        
        if not self.enable_scheduled_sync:
            return False
        
        if self.next_scheduled_sync is None:
            return True
        
        return timezone.now() >= self.next_scheduled_sync
    
    def get_tags_for_object_type(self, object_type: str) -> list:
        """
        Get list of tag names for a specific object type
        
        Args:
            object_type: One of 'site', 'device', 'vlan', 'prefix'
        
        Returns:
            List of tag names (strings)
        """
        tag_field_map = {
            'site': self.site_tags,
            'device': self.device_tags,
            'vlan': self.vlan_tags,
            'prefix': self.prefix_tags,
        }
        
        tag_string = tag_field_map.get(object_type, 'Meraki')
        if not tag_string:
            return ['Meraki']
        
        # Split by comma and strip whitespace
        tags = [tag.strip() for tag in tag_string.split(',') if tag.strip()]
        return tags if tags else ['Meraki']
    
    def transform_name(self, name: str, transform_type: str) -> str:
        """Apply name transformation based on setting"""
        if not name:
            return name
        
        if transform_type == 'upper':
            return name.upper()
        elif transform_type == 'lower':
            return name.lower()
        elif transform_type == 'title':
            return name.title()
        else:  # 'keep'
            return name
    
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
        help_text='Regular expression to match network names (e.g., "^(?P<region>NA|EMEA)-(?P<site>[A-Z]{3})$"). Use (?P<name>...) for named groups'
    )
    site_name_template = models.CharField(
        max_length=200,
        verbose_name='Site Name Template',
        help_text='Template for site name. Use {name} for named groups, {0}/{1} for numbered groups, or {network_name} for full name'
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
            # Check for common mistakes
            if '??<' in self.regex_pattern:
                raise ValidationError({
                    'regex_pattern': 'Invalid named group syntax. Use (?P<name>...) instead of (??<name>...)'
                })
            
            # Try to compile the regex
            re.compile(self.regex_pattern)
        except re.error as e:
            raise ValidationError({
                'regex_pattern': f'Invalid regular expression: {str(e)}. For named groups, use (?P<name>...)'
            })
    
    def apply(self, network_name: str) -> str:
        """Apply this rule to a network name"""
        if not self.enabled:
            return network_name
        
        try:
            match = re.match(self.regex_pattern, network_name)
            if match:
                # Start with the template
                result = self.site_name_template
                
                # Replace named groups first (e.g., {site}, {location})
                for name, value in match.groupdict().items():
                    if value:
                        result = result.replace(f'{{{name}}}', value)
                
                # Replace numbered groups {0}, {1}, etc.
                for i, group in enumerate(match.groups()):
                    result = result.replace(f'{{{i}}}', group or '')
                
                # Replace special placeholders
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
    ssids_synced = models.IntegerField(default=0)
    deleted_sites = models.IntegerField(default=0)
    deleted_devices = models.IntegerField(default=0)
    deleted_vlans = models.IntegerField(default=0)
    deleted_prefixes = models.IntegerField(default=0)
    updated_prefixes = models.IntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    
    # Progress tracking
    progress_logs = models.JSONField(default=list, blank=True, help_text='Live progress log entries')
    current_operation = models.CharField(max_length=255, blank=True, help_text='Current sync operation')
    progress_percent = models.IntegerField(default=0, help_text='Overall progress percentage')
    
    # Cancel capability
    cancel_requested = models.BooleanField(default=False, help_text='Flag to cancel ongoing sync')
    cancelled_at = models.DateTimeField(null=True, blank=True, help_text='When sync was cancelled')
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
    
    def add_progress_log(self, message: str, level: str = 'info'):
        """Add a progress log entry with timestamp"""
        from django.utils import timezone
        entry = {
            'timestamp': timezone.now().isoformat(),
            'level': level,
            'message': message
        }
        if not self.progress_logs:
            self.progress_logs = []
        self.progress_logs.append(entry)
        self.save(update_fields=['progress_logs'])
    
    def update_progress(self, operation: str, percent: int):
        """Update current operation and progress percentage"""
        self.current_operation = operation
        self.progress_percent = min(100, max(0, percent))
        self.save(update_fields=['current_operation', 'progress_percent'])
    
    def request_cancel(self):
        """Request cancellation of this sync"""
        from django.utils import timezone
        self.cancel_requested = True
        self.cancelled_at = timezone.now()
        self.save(update_fields=['cancel_requested', 'cancelled_at'])
    
    def check_cancel_requested(self) -> bool:
        """Check if cancellation has been requested"""
        self.refresh_from_db(fields=['cancel_requested'])
        return self.cancel_requested


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
        """Apply all approved review items in correct dependency order"""
        from .sync_service import MerakiSyncService
        
        service = MerakiSyncService()
        
        # Define the correct order for applying items (dependencies first)
        item_order = ['site', 'vlan', 'prefix', 'device_type', 'device', 'interface', 'ip_address', 'ssid']
        
        # Apply items in dependency order
        for item_type in item_order:
            approved_items = self.items.filter(status='approved', item_type=item_type).order_by('id')
            
            for item in approved_items:
                try:
                    service.apply_review_item(item)
                    item.status = 'applied'
                    item.save()
                except Exception as e:
                    item.status = 'failed'
                    item.error_message = str(e)
                    item.save()
                    # Log but continue with other items
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to apply {item_type} {item.object_name}: {e}")
        
        self.status = 'applied'
        self.save()


class ReviewItem(models.Model):
    """Individual item in a sync review"""
    
    ITEM_TYPES = [
        ('site', 'Site'),
        ('device', 'Device'),
        ('device_type', 'Device Type'),
        ('vlan', 'VLAN'),
        ('prefix', 'Prefix'),
        ('interface', 'Interface'),
        ('ip_address', 'IP Address'),
        ('ssid', 'SSID'),
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
    editable_data = models.JSONField(
        null=True,
        blank=True,
        help_text='User-edited data to apply (overrides proposed_data if set)'
    )
    preview_display = models.TextField(
        blank=True,
        help_text='Human-readable preview of what will be created/updated'
    )
    related_object_info = models.JSONField(
        null=True,
        blank=True,
        help_text='Information about related objects (site, device role, etc.)'
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
    
    def get_final_data(self):
        """Get the final data to apply (editable_data if set, otherwise proposed_data)"""
        return self.editable_data if self.editable_data else self.proposed_data
    
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
