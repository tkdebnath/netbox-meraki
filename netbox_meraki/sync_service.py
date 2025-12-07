import logging
from datetime import datetime
from typing import Dict, List, Optional
from ipaddress import ip_network

from django.db import transaction
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from dcim.models import Site, Device, DeviceType, DeviceRole, Manufacturer, Interface
from ipam.models import VLAN, VLANGroup, Prefix, IPAddress
from wireless.models import WirelessLAN, WirelessLANGroup
from extras.models import Tag, CustomField

from .meraki_client import MerakiAPIClient
from .models import SyncLog, PluginSettings, SiteNameRule, PrefixFilterRule, SyncReview, ReviewItem


logger = logging.getLogger('netbox_meraki')


class MerakiSyncService:
    """Service for synchronizing Meraki data to NetBox"""
    
    def __init__(self, api_key: Optional[str] = None, sync_mode: Optional[str] = None):
        """Initialize sync service"""
        self.client = MerakiAPIClient(api_key=api_key)
        self.sync_log = None
        self.sync_mode = sync_mode or PluginSettings.get_settings().sync_mode
        self.review = None
        self.stats = {
            'organizations': 0,
            'networks': 0,
            'sites': 0,
            'devices': 0,
            'vlans': 0,
            'prefixes': 0,
            'ssids': 0,
            'deleted_sites': 0,
            'deleted_devices': 0,
            'deleted_vlans': 0,
            'deleted_prefixes': 0,
            'updated_prefixes': 0,
        }
        self.errors = []
        self.synced_object_ids = {
            'sites': set(),
            'devices': set(),
            'vlans': set(),
            'prefixes': set(),
        }
        self._ensure_custom_fields()
    
    def _ensure_custom_fields(self):
        """Ensure required custom fields exist"""
        device_ct = ContentType.objects.get_for_model(Device)
        
        firmware_field, created = CustomField.objects.get_or_create(
            name='software_version',
            defaults={
                'label': 'Software Version',
                'type': 'text',
                'description': 'Firmware version from Meraki Dashboard',
                'weight': 100,
            }
        )
        if created:
            firmware_field.object_types.set([device_ct])
            logger.info("Created custom field: software_version")
        elif device_ct not in firmware_field.object_types.all():
            firmware_field.object_types.add(device_ct)
        
        mac_field, created = CustomField.objects.get_or_create(
            name='mac_address',
            defaults={
                'label': 'MAC Address',
                'type': 'text',
                'description': 'Device MAC address from Meraki',
                'weight': 102,
            }
        )
        if created:
            mac_field.object_types.set([device_ct])
            logger.info("Created custom field: mac_address")
        elif device_ct not in mac_field.object_types.all():
            mac_field.object_types.add(device_ct)
    
    def _cleanup_old_review_items(self):
        """Clean up old review items and completed reviews before starting new sync"""
        from datetime import timedelta
        from django.utils import timezone
        
        cutoff_date = timezone.now() - timedelta(days=7)
        old_reviews = SyncReview.objects.filter(
            status__in=['applied', 'cancelled'],
            created__lt=cutoff_date
        )
        
        deleted_count = 0
        for review in old_reviews:
            item_count = review.items.count()
            review.delete()  # This will cascade delete ReviewItems
            deleted_count += item_count
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old review items from completed syncs")
        
        
        orphaned_reviews = SyncReview.objects.filter(sync_log__isnull=True)
        for review in orphaned_reviews:
            review.delete()
    
    def sync_all(self, organization_id: Optional[str] = None, network_ids: Optional[List[str]] = None) -> SyncLog:
        """
        Perform full synchronization from Meraki to NetBox
        
        Args:
            organization_id: Optional specific organization ID to sync
            network_ids: Optional list of specific network IDs to sync
        
        Returns:
            SyncLog instance with results
        """
        start_time = datetime.now()
        
        
        self._cleanup_old_review_items()
        
        # Determine status based on sync mode
        if self.sync_mode == 'dry_run':
            initial_status = 'dry_run'
        elif self.sync_mode == 'review':
            initial_status = 'pending_review'
        else:
            initial_status = 'running'
        
        # Create sync log
        self.sync_log = SyncLog.objects.create(
            status=initial_status,
            message=f'Starting synchronization ({self.sync_mode} mode)...',
            sync_mode=self.sync_mode
        )
        
        # Create review session for ALL modes (used for staging and audit trail)
        self.review = SyncReview.objects.create(
            sync_log=self.sync_log,
            status='pending' if self.sync_mode in ['review', 'dry_run'] else 'approved'
        )
        
        try:
            logger.info("Starting Meraki synchronization")
            self.sync_log.add_progress_log("Starting Meraki synchronization", "info")
            self.sync_log.update_progress("Initializing sync", 0)
            
            
            meraki_tag, _ = Tag.objects.get_or_create(
                name='Meraki',
                defaults={'description': 'Synced from Cisco Meraki Dashboard'}
            )
            
            # Get all organizations or filter to specific one
            self.sync_log.add_progress_log("Fetching organizations from Meraki Dashboard", "info")
            if organization_id:
                organizations = [self.client.get_organization(organization_id)]
                logger.info(f"Syncing specific organization: {organization_id}")
                self.sync_log.add_progress_log(f"Syncing specific organization: {organization_id}", "info")
            else:
                organizations = self.client.get_organizations()
                logger.info(f"Found {len(organizations)} organizations")
                self.sync_log.add_progress_log(f"Found {len(organizations)} organizations", "info")
            
            total_orgs = len(organizations)
            for idx, org in enumerate(organizations):
                
                if self.sync_log.check_cancel_requested():
                    self.sync_log.add_progress_log("Sync cancelled by user", "warning")
                    self.sync_log.status = 'failed'
                    self.sync_log.message = "Sync cancelled by user"
                    self.sync_log.save()
                    logger.warning("Sync cancelled by user")
                    return self.sync_log
                
                try:
                    progress = int(((idx + 1) / total_orgs) * 80)  # 0-80% for orgs
                    self.sync_log.update_progress(f"Syncing organization: {org.get('name')}", progress)
                    self.sync_log.add_progress_log(f"Processing organization: {org.get('name')}", "info")
                    self._sync_organization(org, meraki_tag, network_ids)
                    self.stats['organizations'] += 1
                except Exception as e:
                    error_msg = f"Error syncing organization {org.get('name')}: {str(e)}"
                    logger.error(error_msg)
                    self.sync_log.add_progress_log(error_msg, "error")
                    self.errors.append(error_msg)
            
            # Clean up orphaned objects (only in auto mode)
            if self.sync_mode == 'auto':
                self.sync_log.update_progress("Cleaning up orphaned objects", 85)
                self.sync_log.add_progress_log("Cleaning up orphaned objects", "info")
                logger.info("\nCleaning up orphaned objects...")
                self._cleanup_orphaned_objects(meraki_tag)
            
            self.sync_log.update_progress("Finalizing sync", 100)
            
            # Update sync log
            duration = (datetime.now() - start_time).total_seconds()
            
            # Update status based on mode and results
            if self.sync_mode == 'dry_run':
                status = 'dry_run'
                message = f"Dry run completed - {self.review.items_total if self.review else 0} items would be modified"
            elif self.sync_mode == 'review':
                status = 'pending_review'
                message = f"Review ready - {self.review.items_total if self.review else 0} items pending approval"
            else:
                status = 'success' if not self.errors else 'partial' if self.stats['devices'] > 0 else 'failed'
                message = f"Synchronized {self.stats['organizations']} organizations"
            
            self.sync_log.status = status
            self.sync_log.message = message
            self.sync_log.organizations_synced = self.stats['organizations']
            self.sync_log.networks_synced = self.stats['networks']
            self.sync_log.devices_synced = self.stats['devices']
            self.sync_log.vlans_synced = self.stats['vlans']
            self.sync_log.prefixes_synced = self.stats['prefixes']
            self.sync_log.ssids_synced = self.stats['ssids']
            self.sync_log.deleted_sites = self.stats.get('deleted_sites', 0)
            self.sync_log.deleted_devices = self.stats.get('deleted_devices', 0)
            self.sync_log.deleted_vlans = self.stats.get('deleted_vlans', 0)
            self.sync_log.deleted_prefixes = self.stats.get('deleted_prefixes', 0)
            self.sync_log.updated_prefixes = self.stats.get('updated_prefixes', 0)
            self.sync_log.errors = self.errors
            self.sync_log.duration_seconds = duration
            
            # Log sites stat for debugging (field may not exist in DB yet)
            if self.stats.get('sites', 0) > 0:
                logger.info(f"Synced {self.stats['sites']} sites")
            
            self.sync_log.save()
            
            # Update review stats
            if self.review:
                self.review.items_total = self.review.items.count()
                self.review.save()
            
            logger.info(f"Synchronization completed in {duration:.2f} seconds ({self.sync_mode} mode)")
            
        except Exception as e:
            logger.error(f"Synchronization failed: {str(e)}")
            self.sync_log.status = 'failed'
            self.sync_log.message = f"Synchronization failed: {str(e)}"
            self.sync_log.errors = self.errors + [str(e)]
            self.sync_log.save()
            raise
        
        return self.sync_log
    
    def _sync_organization(self, org: Dict, meraki_tag: Tag, network_ids: Optional[List[str]] = None):
        """Sync a single organization
        
        Args:
            org: Organization data from Meraki API
            meraki_tag: Tag to apply to synced objects
            network_ids: Optional list of specific network IDs to sync (None = all networks)
        """
        org_id = org['id']
        org_name = org['name']
        
        logger.info(f"Syncing organization: {org_name}")
        
        # Fetch device statuses for the entire organization (includes firmware)
        try:
            self.sync_log.add_progress_log(f"Fetching device statuses from organization: {org_name}", "info")
            device_statuses = self.client.get_device_statuses(org_id)
            # Create lookup dictionary by serial number
            device_status_map = {status['serial']: status for status in device_statuses}
            logger.info(f"Fetched status for {len(device_statuses)} devices in {org_name}")
        except Exception as e:
            logger.warning(f"Could not fetch device statuses for {org_name}: {e}")
            device_status_map = {}
        
        # Get networks for this organization
        self.sync_log.add_progress_log(f"Fetching networks from organization: {org_name}", "info")
        networks = self.client.get_networks(org_id)
        
        # Filter networks if specific IDs provided
        if network_ids:
            networks = [n for n in networks if n['id'] in network_ids]
            logger.info(f"Filtering to {len(networks)} selected networks in {org_name}")
            self.sync_log.add_progress_log(f"Syncing {len(networks)} selected networks in {org_name}", "info")
        else:
            logger.info(f"Found {len(networks)} networks in {org_name}")
            self.sync_log.add_progress_log(f"Found {len(networks)} networks in {org_name}", "info")
        
        for network in networks:
            try:
                self._sync_network(network, org_name, meraki_tag, device_status_map)
                self.stats['networks'] += 1
            except Exception as e:
                error_msg = f"Error syncing network {network.get('name')}: {str(e)}"
                logger.error(error_msg)
                self.errors.append(error_msg)
    
    def _sync_network(self, network: Dict, org_name: str, meraki_tag: Tag, device_status_map: Dict = None):
        """Sync a single network as a Site
        
        Args:
            network: Network data from Meraki API
            org_name: Organization name
            meraki_tag: Tag to apply to synced objects
            device_status_map: Dictionary of device statuses by serial number (includes firmware)
        """
        if device_status_map is None:
            device_status_map = {}
            
        network_id = network['id']
        network_name = network['name']
        
        logger.info(f"Syncing network: {network_name}")
        
        # Get devices in this network first to check if we should create the site
        self.sync_log.add_progress_log(f"Fetching devices from network: {network_name}", "info")
        devices = self.client.get_devices(network_id)
        
        # Fetch detailed firmware information from network firmware upgrades API
        firmware_info_map = {}
        try:
            firmware_data = self.client.get_network_firmware_upgrades(network_id)
            if firmware_data and 'products' in firmware_data:
                # Map product types to their current firmware versions
                for product_type, product_data in firmware_data.get('products', {}).items():
                    current_version = product_data.get('currentVersion', {})
                    if current_version:
                        # Store shortName which has the full version like "MX 18.107.4"
                        short_name = current_version.get('shortName', '')
                        if short_name:
                            firmware_info_map[product_type] = short_name
                logger.debug(f"Fetched detailed firmware info for {len(firmware_info_map)} product types in {network_name}")
        except Exception as e:
            logger.debug(f"Could not fetch detailed firmware info for {network_name}: {e}")
        
        # Merge firmware information from device statuses and detailed firmware API
        firmware_count = 0
        for device in devices:
            serial = device.get('serial')
            model = device.get('model', '')
            product_type = device.get('productType', '')
            
            # Always merge status info first from device_status_map if available
            if serial and serial in device_status_map:
                status_info = device_status_map[serial]
                # Merge status info (online/offline/dormant/alerting)
                if 'status' in status_info:
                    device['status'] = status_info['status']
                if 'publicIp' in status_info:
                    device['publicIp'] = status_info['publicIp']
            
            # Try to get detailed firmware version from network firmware upgrades API first
            if product_type and product_type in firmware_info_map:
                device['firmware'] = firmware_info_map[product_type]
                firmware_count += 1
                logger.debug(f"Set firmware for {serial} from firmware upgrades API: {firmware_info_map[product_type]}")
            elif serial and serial in device_status_map:
                # Fallback to device status API for firmware
                status_info = device_status_map[serial]
                if 'firmware' in status_info and status_info['firmware']:
                    device['firmware'] = status_info['firmware']
                    firmware_count += 1
        
        if firmware_count > 0:
            logger.info(f"Merged firmware info for {firmware_count}/{len(devices)} devices in {network_name}")
        
        logger.info(f"Found {len(devices)} devices in {network_name}")
        self.sync_log.add_progress_log(f"Found {len(devices)} devices in {network_name}", "info")
        
        # Skip this network if it has no devices
        if not devices:
            logger.info(f"Skipping network '{network_name}' - no devices found")
            return
        
        # Get plugin settings for transformations
        plugin_settings = PluginSettings.get_settings()
        
        # Apply site name transformation rules first
        site_name = SiteNameRule.transform_network_name(network_name)
        
        # If site_name is None, it means the site should be skipped (doesn't match rules and process_unmatched_sites is False)
        if site_name is None:
            logger.info(f"⊗ Skipping site '{network_name}' - does not match any name rules")
            return None
        
        if site_name != network_name:
            logger.info(f"Transformed site name: '{network_name}' -> '{site_name}'")
        
        # Apply name transformation setting
        site_name = plugin_settings.transform_name(site_name, plugin_settings.site_name_transform)
        
        # Generate slug from site name
        import re
        slug = re.sub(r'[^a-z0-9-]+', '-', site_name.lower()).strip('-')
        if not slug:
            slug = f"site-{network_id.lower()}"
        
        # Check if site exists
        existing_site = Site.objects.filter(name=site_name).first()
        action_type = 'update' if existing_site else 'create'
        current_data = None
        
        if existing_site:
            current_data = {
                'name': existing_site.name,
                'slug': existing_site.slug,
                'description': existing_site.description,
            }
        
        # Prepare site data
        proposed_site_data = {
            'name': site_name,
            'slug': slug,
            'description': network_name,
            'network_id': network_id,
            'timezone': network.get('timeZone', 'N/A'),
        }
        
        # All sync modes: Create review item (staging table) first
        review_item = self._create_review_item(
            item_type='site',
            action_type=action_type,
            object_name=site_name,
            object_identifier=network_id,
            proposed_data=proposed_site_data,
            current_data=current_data
        )
        logger.info(f"Created staging entry for site: {site_name} ({action_type})")
        self.sync_log.add_progress_log(f"Staging site: {site_name} (Network: {network_name})", "info")
        
        
        if self.sync_mode == 'auto' and review_item:
            try:
                review_item.status = 'approved'
                review_item.save()
                self.apply_review_item(review_item)
                review_item.status = 'applied'
                review_item.save()
                site = Site.objects.get(name=site_name)
                self.stats['sites'] += 1
                self.sync_log.add_progress_log(f"✓ Created/Updated site: {site_name}", "success")
            except Exception as e:
                review_item.status = 'failed'
                review_item.error_message = str(e)
                review_item.save()
                error_msg = f"Failed to apply site {site_name}: {e}"
                logger.error(error_msg)
                self.sync_log.add_progress_log(f"✗ {error_msg}", "error")
                raise
        else:
            
            site = existing_site if existing_site else site_name
        
        # Sync VLANs and prefixes (now works in all modes via staging)
        # Pass site name string so it works in review/dry-run mode
        site_name_for_sync = site.name if isinstance(site, Site) else site
        
        # 1. Sync VLANs for this network FIRST (after site)
        try:
            self._sync_vlans(network_id, site_name_for_sync, meraki_tag)
        except Exception as e:
            error_msg = f"Error syncing VLANs for network {network_name}: {str(e)}"
            logger.error(error_msg)
            self.errors.append(error_msg)
        
        # 2. Sync prefixes for this network SECOND (after VLANs)
        try:
            self._sync_prefixes(network_id, site_name_for_sync, meraki_tag)
        except Exception as e:
            error_msg = f"Error syncing prefixes for network {network_name}: {str(e)}"
            logger.error(error_msg)
            self.errors.append(error_msg)
        
        # 3. Process devices LAST (after VLANs and prefixes)
        for device in devices:
            try:
                self._sync_device(device, site, meraki_tag)
                self.stats['devices'] += 1
            except Exception as e:
                error_msg = f"Error syncing device {device.get('name', device.get('serial'))}: {str(e)}"
                logger.error(error_msg)
                self.errors.append(error_msg)
    
    def _sync_device(self, device: Dict, site: Site, meraki_tag: Tag):
        """Sync a single device"""
        serial = device['serial']
        name = device.get('name') or serial  # Use serial if name is None or empty
        model = device.get('model', 'Unknown')
        notes = device.get('notes', '')
        tags = device.get('tags', [])
        address = device.get('address', '')
        
        # Extract product type from model
        product_type = device.get('productType', '')
        if not product_type and model and len(model) >= 2:
            # Get first two characters of model (e.g., "MS350-48LP" -> "MS")
            product_type = model[:2].upper()
        
        logger.debug(f"Syncing device: {name} ({serial}) - Model: {model}, Product Type: {product_type}")
        
        # Get plugin settings
        plugin_settings = PluginSettings.get_settings()
        
        # Apply device name transformation
        name = plugin_settings.transform_name(name, plugin_settings.device_name_transform)
        
        # Get device role based on product type from settings
        role_name = plugin_settings.get_device_role_for_product(product_type)
        
        logger.info(f"Device {name}: model='{model}', product_type='{product_type}', assigned role='{role_name}'")
        
        # Get site name - handle both Site object and string
        site_name = site.name if hasattr(site, 'name') else site
        
        # For MX devices, capture WAN IP
        wan_ip = None
        raw_wan_ip = None
        if product_type.startswith('MX'):
            raw_wan_ip = device.get('wan1Ip') or device.get('wan2Ip')
            if raw_wan_ip:
                wan_ip = raw_wan_ip
        
        # Prepare proposed data (don't create device types/roles yet in review mode)
        firmware_version = device.get('firmware', 'Unknown')
        comments = f"MAC: {device.get('mac', 'N/A')}\\n"
        comments += f"LAN IP: {device.get('lanIp', 'N/A')}\\n"
        if wan_ip:
            comments += f"WAN IP: {wan_ip}\\n"
        comments += f"Firmware: {firmware_version}\\n"
        comments += f"Product Type: {product_type}"
        
        if firmware_version and firmware_version != 'Unknown':
            logger.debug(f"Device {name} firmware: {firmware_version}")
        
        # Map Meraki device status to NetBox status
        # Meraki statuses: online, offline, alerting, dormant
        meraki_status = device.get('status', '').lower()
        netbox_status = 'active'  # Default to active
        
        if meraki_status == 'offline':
            netbox_status = 'offline'
        elif meraki_status == 'dormant':
            netbox_status = 'offline'  # Dormant devices are essentially offline
        elif meraki_status in ['online', 'alerting']:
            netbox_status = 'active'  # Online or alerting devices are active
        
        logger.debug(f"Device {name} status: Meraki={meraki_status}, NetBox={netbox_status}")
        
        proposed_data = {
            'name': name,
            'serial': serial,
            'model': model,
            'manufacturer': 'Cisco Meraki',
            'role': role_name,
            'site': site_name,
            'status': netbox_status,
            'product_type': product_type,
            'mac': device.get('mac', 'N/A'),
            'lan_ip': device.get('lanIp', 'N/A'),
            'wan_ip': wan_ip if wan_ip else 'N/A',
            'firmware': firmware_version,
            'comments': comments,
            'custom_field_data': {
                'software_version': firmware_version if firmware_version != 'Unknown' else '',
                'meraki_network_id': device.get('networkId', ''),
                'mac_address': device.get('mac', ''),
            }
        }
        
        # Check if device exists
        existing_device = Device.objects.filter(serial=serial).first()
        action_type = 'update' if existing_device else 'create'
        current_data = None
        
        if existing_device:
            current_data = {
                'name': existing_device.name,
                'serial': existing_device.serial,
                'model': existing_device.device_type.model,
                'role': existing_device.role.name,
                'site': existing_device.site.name,
                'status': existing_device.status,
            }
        
        # All sync modes: Create review item (staging table) first
        review_item = self._create_review_item(
            item_type='device',
            action_type=action_type,
            object_name=name,
            object_identifier=serial,
            proposed_data=proposed_data,
            current_data=current_data
        )
        logger.info(f"Created staging entry for device: {name} ({action_type})")
        site_name = site.name if isinstance(site, Site) else site
        self.sync_log.add_progress_log(f"Staging device: {name} [{model}] at {site_name}", "info")
        
        
        if self.sync_mode == 'auto' and review_item:
            try:
                review_item.status = 'approved'
                review_item.save()
                self.apply_review_item(review_item)
                review_item.status = 'applied'
                review_item.save()
                self.sync_log.add_progress_log(f"✓ Created/Updated device: {name} (Serial: {serial})", "success")
                
                # Get the device object for additional operations
                device_obj = Device.objects.get(serial=serial)
                
                # For MX devices with WAN IP, create WAN interface and IP address
                if raw_wan_ip:
                    self._create_wan_interface_and_ip(serial, name, str(wan_ip), str(raw_wan_ip))
                
                # For MR (wireless) devices, sync SSIDs
                if product_type.startswith('MR'):
                    try:
                        self._sync_device_ssids(device_obj, device)
                        logger.info(f"✓ Synced SSIDs for {name}")
                    except Exception as e:
                        logger.warning(f"Could not sync SSIDs for {name}: {e}")
                
                # For MX devices, create SVI interfaces for VLANs
                if product_type.startswith('MX'):
                    try:
                        network_id = device.get('networkId')
                        if network_id:
                            self._create_mx_svi_interfaces(device_obj, network_id)
                            logger.info(f"✓ Created SVI interfaces for {name}")
                    except Exception as e:
                        logger.warning(f"Could not create SVI interfaces for {name}: {e}")
                
                # For MS devices, create switch port interfaces
                if product_type.startswith('MS'):
                    try:
                        self._create_switch_port_interfaces(device_obj, serial)
                        logger.info(f"✓ Created switch port interfaces for {name}")
                    except Exception as e:
                        logger.warning(f"Could not create switch port interfaces for {name}: {e}")
            except Exception as e:
                review_item.status = 'failed'
                review_item.error_message = str(e)
                review_item.save()
                error_msg = f"Failed to apply device {name}: {e}"
                logger.error(error_msg)
                self.sync_log.add_progress_log(f"✗ {error_msg}", "error")
                raise
            
            return
        
        
        if raw_wan_ip:
            # Stage WAN interface
            interface_data = {
                'device': name,
                'device_serial': serial,
                'name': 'WAN',
                'type': 'other',
                'description': 'Meraki MX WAN Interface',
                'enabled': True,
            }
            interface_item = self._create_review_item(
                item_type='interface',
                action_type='create',
                object_name=f"{name} - WAN",
                object_identifier=f"{serial}-wan",
                proposed_data=interface_data,
                current_data=None
            )
            logger.info(f"Created staging entry for WAN interface on {name}")
            
            # Stage WAN IP address
            ip_data = {
                'address': f"{wan_ip}/32",
                'device': name,
                'device_serial': serial,
                'interface': 'WAN',
                'description': 'Meraki MX WAN IP',
                'status': 'active',
            }
            ip_item = self._create_review_item(
                item_type='ip_address',
                action_type='create',
                object_name=f"{wan_ip} on {name}",
                object_identifier=f"{serial}-wan-ip",
                proposed_data=ip_data,
                current_data=None
            )
            logger.info(f"Created staging entry for WAN IP {wan_ip} on {name}")
        
        
        return
    
    def _sync_device_ssids(self, device: Device, meraki_device: Dict):
        """Create Wireless LAN objects for SSIDs on wireless access points"""
        try:
            # Get the network ID from device
            network_id = meraki_device.get('networkId')
            if not network_id:
                return
            
            # Get plugin settings for transformations
            plugin_settings = PluginSettings.get_settings()
            
            # Fetch SSIDs for this network
            try:
                ssids = self.client.get_wireless_ssids(network_id)
                if ssids:
                    for ssid_data in ssids:
                        if not ssid_data.get('enabled', False):
                            continue
                        
                        ssid_name = ssid_data.get('name', f"SSID {ssid_data.get('number', '')}")
                        ssid_number = ssid_data.get('number')
                        auth_mode = ssid_data.get('authMode', 'open')
                        encryption = ssid_data.get('encryptionMode', 'open')
                        
                        # Apply SSID name transformation
                        ssid_name = plugin_settings.transform_name(
                            ssid_name,
                            plugin_settings.ssid_name_transform
                        )
                        
                        # Create or update Wireless LAN (without group - SSIDs are organization-wide)
                        wlan, created = WirelessLAN.objects.update_or_create(
                            ssid=ssid_name,
                            defaults={
                                'description': f"Meraki SSID #{ssid_number} - Auth: {auth_mode}, Encryption: {encryption}",
                                'status': 'active',
                            }
                        )
                        
                        if created:
                            logger.info(f"✓ Created Wireless LAN '{ssid_name}'")
                        
                        # Associate the wireless LAN with this interface
                        # Find or create a wireless interface on the AP
                        wireless_interface, _ = Interface.objects.get_or_create(
                            device=device,
                            name='radio0',
                            defaults={
                                'type': 'ieee802.11ax',
                                'description': 'Wireless radio interface',
                                'enabled': True,
                            }
                        )
                        
                        # Set the wireless LAN on the interface
                        if wireless_interface.wireless_lans.filter(id=wlan.id).exists():
                            logger.debug(f"SSID '{ssid_name}' already associated with {device.name}")
                        else:
                            wireless_interface.wireless_lans.add(wlan)
                            logger.info(f"✓ Added Wireless LAN '{ssid_name}' to AP {device.name}")
                        
                        self.stats['ssids'] += 1
                        
            except Exception as e:
                logger.debug(f"Could not fetch SSIDs for AP {device.name}: {e}")
        except Exception as e:
            logger.warning(f"Error syncing SSIDs for device {device.name}: {e}")
    
    def _create_mx_svi_interfaces(self, device: Device, network_id: str):
        """Create SVI (VLAN) interfaces on MX device"""
        try:
            # Get VLANs for this network
            vlans = self.client.get_appliance_vlans(network_id)
            if not vlans:
                return
            
            for vlan_data in vlans:
                vlan_id = vlan_data.get('id')
                vlan_name = vlan_data.get('name', f"VLAN {vlan_id}")
                vlan_subnet = vlan_data.get('subnet')
                appliance_ip = vlan_data.get('applianceIp')
                
                if not vlan_id:
                    continue
                
                # Create or get the VLAN interface (SVI)
                interface_name = f"vlan{vlan_id}"
                interface, created = Interface.objects.get_or_create(
                    device=device,
                    name=interface_name,
                    defaults={
                        'type': 'virtual',
                        'description': f"{vlan_name} - {vlan_subnet if vlan_subnet else 'N/A'}",
                        'enabled': True,
                    }
                )
                
                if created:
                    logger.info(f"✓ Created SVI interface {interface_name} on {device.name}")
                
                # If there's an appliance IP, assign it to the interface
                if appliance_ip:
                    # Determine IP with CIDR if subnet is available
                    if vlan_subnet and '/' in vlan_subnet:
                        # Extract prefix length from subnet
                        prefix_length = vlan_subnet.split('/')[1]
                        ip_address_str = f"{appliance_ip}/{prefix_length}"
                    else:
                        ip_address_str = f"{appliance_ip}/24"  # Default to /24
                    
                    # Check if IP already exists
                    existing_ip = IPAddress.objects.filter(address=ip_address_str).first()
                    
                    if existing_ip:
                        # IP exists - check if it's assigned to a different device's interface
                        if existing_ip.assigned_object and existing_ip.assigned_object.device != device:
                            # IP belongs to another device (e.g., HA pair), skip assignment
                            logger.debug(f"IP {appliance_ip} already assigned to {existing_ip.assigned_object.device.name}, skipping for {device.name}")
                        elif not existing_ip.assigned_object:
                            # IP exists but not assigned, assign it to this interface
                            existing_ip.assigned_object = interface
                            existing_ip.description = f'{vlan_name} SVI on {device.name}'
                            existing_ip.save()
                            logger.info(f"✓ Assigned existing IP {appliance_ip} to {interface_name} on {device.name}")
                        else:
                            # Already assigned to this device's interface
                            logger.debug(f"IP {appliance_ip} already assigned to {interface_name} on {device.name}")
                    else:
                        # Create new IP and assign to interface
                        ip_address = IPAddress.objects.create(
                            address=ip_address_str,
                            description=f'{vlan_name} SVI on {device.name}',
                            status='active',
                            assigned_object=interface
                        )
                        logger.info(f"✓ Assigned IP {appliance_ip} to {interface_name} on {device.name}")
                        
        except Exception as e:
            logger.error(f"Error creating SVI interfaces for {device.name}: {e}")
    
    def _create_wan_interface_and_ip(self, device_serial: str, device_name: str, wan_ip: str, raw_wan_ip: str):
        """Create WAN interface and assign IP address for MX devices in auto mode"""
        try:
            device = Device.objects.get(serial=device_serial)
            
            # Create or get WAN interface
            interface, created = Interface.objects.get_or_create(
                device=device,
                name='WAN',
                defaults={
                    'type': 'other',
                    'description': 'Meraki MX WAN Interface',
                    'enabled': True,
                }
            )
            
            if created:
                logger.info(f"✓ Created WAN interface on {device_name}")
            else:
                logger.info(f"✓ WAN interface already exists on {device_name}")
            
            # Create or update IP address
            ip_address_str = f"{raw_wan_ip}/32" if '/' not in raw_wan_ip else raw_wan_ip
            ip_address, ip_created = IPAddress.objects.get_or_create(
                address=ip_address_str,
                defaults={
                    'description': 'Meraki MX WAN IP',
                    'status': 'active',
                }
            )
            
            # Assign IP to interface
            if not ip_address.assigned_object:
                ip_address.assigned_object = interface
                ip_address.save()
                logger.info(f"✓ Assigned WAN IP {raw_wan_ip} to interface WAN on {device_name}")
            else:
                logger.info(f"✓ WAN IP {raw_wan_ip} already assigned on {device_name}")
                
        except Device.DoesNotExist:
            logger.error(f"Device with serial {device_serial} not found for WAN interface creation")
        except Exception as e:
            logger.error(f"Error creating WAN interface/IP for {device_name}: {e}")
    
    def _create_switch_port_interfaces(self, device: Device, serial: str):
        """Create switch port interfaces for MS devices with port configuration"""
        try:
            # Fetch switch ports from Meraki API
            ports = self.client.get_switch_ports(serial)
            
            if not ports:
                logger.debug(f"No switch ports found for {device.name}")
                return
            
            logger.info(f"Creating {len(ports)} switch port interfaces for {device.name}")
            
            for port in ports:
                port_id = port.get('portId')
                port_name = port.get('name', f"Port {port_id}")
                enabled = port.get('enabled', True)
                port_type = port.get('type', 'access')  # access or trunk
                vlan = port.get('vlan')  # For access ports
                allowed_vlans = port.get('allowedVlans', 'all')  # For trunk ports
                voice_vlan = port.get('voiceVlan')
                poe_enabled = port.get('poeEnabled', False)
                
                # Determine interface type based on port speed/type
                interface_type = '1000base-t'  # Default to gigabit
                if 'SFP' in port_name.upper() or 'uplink' in port_name.lower():
                    interface_type = '10gbase-x-sfpp'
                
                # Build description
                description_parts = []
                if port_type == 'trunk':
                    description_parts.append(f"Trunk (VLANs: {allowed_vlans})")
                elif port_type == 'access' and vlan:
                    description_parts.append(f"Access VLAN {vlan}")
                
                if voice_vlan:
                    description_parts.append(f"Voice VLAN {voice_vlan}")
                if poe_enabled:
                    description_parts.append("PoE Enabled")
                    
                description = " | ".join(description_parts) if description_parts else "Switch port"
                
                # Create or update interface
                interface, created = Interface.objects.update_or_create(
                    device=device,
                    name=port_id,
                    defaults={
                        'type': interface_type,
                        'description': description,
                        'enabled': enabled,
                        'mode': 'tagged-all' if port_type == 'trunk' else 'access',
                    }
                )
                
                # For access ports, assign untagged VLAN
                if port_type == 'access' and vlan:
                    try:
                        vlan_obj = VLAN.objects.filter(vid=vlan, site=device.site).first()
                        if vlan_obj:
                            interface.untagged_vlan = vlan_obj
                            interface.save()
                            logger.debug(f"Assigned VLAN {vlan} to {port_id} on {device.name}")
                    except Exception as e:
                        logger.debug(f"Could not assign VLAN {vlan} to {port_id}: {e}")
                
                if created:
                    logger.debug(f"✓ Created interface {port_id} on {device.name}")
                else:
                    logger.debug(f"✓ Updated interface {port_id} on {device.name}")
            
            logger.info(f"✓ Configured {len(ports)} switch ports for {device.name}")
            
        except Exception as e:
            logger.error(f"Error creating switch port interfaces for {device.name}: {e}")
    
    def _sync_device_interface(self, device: Device, meraki_device: Dict):
        """Sync primary interface for a device"""
        lan_ip = meraki_device.get('lanIp')
        mac = meraki_device.get('mac')
        product_type = meraki_device.get('productType', '')
        
        if not lan_ip:
            return
        
        # Determine interface type based on product
        interface_type = 'other'
        if product_type.startswith('MX'):
            interface_type = '1000base-t'  # Most MX appliances have gigabit
        elif product_type.startswith('MS'):
            interface_type = '1000base-t'  # Switches
        elif product_type.startswith('MR'):
            interface_type = 'ieee802.11ac'  # Wireless APs
        
        # Build interface description
        description = f"Management interface for {meraki_device.get('name', device.name)}"
        if meraki_device.get('firmware'):
            description += f" (Firmware: {meraki_device.get('firmware')})"
        
        # Create or update management interface
        interface, created = Interface.objects.get_or_create(
            device=device,
            name='Management',
            defaults={
                'type': interface_type,
                'mac_address': mac if mac else None,
                'description': description,
            }
        )
        
        # Update description if interface already exists
        if not created:
            interface.description = description
            if mac and not interface.mac_address:
                interface.mac_address = mac
            interface.save()
        
        # Create or update IP address
        try:
            ip_address, created = IPAddress.objects.get_or_create(
                address=f"{lan_ip}/32",
                defaults={
                    'status': 'active',
                    'dns_name': meraki_device.get('name', ''),
                    'description': f"Management IP for {device.name}",
                }
            )
            
            # Assign to interface if not already assigned
            if not created:
                if ip_address.assigned_object != interface:
                    ip_address.assigned_object = interface
                    ip_address.save()
            else:
                ip_address.assigned_object = interface
                ip_address.save()
                logger.debug(f"Created IP address {lan_ip} for {device.name}")
            
            # Set as primary IP
            if not device.primary_ip4:
                device.primary_ip4 = ip_address
                device.save()
                logger.debug(f"Set {lan_ip} as primary IP for {device.name}")
                
        except Exception as e:
            logger.warning(f"Could not create IP address {lan_ip} for device {device.name}: {e}")
    
    def _sync_switch_ports(self, device: Device, serial: str, meraki_tag: Tag):
        """Sync switch ports for MS devices"""
        try:
            ports = self.client.get_switch_ports(serial)
            if not ports:
                return
            
            logger.info(f"Syncing {len(ports)} switch ports for {device.name}")
            
            for port_data in ports:
                try:
                    port_id = port_data.get('portId', '')
                    port_name = port_data.get('name', f"Port {port_id}")
                    enabled = port_data.get('enabled', True)
                    port_type = port_data.get('type', 'access')
                    vlan = port_data.get('vlan')
                    voice_vlan = port_data.get('voiceVlan')
                    allowed_vlans = port_data.get('allowedVlans', '')
                    poe_enabled = port_data.get('poeEnabled', False)
                    link_negotiation = port_data.get('linkNegotiation', '')
                    
                    # Determine interface type based on link negotiation
                    interface_type = '1000base-t'  # Default to gigabit
                    if 'Auto negotiate' in str(link_negotiation):
                        interface_type = '1000base-t'
                    elif '10 Gigabit' in str(link_negotiation):
                        interface_type = '10gbase-t'
                    elif '100 Megabit' in str(link_negotiation):
                        interface_type = '100base-tx'
                    
                    # Build description
                    description_parts = []
                    if port_type == 'trunk':
                        description_parts.append(f"Trunk port")
                        if allowed_vlans:
                            description_parts.append(f"Allowed VLANs: {allowed_vlans}")
                    else:
                        description_parts.append(f"Access port")
                        if vlan:
                            description_parts.append(f"VLAN {vlan}")
                    
                    if voice_vlan:
                        description_parts.append(f"Voice VLAN {voice_vlan}")
                    if poe_enabled:
                        description_parts.append("PoE Enabled")
                    
                    description = " | ".join(description_parts) if description_parts else port_name
                    
                    # Determine mode
                    mode = ''
                    if port_type == 'trunk':
                        mode = 'tagged'
                    elif port_type == 'access':
                        mode = 'access'
                    
                    # Create or update interface
                    interface, created = Interface.objects.update_or_create(
                        device=device,
                        name=port_name,
                        defaults={
                            'type': interface_type,
                            'enabled': enabled,
                            'mode': mode,
                            'description': description,
                        }
                    )
                    
                    if created:
                        logger.debug(f"Created interface {port_name} on {device.name}")
                    
                    # Assign untagged VLAN for access ports
                    if port_type == 'access' and vlan:
                        # Find VLAN in the site's VLAN group
                        vlan_group_name = f"{device.site.name} VLANs"
                        vlan_obj = VLAN.objects.filter(
                            vid=vlan,
                            group__name=vlan_group_name
                        ).first()
                        
                        if vlan_obj:
                            interface.untagged_vlan = vlan_obj
                            interface.save()
                            logger.debug(f"Assigned VLAN {vlan} to interface {port_name}")
                    
                    # For trunk ports, assign tagged VLANs
                    if port_type == 'trunk' and allowed_vlans and allowed_vlans != 'all':
                        vlan_group_name = f"{device.site.name} VLANs"
                        # Parse allowed VLANs (can be ranges like "10-20,30,40-50")
                        vlan_ids = self._parse_vlan_list(allowed_vlans)
                        
                        tagged_vlans = VLAN.objects.filter(
                            vid__in=vlan_ids,
                            group__name=vlan_group_name
                        )
                        
                        if tagged_vlans.exists():
                            interface.tagged_vlans.set(tagged_vlans)
                            logger.debug(f"Assigned tagged VLANs to interface {port_name}: {allowed_vlans}")
                    
                    interface.tags.add(meraki_tag)
                    
                except Exception as e:
                    logger.warning(f"Could not sync port {port_data.get('portId')} on {device.name}: {e}")
                    
        except Exception as e:
            logger.debug(f"Could not fetch switch ports for {device.name}: {e}")
    
    def _parse_vlan_list(self, vlan_string: str) -> List[int]:
        """Parse VLAN list string like '10-20,30,40-50' into list of VLAN IDs"""
        vlan_ids = []
        if not vlan_string or vlan_string == 'all':
            return vlan_ids
        
        try:
            for part in vlan_string.split(','):
                part = part.strip()
                if '-' in part:
                    # Range like "10-20"
                    start, end = part.split('-')
                    vlan_ids.extend(range(int(start), int(end) + 1))
                else:
                    # Single VLAN
                    vlan_ids.append(int(part))
        except Exception as e:
            logger.warning(f"Could not parse VLAN list '{vlan_string}': {e}")
        
        return vlan_ids
    
    def _sync_vlans(self, network_id: str, site_name: str, meraki_tag: Tag):
        """Sync VLANs for a network - now works in all sync modes via staging"""
        try:
            vlans = self.client.get_appliance_vlans(network_id)
        except Exception as e:
            # Network might not have MX appliance or VLANs configured
            logger.debug(f"Could not fetch VLANs for network {network_id}: {e}")
            return
        
        if not vlans:
            return
        
        logger.info(f"Syncing {len(vlans)} VLANs for {site_name}")
        self.sync_log.add_progress_log(f"Syncing {len(vlans)} VLANs for {site_name}", "info")
        
        # Get plugin settings for transformations
        plugin_settings = PluginSettings.get_settings()
        
        for vlan_data in vlans:
            vlan_id = vlan_data.get('id')
            vlan_name = vlan_data.get('name', f"VLAN {vlan_id}")
            
            # Apply VLAN name transformation
            vlan_name = plugin_settings.transform_name(vlan_name, plugin_settings.vlan_name_transform)
            
            try:
                # In review/dry-run mode, site might not exist in NetBox yet (only in staging)
                # So we check but don't skip - just use the site name
                site_obj = Site.objects.filter(name=site_name).first()
                    
                vlan_group_name = f"{site_name} VLANs"
                vlan_group = VLANGroup.objects.filter(name=vlan_group_name).first() if site_obj else None
                
                existing_vlan = None
                if vlan_group:
                    existing_vlan = VLAN.objects.filter(vid=vlan_id, group=vlan_group).first()
                
                action_type = 'update' if existing_vlan else 'create'
                current_data = None
                
                if existing_vlan:
                    current_data = {
                        'vid': existing_vlan.vid,
                        'name': existing_vlan.name,
                        'description': existing_vlan.description,
                        'site': site_name,
                    }
                
                # Prepare VLAN data
                proposed_data = {
                    'vid': vlan_id,
                    'name': vlan_name,
                    'site': site_name,
                    'description': f"Subnet: {vlan_data.get('subnet', 'N/A')}",
                    'status': 'active',
                }
                
                # All sync modes: Create review item (staging) first
                review_item = self._create_review_item(
                    item_type='vlan',
                    action_type=action_type,
                    object_name=vlan_name,
                    object_identifier=f"{site_name}-VLAN-{vlan_id}",
                    proposed_data=proposed_data,
                    current_data=current_data
                )
                
                
                if self.sync_mode == 'auto' and review_item:
                    try:
                        review_item.status = 'approved'
                        review_item.save()
                        self.apply_review_item(review_item)
                        review_item.status = 'applied'
                        review_item.save()
                        self.sync_log.add_progress_log(f"✓ Created/Updated VLAN {vlan_id}: {vlan_name} at {site_name}", "success")
                    except Exception as e:
                        review_item.status = 'failed'
                        review_item.error_message = str(e)
                        review_item.save()
                        error_msg = f"Failed to apply VLAN {vlan_id} at {site_name}: {e}"
                        logger.error(error_msg)
                        self.sync_log.add_progress_log(f"✗ {error_msg}", "error")
                    self.stats['vlans'] += 1
                else:
                    
                    self.stats['vlans'] += 1
                
            except Exception as e:
                logger.warning(f"Could not sync VLAN {vlan_id}: {e}")
    
    def _sync_prefixes(self, network_id: str, site_name: str, meraki_tag: Tag):
        """Sync prefixes/subnets for a network - now works in all sync modes via staging"""
        try:
            subnets = self.client.get_appliance_subnets(network_id)
        except Exception as e:
            # Network might not have MX appliance or subnets configured
            logger.debug(f"Could not fetch subnets for network {network_id}: {e}")
            return
        
        if not subnets:
            return
        
        logger.info(f"Syncing {len(subnets)} prefixes for {site_name}")
        self.sync_log.add_progress_log(f"Syncing {len(subnets)} prefixes/subnets for {site_name}", "info")
        
        for subnet_data in subnets:
            subnet = subnet_data.get('subnet')
            vlan_id = subnet_data.get('vlan_id')
            vlan_name = subnet_data.get('vlan_name', '')
            
            if not subnet:
                continue
            
            try:
                # Validate subnet format
                network = ip_network(subnet, strict=False)
                
                # Check if prefix should be synced based on filter rules
                if not PrefixFilterRule.should_sync_prefix(str(network)):
                    logger.info(f"⊗ Skipping prefix {network} - excluded by filter rules")
                    continue
                
                # Check if prefix exists
                existing_prefix = Prefix.objects.filter(prefix=str(network)).first()
                action_type = 'update' if existing_prefix else 'create'
                current_data = None
                
                if existing_prefix:
                    current_data = {
                        'prefix': str(existing_prefix.prefix),
                        'site': existing_prefix.site.name if existing_prefix.site else None,
                        'description': existing_prefix.description,
                        'status': existing_prefix.status,
                    }
                
                # Prepare prefix data
                proposed_data = {
                    'prefix': str(network),
                    'site': site_name,
                    'vlan': f"VLAN {vlan_id}" if vlan_id else None,
                    'status': 'active',
                    'description': f"VLAN {vlan_id}: {vlan_name}" if vlan_id else "Meraki Subnet",
                }
                
                # All sync modes: Create review item (staging) first
                review_item = self._create_review_item(
                    item_type='prefix',
                    action_type=action_type,
                    object_name=str(network),
                    object_identifier=str(network),
                    proposed_data=proposed_data,
                    current_data=current_data
                )
                
                
                if self.sync_mode == 'auto' and review_item:
                    try:
                        review_item.status = 'approved'
                        review_item.save()
                        self.apply_review_item(review_item)
                        review_item.status = 'applied'
                        review_item.save()
                        self.sync_log.add_progress_log(f"✓ Created/Updated prefix: {network} at {site_name}", "success")
                    except Exception as e:
                        review_item.status = 'failed'
                        review_item.error_message = str(e)
                        review_item.save()
                        error_msg = f"Failed to apply prefix {network} at {site_name}: {e}"
                        logger.error(error_msg)
                        self.sync_log.add_progress_log(f"✗ {error_msg}", "error")
                    self.stats['prefixes'] += 1
                else:
                    
                    self.stats['prefixes'] += 1
                
            except Exception as e:
                logger.warning(f"Could not sync prefix {subnet}: {e}")
    
    def _create_review_item(self, item_type: str, action_type: str, object_name: str, 
                           object_identifier: str, proposed_data: Dict, current_data: Optional[Dict] = None):
        """Create a review item for manual approval with detailed preview"""
        if not self.review:
            return None
        
        # Generate human-readable preview and related object info
        preview_display = ""
        related_object_info = {}
        
        if item_type == 'site':
            preview_display = f"**Name:** {proposed_data.get('name', 'N/A')}\n"
            preview_display += f"**Network ID:** {proposed_data.get('network_id', 'N/A')}\n"
            preview_display += f"**Time Zone:** {proposed_data.get('timezone', 'N/A')}\n"
            if proposed_data.get('description'):
                preview_display += f"**Description:** {proposed_data['description']}\n"
            related_object_info['network_id'] = proposed_data.get('network_id')
            
        elif item_type == 'device':
            preview_display = f"**Name:** {proposed_data.get('name', 'N/A')}\n"
            preview_display += f"**Serial:** {proposed_data.get('serial', 'N/A')}\n"
            preview_display += f"**Model:** {proposed_data.get('model', 'N/A')}\n"
            preview_display += f"**Manufacturer:** {proposed_data.get('manufacturer', 'N/A')}\n"
            preview_display += f"**Device Role:** {proposed_data.get('role', 'N/A')}\n"
            preview_display += f"**Site:** {proposed_data.get('site', 'N/A')}\n"
            preview_display += f"**Status:** {proposed_data.get('status', 'active')}\n"
            preview_display += f"**Product Type:** {proposed_data.get('product_type', 'N/A')}\n"
            preview_display += f"**MAC Address:** {proposed_data.get('mac', 'N/A')}\n"
            preview_display += f"**LAN IP:** {proposed_data.get('lan_ip', 'N/A')}\n"
            preview_display += f"**Firmware:** {proposed_data.get('firmware', 'N/A')}\n"
            related_object_info = {
                'site': proposed_data.get('site'),
                'role': proposed_data.get('role'),
                'model': proposed_data.get('model'),
                'manufacturer': proposed_data.get('manufacturer'),
            }
            
        elif item_type == 'device_type':
            preview_display = f"**Model:** {proposed_data.get('model', 'N/A')}\n"
            preview_display += f"**Manufacturer:** {proposed_data.get('manufacturer', 'N/A')}\n"
            preview_display += f"**Part Number:** {proposed_data.get('part_number', 'N/A')}\n"
            preview_display += f"**Slug:** {proposed_data.get('slug', 'N/A')}\n"
            related_object_info = {
                'manufacturer': proposed_data.get('manufacturer'),
            }
            
        elif item_type == 'vlan':
            preview_display = f"**Name:** {proposed_data.get('name', 'N/A')}\n"
            preview_display += f"**VID:** {proposed_data.get('vid', 'N/A')}\n"
            preview_display += f"**Site:** {proposed_data.get('site', 'N/A')}\n"
            if proposed_data.get('description'):
                preview_display += f"**Description:** {proposed_data['description']}\n"
            related_object_info = {
                'site': proposed_data.get('site'),
            }
            
        elif item_type == 'prefix':
            preview_display = f"**Prefix:** {proposed_data.get('prefix', 'N/A')}\n"
            preview_display += f"**Site:** {proposed_data.get('site', 'N/A')}\n"
            preview_display += f"**VLAN:** {proposed_data.get('vlan', 'N/A')}\n"
            preview_display += f"**Status:** {proposed_data.get('status', 'active')}\n"
            if proposed_data.get('description'):
                preview_display += f"**Description:** {proposed_data['description']}\n"
            related_object_info = {
                'site': proposed_data.get('site'),
                'vlan': proposed_data.get('vlan'),
            }
            
        elif item_type == 'interface':
            preview_display = f"**Name:** {proposed_data.get('name', 'N/A')}\n"
            preview_display += f"**Device:** {proposed_data.get('device', 'N/A')}\n"
            preview_display += f"**Type:** {proposed_data.get('type', 'N/A')}\n"
            if proposed_data.get('description'):
                preview_display += f"**Description:** {proposed_data['description']}\n"
            related_object_info = {
                'device': proposed_data.get('device'),
                'device_serial': proposed_data.get('device_serial'),
            }
        
        elif item_type == 'ip_address':
            preview_display = f"**Address:** {proposed_data.get('address', 'N/A')}\n"
            preview_display += f"**Device:** {proposed_data.get('device', 'N/A')}\n"
            preview_display += f"**Interface:** {proposed_data.get('interface', 'N/A')}\n"
            preview_display += f"**Status:** {proposed_data.get('status', 'active')}\n"
            if proposed_data.get('description'):
                preview_display += f"**Description:** {proposed_data['description']}\n"
            related_object_info = {
                'device': proposed_data.get('device'),
                'device_serial': proposed_data.get('device_serial'),
                'interface': proposed_data.get('interface'),
            }
            
        elif item_type == 'ssid':
            preview_display = f"**SSID Name:** {proposed_data.get('name', 'N/A')}\n"
            preview_display += f"**Network:** {proposed_data.get('network', 'N/A')}\n"
            preview_display += f"**Enabled:** {proposed_data.get('enabled', False)}\n"
            if proposed_data.get('auth_mode'):
                preview_display += f"**Auth Mode:** {proposed_data['auth_mode']}\n"
            related_object_info = {
                'network': proposed_data.get('network'),
            }
        
        return ReviewItem.objects.create(
            review=self.review,
            item_type=item_type,
            action_type=action_type,
            object_name=object_name,
            object_identifier=object_identifier,
            proposed_data=proposed_data,
            current_data=current_data,
            preview_display=preview_display,
            related_object_info=related_object_info,
            status='pending'
        )
    
    def _should_execute(self) -> bool:
        """Check if sync should actually modify database"""
        return self.sync_mode == 'auto'
    
    def apply_review_item(self, item: 'ReviewItem'):
        """Apply an approved review item"""
        item_type = item.item_type
        # Use editable_data if it exists, otherwise use proposed_data
        data = item.get_final_data()
        
        # Get plugin settings for tags
        plugin_settings = PluginSettings.get_settings()
        
        try:
            if item_type == 'site':
                # Generate slug for site
                import re
                slug = re.sub(r'[^a-z0-9-]+', '-', data['name'].lower()).strip('-')
                if not slug:
                    slug = f"site-{data.get('network_id', 'unknown')}"
                
                site, created = Site.objects.update_or_create(
                    name=data['name'],
                    defaults={
                        'slug': slug,
                        'description': data.get('description', ''),
                        'comments': data.get('comments', ''),
                    }
                )
                logger.info(f"{'Created' if created else 'Updated'} site: {data['name']}")
                # Apply site tags (only if configured)
                tag_names = plugin_settings.get_tags_for_object_type('site')
                if tag_names:
                    for tag_name in tag_names:
                        tag, _ = Tag.objects.get_or_create(name=tag_name, defaults={'slug': tag_name.lower().replace(' ', '-')})
                        site.tags.add(tag)
                
                # Track synced site ID to prevent cleanup deletion
                self.synced_object_ids['sites'].add(site.id)
                    
            elif item_type == 'device':
                # Ensure site exists
                try:
                    site = Site.objects.get(name=data['site'])
                except Site.DoesNotExist:
                    raise Exception(f"Site '{data['site']}' does not exist. Please ensure sites are created first.")
                
                manufacturer, _ = Manufacturer.objects.get_or_create(
                    name=data.get('manufacturer', 'Cisco Meraki'),
                    defaults={'slug': 'cisco-meraki'}
                )
                
                # Generate proper slug for device type (handle special characters)
                import re
                device_type_slug = re.sub(r'[^a-z0-9-]+', '-', data['model'].lower()).strip('-')
                if not device_type_slug:
                    device_type_slug = f"device-{data['serial'].lower()}"
                
                device_type, created = DeviceType.objects.get_or_create(
                    model=data['model'],
                    manufacturer=manufacturer,
                    defaults={
                        'slug': device_type_slug,
                        'part_number': data['model']  # Use model as part number
                    }
                )
                
                # Ensure part_number is always set (update existing device types if blank)
                if not device_type.part_number:
                    device_type.part_number = data['model']
                    device_type.save()
                    logger.info(f"Updated part_number for device type '{data['model']}'")

                
                # Get or create device role with product-type based defaults
                product_type = data.get('product_type', '')
                role_name = data['role']
                
                logger.info(f"Device role assignment: product_type='{product_type}', role_name='{role_name}'")
                
                # Generate proper slug for device role
                device_role_slug = re.sub(r'[^a-z0-9-]+', '-', role_name.lower()).strip('-')
                if not device_role_slug:
                    device_role_slug = 'unknown-role'
                
                # Set color based on product type
                role_color_map = {
                    'MX': 'f44336',  # Red for security appliances
                    'MS': '2196f3',  # Blue for switches
                    'MR': '4caf50',  # Green for wireless APs
                    'MG': 'ff9800',  # Orange for cellular gateways
                    'MV': '9c27b0',  # Purple for cameras
                    'MT': '00bcd4',  # Cyan for sensors
                }
                product_prefix = product_type[:2].upper() if len(product_type) >= 2 else ''
                role_color = role_color_map.get(product_prefix, '607d8b')  # Grey for unknown
                
                logger.info(f"Creating/getting role '{role_name}' with color '{role_color}' for product prefix '{product_prefix}'")
                
                device_role, _ = DeviceRole.objects.get_or_create(
                    name=role_name,
                    defaults={
                        'slug': device_role_slug,
                        'color': role_color
                    }
                )
                
                device, created = Device.objects.update_or_create(
                    serial=data['serial'],
                    defaults={
                        'name': data['name'],
                        'device_type': device_type,
                        'role': device_role,
                        'site': site,
                        'status': data.get('status', 'active'),
                        'comments': data.get('comments', ''),
                    }
                )
                
                # Set custom field data if provided
                if 'custom_field_data' in data and data['custom_field_data']:
                    device.custom_field_data.update(data['custom_field_data'])
                    device.save()
                
                logger.info(f"{'Created' if created else 'Updated'} device: {data['name']} (Serial: {data['serial']})") 
                # Apply device tags (only if configured)
                tag_names = plugin_settings.get_tags_for_object_type('device')
                if tag_names:
                    for tag_name in tag_names:
                        tag, _ = Tag.objects.get_or_create(name=tag_name, defaults={'slug': tag_name.lower().replace(' ', '-')})
                        device.tags.add(tag)
                
                # Track synced device ID to prevent cleanup deletion
                self.synced_object_ids['devices'].add(device.id)
                    
            elif item_type == 'vlan':
                try:
                    site = Site.objects.get(name=data['site'])
                except Site.DoesNotExist:
                    raise Exception(f"Site '{data['site']}' does not exist. Please ensure sites are created first.")
                    
                # Generate proper slug
                import re
                vlan_group_slug = re.sub(r'[^a-z0-9-]+', '-', site.name.lower()).strip('-')
                if not vlan_group_slug:
                    vlan_group_slug = f"site-{site.id}"
                vlan_group_slug = f"{vlan_group_slug}-vlans"
                
                vlan_group, _ = VLANGroup.objects.get_or_create(
                    name=f"{site.name} VLANs",
                    defaults={'slug': vlan_group_slug}
                )
                vlan, created = VLAN.objects.update_or_create(
                    vid=data['vid'],
                    group=vlan_group,
                    defaults={
                        'name': data['name'],
                        'status': 'active',
                        'description': data.get('description', ''),
                    }
                )
                logger.info(f"{'Created' if created else 'Updated'} VLAN {data['vid']}: {data['name']}")
                # Apply VLAN tags (only if configured)
                tag_names = plugin_settings.get_tags_for_object_type('vlan')
                if tag_names:
                    for tag_name in tag_names:
                        tag, _ = Tag.objects.get_or_create(name=tag_name, defaults={'slug': tag_name.lower().replace(' ', '-')})
                        vlan.tags.add(tag)
                
                # Track synced VLAN ID to prevent cleanup deletion
                self.synced_object_ids['vlans'].add(vlan.id)
                    
            elif item_type == 'prefix':
                try:
                    site = Site.objects.get(name=data['site'])
                except Site.DoesNotExist:
                    raise Exception(f"Site '{data['site']}' does not exist. Please ensure sites are created first.")
                
                # Try to find VLAN by VID if specified
                vlan_obj = None
                if data.get('vlan'):
                    # Extract VLAN ID from string like "VLAN 101"
                    vlan_id_str = data['vlan']
                    if 'VLAN' in vlan_id_str:
                        vlan_id = int(vlan_id_str.split()[-1])
                        # Find VLAN group for this site
                        vlan_group = VLANGroup.objects.filter(name=f"{site.name} VLANs").first()
                        if vlan_group:
                            vlan_obj = VLAN.objects.filter(vid=vlan_id, group=vlan_group).first()
                            if vlan_obj:
                                logger.debug(f"Found VLAN {vlan_id} for prefix {data['prefix']}")
                            else:
                                logger.debug(f"VLAN {vlan_id} not found in group {vlan_group.name}")
                    
                # For NetBox 4.x: Check if prefix exists first
                existing_prefix = Prefix.objects.filter(prefix=data['prefix']).first()
                
                if existing_prefix:
                    # Update existing prefix
                    existing_prefix.status = 'active'
                    existing_prefix.description = data.get('description', '')
                    existing_prefix.vlan = vlan_obj
                    # NetBox 4.x uses scope_id and scope_type for site relationship
                    if hasattr(existing_prefix, 'scope_id'):
                        # NetBox 4.x approach
                        site_content_type = ContentType.objects.get_for_model(site)
                        existing_prefix.scope_type = site_content_type
                        existing_prefix.scope_id = site.id
                    else:
                        # Older NetBox with direct site ForeignKey
                        existing_prefix.site = site
                    existing_prefix.save()
                    prefix = existing_prefix
                    created = False
                else:
                    # Create new prefix with site relationship
                    if hasattr(Prefix, 'scope_id'):
                        # NetBox 4.x approach
                        site_content_type = ContentType.objects.get_for_model(site)
                        prefix = Prefix.objects.create(
                            prefix=data['prefix'],
                            status='active',
                            description=data.get('description', ''),
                            vlan=vlan_obj,
                            scope_type=site_content_type,
                            scope_id=site.id
                        )
                    else:
                        # Older NetBox with direct site ForeignKey
                        prefix = Prefix.objects.create(
                            prefix=data['prefix'],
                            status='active',
                            description=data.get('description', ''),
                            vlan=vlan_obj,
                            site=site
                        )
                    created = True
                
                logger.info(f"{'Created' if created else 'Updated'} prefix: {data['prefix']} at site {site.name}" + (f" with VLAN {vlan_obj.vid}" if vlan_obj else ""))
                # Apply prefix tags (only if configured)
                tag_names = plugin_settings.get_tags_for_object_type('prefix')
                if tag_names:
                    for tag_name in tag_names:
                        tag, _ = Tag.objects.get_or_create(name=tag_name, defaults={'slug': tag_name.lower().replace(' ', '-')})
                        prefix.tags.add(tag)
                
                # Track synced prefix ID to prevent cleanup deletion
                self.synced_object_ids['prefixes'].add(prefix.id)
            
            elif item_type == 'interface':
                # Find device by serial
                device = Device.objects.get(serial=data.get('device_serial'))
                interface, _ = Interface.objects.get_or_create(
                    device=device,
                    name=data['name'],
                    defaults={
                        'type': data.get('type', 'other'),
                        'description': data.get('description', ''),
                        'enabled': data.get('enabled', True),
                    }
                )
                logger.info(f"Created/Updated interface {data['name']} on device {device.name}")
            
            elif item_type == 'ip_address':
                # Find device and interface
                device = Device.objects.get(serial=data.get('device_serial'))
                interface = Interface.objects.get(device=device, name=data.get('interface'))
                
                ip_address, _ = IPAddress.objects.get_or_create(
                    address=data['address'],
                    defaults={
                        'description': data.get('description', ''),
                        'status': data.get('status', 'active'),
                    }
                )
                
                # Assign to interface
                if not ip_address.assigned_object:
                    ip_address.assigned_object = interface
                    ip_address.save()
                    logger.info(f"Assigned IP {data['address']} to interface {data.get('interface')} on device {device.name}")
            
            logger.info(f"Applied review item: {item.action_type} {item.item_type} - {item.object_name}")
            
        except Exception as e:
            logger.error(f"Failed to apply review item {item.item_type} - {item.object_name}: {e}")
            raise
    
    def _cleanup_orphaned_objects(self, meraki_tag: Tag):
        """Delete objects with meraki tag that were not synced in this run
        
        IMPORTANT: Only cleanup objects within sites that were synced in this run.
        This prevents deleting objects from other networks when doing selective sync.
        
        Order matters: Delete in reverse dependency order to avoid foreign key constraint errors
        1. Prefixes (no dependencies)
        2. VLANs (no dependencies)
        3. Devices (depend on sites)
        4. Sites (last, depended on by devices)
        """
        logger.info("Checking for orphaned objects to clean up...")
        
        # Get the sites that were synced in this run
        synced_sites = Site.objects.filter(id__in=self.synced_object_ids['sites'])
        
        if not synced_sites.exists():
            logger.info("No sites were synced, skipping orphaned object cleanup")
            return
        
        logger.info(f"Will only cleanup orphaned objects within {synced_sites.count()} synced site(s)")
        
        # Clean up prefixes first - only within synced sites
        all_meraki_prefixes = Prefix.objects.filter(tags=meraki_tag)
        # Filter to only prefixes that belong to synced sites
        synced_site_prefixes = all_meraki_prefixes.filter(
            scope_type=ContentType.objects.get_for_model(Site),
            scope_id__in=[site.id for site in synced_sites]
        )
        orphaned_prefixes = synced_site_prefixes.exclude(id__in=self.synced_object_ids['prefixes'])
        if orphaned_prefixes.exists():
            count = orphaned_prefixes.count()
            for prefix in orphaned_prefixes:
                logger.info(f"Deleting orphaned prefix: {prefix.prefix} (ID: {prefix.id})")
            orphaned_prefixes.delete()
            self.stats['deleted_prefixes'] = count
            logger.info(f"Deleted {count} orphaned prefix(es)")
        
        # Clean up VLANs - only within synced sites
        all_meraki_vlans = VLAN.objects.filter(tags=meraki_tag)
        synced_site_vlans = all_meraki_vlans.filter(site__in=synced_sites)
        orphaned_vlans = synced_site_vlans.exclude(id__in=self.synced_object_ids['vlans'])
        if orphaned_vlans.exists():
            count = orphaned_vlans.count()
            for vlan in orphaned_vlans:
                logger.info(f"Deleting orphaned VLAN: {vlan.name} (VID: {vlan.vid}, ID: {vlan.id})")
            orphaned_vlans.delete()
            self.stats['deleted_vlans'] = count
            logger.info(f"Deleted {count} orphaned VLAN(s)")
        
        # Clean up devices (before sites, as devices depend on sites) - only within synced sites
        all_meraki_devices = Device.objects.filter(tags=meraki_tag)
        synced_site_devices = all_meraki_devices.filter(site__in=synced_sites)
        orphaned_devices = synced_site_devices.exclude(id__in=self.synced_object_ids['devices'])
        if orphaned_devices.exists():
            count = orphaned_devices.count()
            for device in orphaned_devices:
                logger.info(f"Deleting orphaned device: {device.name} (Serial: {device.serial}, ID: {device.id})")
            orphaned_devices.delete()
            self.stats['deleted_devices'] = count
            logger.info(f"Deleted {count} orphaned device(s)")
        
        # Clean up sites last (depended on by devices) - only sites that were synced
        all_meraki_sites = Site.objects.filter(tags=meraki_tag)
        # Only consider sites that were part of this sync run for deletion
        synced_meraki_sites = all_meraki_sites.filter(id__in=[site.id for site in synced_sites])
        orphaned_sites = synced_meraki_sites.exclude(id__in=self.synced_object_ids['sites'])
        if orphaned_sites.exists():
            count = orphaned_sites.count()
            for site in orphaned_sites:
                logger.info(f"Deleting orphaned site: {site.name} (ID: {site.id})")
            orphaned_sites.delete()
            self.stats['deleted_sites'] = count
            logger.info(f"Deleted {count} orphaned site(s)")
        
        logger.info("Orphaned object cleanup complete")

