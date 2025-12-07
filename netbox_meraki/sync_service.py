"""
Sync service for importing Meraki data into NetBox
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional
from ipaddress import ip_network

from django.db import transaction
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from dcim.models import Site, Device, DeviceType, DeviceRole, Manufacturer, Interface
from ipam.models import VLAN, VLANGroup, Prefix, IPAddress
from extras.models import Tag, CustomField

from .meraki_client import MerakiAPIClient
from .models import SyncLog, PluginSettings, SiteNameRule, SyncReview, ReviewItem


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
        # Track all synced object IDs to detect orphans
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
        
        # Create firmware version custom field
        firmware_field, created = CustomField.objects.get_or_create(
            name='meraki_firmware',
            defaults={
                'label': 'Meraki Firmware',
                'type': 'text',
                'description': 'Firmware version from Meraki Dashboard',
                'weight': 100,
            }
        )
        if created:
            # NetBox 4.x uses object_types instead of content_types
            firmware_field.object_types.set([device_ct])
            logger.info("Created custom field: meraki_firmware")
        elif device_ct not in firmware_field.object_types.all():
            firmware_field.object_types.add(device_ct)
        
        # Create SSID custom field for wireless APs
        ssid_field, created = CustomField.objects.get_or_create(
            name='meraki_ssids',
            defaults={
                'label': 'Meraki SSIDs',
                'type': 'text',
                'description': 'SSIDs broadcast by this access point',
                'weight': 101,
            }
        )
        if created:
            # NetBox 4.x uses object_types instead of content_types
            ssid_field.object_types.set([device_ct])
            logger.info("Created custom field: meraki_ssids")
        elif device_ct not in ssid_field.object_types.all():
            ssid_field.object_types.add(device_ct)
    
    def _cleanup_old_review_items(self):
        """Clean up old review items and completed reviews before starting new sync"""
        from datetime import timedelta
        from django.utils import timezone
        
        # Delete review items from completed/applied reviews older than 7 days
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
        
        # Also delete orphaned review items (reviews without sync logs)
        orphaned_reviews = SyncReview.objects.filter(sync_log__isnull=True)
        for review in orphaned_reviews:
            review.delete()
    
    def sync_all(self) -> SyncLog:
        """
        Perform full synchronization from Meraki to NetBox
        
        Returns:
            SyncLog instance with results
        """
        start_time = datetime.now()
        
        # Clean up old review items from previous syncs
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
        
        # Create review session if needed
        if self.sync_mode in ['review', 'dry_run']:
            self.review = SyncReview.objects.create(
                sync_log=self.sync_log,
                status='pending'
            )
        
        try:
            logger.info("Starting Meraki synchronization")
            self.sync_log.add_progress_log("Starting Meraki synchronization", "info")
            self.sync_log.update_progress("Initializing sync", 0)
            
            # Get or create Meraki tag
            meraki_tag, _ = Tag.objects.get_or_create(
                name='Meraki',
                defaults={'description': 'Synced from Cisco Meraki Dashboard'}
            )
            
            # Get all organizations
            self.sync_log.add_progress_log("Fetching organizations from Meraki Dashboard", "info")
            organizations = self.client.get_organizations()
            logger.info(f"Found {len(organizations)} organizations")
            self.sync_log.add_progress_log(f"Found {len(organizations)} organizations", "info")
            
            total_orgs = len(organizations)
            for idx, org in enumerate(organizations):
                # Check for cancellation
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
                    self._sync_organization(org, meraki_tag)
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
    
    def _sync_organization(self, org: Dict, meraki_tag: Tag):
        """Sync a single organization"""
        org_id = org['id']
        org_name = org['name']
        
        logger.info(f"Syncing organization: {org_name}")
        
        # Get networks for this organization
        self.sync_log.add_progress_log(f"Fetching networks from organization: {org_name}", "info")
        networks = self.client.get_networks(org_id)
        logger.info(f"Found {len(networks)} networks in {org_name}")
        self.sync_log.add_progress_log(f"Found {len(networks)} networks in {org_name}", "info")
        
        for network in networks:
            try:
                self._sync_network(network, org_name, meraki_tag)
                self.stats['networks'] += 1
            except Exception as e:
                error_msg = f"Error syncing network {network.get('name')}: {str(e)}"
                logger.error(error_msg)
                self.errors.append(error_msg)
    
    def _sync_network(self, network: Dict, org_name: str, meraki_tag: Tag):
        """Sync a single network as a Site"""
        network_id = network['id']
        network_name = network['name']
        
        logger.info(f"Syncing network: {network_name}")
        
        # Get devices in this network first to check if we should create the site
        self.sync_log.add_progress_log(f"Fetching devices from network: {network_name}", "info")
        devices = self.client.get_devices(network_id)
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
        
        # Auto mode: Immediately approve and apply
        if self.sync_mode == 'auto' and review_item:
            review_item.status = 'approved'
            review_item.save()
            self.apply_review_item(review_item)
            site = Site.objects.get(name=site_name)
            self.stats['sites'] += 1
            self.sync_log.add_progress_log(f"✓ Created/Updated site: {site_name}", "success")
        else:
            # Review/Dry-run mode: Use existing site or site name for device references
            site = existing_site if existing_site else site_name
        
        # Process devices
        for device in devices:
            try:
                self._sync_device(device, site, meraki_tag)
                self.stats['devices'] += 1
            except Exception as e:
                error_msg = f"Error syncing device {device.get('name', device.get('serial'))}: {str(e)}"
                logger.error(error_msg)
                self.errors.append(error_msg)
        
        # Sync VLANs and prefixes (now works in all modes via staging)
        # Pass site name string so it works in review/dry-run mode
        site_name_for_sync = site.name if isinstance(site, Site) else site
        
        # Sync VLANs for this network
        try:
            self._sync_vlans(network_id, site_name_for_sync, meraki_tag)
        except Exception as e:
            error_msg = f"Error syncing VLANs for network {network_name}: {str(e)}"
            logger.error(error_msg)
            self.errors.append(error_msg)
        
        # Sync prefixes for this network
        try:
            self._sync_prefixes(network_id, site_name_for_sync, meraki_tag)
        except Exception as e:
            error_msg = f"Error syncing prefixes for network {network_name}: {str(e)}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            logger.info(f"Skipping VLANs/prefixes for new site '{site_name}' in review mode - will be synced after site is approved")
    
    def _sync_device(self, device: Dict, site: Site, meraki_tag: Tag):
        """Sync a single device"""
        serial = device['serial']
        name = device.get('name') or serial  # Use serial if name is None or empty
        model = device.get('model', 'Unknown')
        product_type = device.get('productType', '')
        notes = device.get('notes', '')
        tags = device.get('tags', [])
        address = device.get('address', '')
        
        logger.debug(f"Syncing device: {name} ({serial})")
        
        # Get plugin settings
        plugin_settings = PluginSettings.get_settings()
        
        # Apply device name transformation
        name = plugin_settings.transform_name(name, plugin_settings.device_name_transform)
        
        # Get or create manufacturer
        manufacturer, created = Manufacturer.objects.get_or_create(
            name='Cisco Meraki'
        )
        if created:
            logger.info("Created manufacturer: Cisco Meraki")
        
        # Get or create device type
        device_type, created = DeviceType.objects.get_or_create(
            model=model,
            manufacturer=manufacturer,
            defaults={
                'slug': model.lower().replace(' ', '-'),
                'part_number': model,  # Use model as part number
            }
        )
        if created:
            logger.info(f"Created device type: {model} with part number: {model}")
            self.sync_log.add_progress_log(f"Auto-created device type: {model}", "info")
        else:
            # Update part_number if it's missing
            if not device_type.part_number:
                device_type.part_number = model
                device_type.save()
                logger.info(f"Updated device type {model} with part number: {model}")
        
        # Get device role based on product type from settings
        role_name = plugin_settings.get_device_role_for_product(product_type)
        
        # Get or create device role
        device_role, created = DeviceRole.objects.get_or_create(
            name=role_name,
            defaults={
                'slug': role_name.lower().replace(' ', '-'),
                'color': '2196f3',
            }
        )
        
        if created and plugin_settings.auto_create_device_roles:
            logger.info(f"Created device role: {role_name}")
        
        # Get site name - handle both Site object and string
        site_name = site.name if hasattr(site, 'name') else site
        
        # Prepare proposed data
        proposed_data = {
            'name': name,
            'serial': serial,
            'model': model,
            'manufacturer': 'Cisco Meraki',
            'role': role_name,
            'site': site_name,
            'status': 'active' if device.get('status') != 'offline' else 'offline',
            'product_type': product_type,
            'mac': device.get('mac', 'N/A'),
            'lan_ip': device.get('lanIp', 'N/A'),
            'firmware': device.get('firmware', 'N/A'),
            'comments': f"MAC: {device.get('mac', 'N/A')}\\n"
                       f"LAN IP: {device.get('lanIp', 'N/A')}\\n"
                       f"Firmware: {device.get('firmware', 'N/A')}\\n"
                       f"Product Type: {product_type}",
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
                'role': existing_device.device_role.name,
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
        
        # Auto mode: Immediately approve and apply
        if self.sync_mode == 'auto' and review_item:
            review_item.status = 'approved'
            review_item.save()
            self.apply_review_item(review_item)
            self.sync_log.add_progress_log(f"✓ Created/Updated device: {name} (Serial: {serial})", "success")
            return
        
        # Review/Dry-run mode: Item stays pending in staging table
        return
    
    def _sync_device_ssids(self, device: Device, meraki_device: Dict):
        """Fetch and store SSIDs for wireless access points"""
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
                    # Filter enabled SSIDs and get their names
                    enabled_ssids = [
                        plugin_settings.transform_name(
                            ssid.get('name', f"SSID {ssid.get('number', '')}"),
                            plugin_settings.ssid_name_transform
                        )
                        for ssid in ssids
                        if ssid.get('enabled', False)
                    ]
                    if enabled_ssids:
                        ssid_list = ', '.join(enabled_ssids)
                        device.custom_field_data['meraki_ssids'] = ssid_list
                        self.stats['ssids'] += len(enabled_ssids)
                        logger.debug(f"Added SSIDs to AP {device.name}: {ssid_list}")
            except Exception as e:
                logger.debug(f"Could not fetch SSIDs for AP {device.name}: {e}")
        except Exception as e:
            logger.warning(f"Error syncing SSIDs for device {device.name}: {e}")
    
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
                # Check if VLAN exists
                site_obj = Site.objects.filter(name=site_name).first()
                if not site_obj:
                    logger.debug(f"Site {site_name} not found, skipping VLAN {vlan_id} in review/dry-run mode")
                    continue
                    
                vlan_group_name = f"{site_name} VLANs"
                vlan_group = VLANGroup.objects.filter(name=vlan_group_name).first()
                
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
                
                # Auto mode: Immediately approve and apply
                if self.sync_mode == 'auto' and review_item:
                    review_item.status = 'approved'
                    review_item.save()
                    self.apply_review_item(review_item)
                    self.sync_log.add_progress_log(f"✓ Created/Updated VLAN {vlan_id}: {vlan_name} at {site_name}", "success")
                    self.stats['vlans'] += 1
                else:
                    # Review/Dry-run mode: Just count staged items
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
                
                # Auto mode: Immediately approve and apply
                if self.sync_mode == 'auto' and review_item:
                    review_item.status = 'approved'
                    review_item.save()
                    self.apply_review_item(review_item)
                    self.sync_log.add_progress_log(f"✓ Created/Updated prefix: {network} at {site_name}", "success")
                    self.stats['prefixes'] += 1
                else:
                    # Review/Dry-run mode: Just count staged items
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
            preview_display += f"**MAC Address:** {proposed_data.get('mac_address', 'N/A')}\n"
            if proposed_data.get('description'):
                preview_display += f"**Description:** {proposed_data['description']}\n"
            related_object_info = {
                'device': proposed_data.get('device'),
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
                site, _ = Site.objects.update_or_create(
                    name=data['name'],
                    defaults={
                        'description': data.get('description', ''),
                        'comments': data.get('comments', ''),
                    }
                )
                # Apply site tags
                tag_names = plugin_settings.get_tags_for_object_type('site')
                for tag_name in tag_names:
                    tag, _ = Tag.objects.get_or_create(name=tag_name)
                    site.tags.add(tag)
                    
            elif item_type == 'device':
                manufacturer, _ = Manufacturer.objects.get_or_create(
                    name=data.get('manufacturer', 'Cisco Meraki')
                )
                device_type, _ = DeviceType.objects.get_or_create(
                    model=data['model'],
                    manufacturer=manufacturer,
                    defaults={'slug': data['model'].lower().replace(' ', '-')}
                )
                device_role, _ = DeviceRole.objects.get_or_create(
                    name=data['role'],
                    defaults={
                        'slug': data['role'].lower().replace(' ', '-'),
                        'color': '2196f3'
                    }
                )
                site = Site.objects.get(name=data['site'])
                
                device, _ = Device.objects.update_or_create(
                    serial=data['serial'],
                    defaults={
                        'name': data['name'],
                        'device_type': device_type,
                        'device_role': device_role,
                        'site': site,
                        'status': data.get('status', 'active'),
                        'comments': data.get('comments', ''),
                    }
                )
                # Apply device tags
                tag_names = plugin_settings.get_tags_for_object_type('device')
                for tag_name in tag_names:
                    tag, _ = Tag.objects.get_or_create(name=tag_name)
                    device.tags.add(tag)
                    
            elif item_type == 'vlan':
                site = Site.objects.get(name=data['site'])
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
                vlan, _ = VLAN.objects.update_or_create(
                    vid=data['vid'],
                    group=vlan_group,
                    defaults={
                        'name': data['name'],
                        'status': 'active',
                        'description': data.get('description', ''),
                    }
                )
                # Apply VLAN tags
                tag_names = plugin_settings.get_tags_for_object_type('vlan')
                for tag_name in tag_names:
                    tag, _ = Tag.objects.get_or_create(name=tag_name)
                    vlan.tags.add(tag)
                    
            elif item_type == 'prefix':
                site = Site.objects.get(name=data['site'])
                prefix, _ = Prefix.objects.update_or_create(
                    prefix=data['prefix'],
                    defaults={
                        'site': site,
                        'status': 'active',
                        'description': data.get('description', ''),
                    }
                )
                # Apply prefix tags
                tag_names = plugin_settings.get_tags_for_object_type('prefix')
                for tag_name in tag_names:
                    tag, _ = Tag.objects.get_or_create(name=tag_name)
                    prefix.tags.add(tag)
            
            logger.info(f"Applied review item: {item.action_type} {item.item_type} - {item.object_name}")
            
        except Exception as e:
            logger.error(f"Failed to apply review item {item.item_type} - {item.object_name}: {e}")
            raise
    
    def _cleanup_orphaned_objects(self, meraki_tag: Tag):
        """Delete objects with meraki tag that were not synced in this run"""
        logger.info("Checking for orphaned objects to clean up...")
        
        # Clean up sites
        all_meraki_sites = Site.objects.filter(tags=meraki_tag)
        orphaned_sites = all_meraki_sites.exclude(id__in=self.synced_object_ids['sites'])
        if orphaned_sites.exists():
            count = orphaned_sites.count()
            for site in orphaned_sites:
                logger.info(f"Deleting orphaned site: {site.name} (ID: {site.id})")
            orphaned_sites.delete()
            self.stats['deleted_sites'] = count
            logger.info(f"Deleted {count} orphaned site(s)")
        
        # Clean up devices
        all_meraki_devices = Device.objects.filter(tags=meraki_tag)
        orphaned_devices = all_meraki_devices.exclude(id__in=self.synced_object_ids['devices'])
        if orphaned_devices.exists():
            count = orphaned_devices.count()
            for device in orphaned_devices:
                logger.info(f"Deleting orphaned device: {device.name} (Serial: {device.serial}, ID: {device.id})")
            orphaned_devices.delete()
            self.stats['deleted_devices'] = count
            logger.info(f"Deleted {count} orphaned device(s)")
        
        # Clean up VLANs
        all_meraki_vlans = VLAN.objects.filter(tags=meraki_tag)
        orphaned_vlans = all_meraki_vlans.exclude(id__in=self.synced_object_ids['vlans'])
        if orphaned_vlans.exists():
            count = orphaned_vlans.count()
            for vlan in orphaned_vlans:
                logger.info(f"Deleting orphaned VLAN: {vlan.name} (VID: {vlan.vid}, ID: {vlan.id})")
            orphaned_vlans.delete()
            self.stats['deleted_vlans'] = count
            logger.info(f"Deleted {count} orphaned VLAN(s)")
        
        # Clean up prefixes
        all_meraki_prefixes = Prefix.objects.filter(tags=meraki_tag)
        orphaned_prefixes = all_meraki_prefixes.exclude(id__in=self.synced_object_ids['prefixes'])
        if orphaned_prefixes.exists():
            count = orphaned_prefixes.count()
            for prefix in orphaned_prefixes:
                logger.info(f"Deleting orphaned prefix: {prefix.prefix} (ID: {prefix.id})")
            orphaned_prefixes.delete()
            self.stats['deleted_prefixes'] = count
            logger.info(f"Deleted {count} orphaned prefix(s)")
        
        logger.info("Orphaned object cleanup complete")
