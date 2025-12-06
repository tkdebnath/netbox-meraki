from django.db import models
from django.urls import reverse


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
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Sync Log'
        verbose_name_plural = 'Sync Logs'
    
    def __str__(self):
        return f"Sync {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {self.status}"
    
    def get_absolute_url(self):
        return reverse('plugins:netbox_meraki:synclog', args=[self.pk])
