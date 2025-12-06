"""
Sync service for importing Meraki data into NetBox
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional
from ipaddress import ip_network

from django.db import transaction
from django.utils import timezone

from dcim.models import Site, Device, DeviceType, DeviceRole, Manufacturer, Interface
from ipam.models import VLAN, VLANGroup, Prefix, IPAddress
from extras.models import Tag

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
        }
        self.errors = []
    
    def sync_all(self) -> SyncLog:
        """
        Perform full synchronization from Meraki to NetBox
        
        Returns:
            SyncLog instance with results
        """
        start_time = datetime.now()
        
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
            
            # Get or create Meraki tag
            meraki_tag, _ = Tag.objects.get_or_create(
                name='Meraki',
                defaults={'description': 'Synced from Cisco Meraki Dashboard'}
            )
            
            # Get all organizations
            organizations = self.client.get_organizations()
            logger.info(f"Found {len(organizations)} organizations")
            
            for org in organizations:
                try:
                    self._sync_organization(org, meraki_tag)
                    self.stats['organizations'] += 1
                except Exception as e:
                    error_msg = f"Error syncing organization {org.get('name')}: {str(e)}"
                    logger.error(error_msg)
                    self.errors.append(error_msg)
            
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
        networks = self.client.get_networks(org_id)
        logger.info(f"Found {len(networks)} networks in {org_name}")
        
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
        
        # Apply site name transformation rules
        site_name = SiteNameRule.transform_network_name(network_name)
        if site_name != network_name:
            logger.info(f"Transformed site name: '{network_name}' -> '{site_name}'")
        
        # Create or update site for this network
        site, created = Site.objects.update_or_create(
            name=site_name,
            defaults={
                'description': f"Meraki Network - {org_name}",
                'comments': f"Meraki Network ID: {network_id}\nOriginal Network Name: {network_name}\nTimezone: {network.get('timeZone', 'N/A')}",
            }
        )
        
        if created:
            logger.info(f"Created site: {network_name}")
        
        site.tags.add(meraki_tag)
        
        # Get devices in this network
        devices = self.client.get_devices(network_id)
        logger.info(f"Found {len(devices)} devices in {network_name}")
        
        for device in devices:
            try:
                self._sync_device(device, site, meraki_tag)
                self.stats['devices'] += 1
            except Exception as e:
                error_msg = f"Error syncing device {device.get('name', device.get('serial'))}: {str(e)}"
                logger.error(error_msg)
                self.errors.append(error_msg)
        
        # Sync VLANs for this network
        try:
            self._sync_vlans(network_id, site, meraki_tag)
        except Exception as e:
            error_msg = f"Error syncing VLANs for network {network_name}: {str(e)}"
            logger.error(error_msg)
            self.errors.append(error_msg)
        
        # Sync prefixes for this network
        try:
            self._sync_prefixes(network_id, site, meraki_tag)
        except Exception as e:
            error_msg = f"Error syncing prefixes for network {network_name}: {str(e)}"
            logger.error(error_msg)
            self.errors.append(error_msg)
    
    def _sync_device(self, device: Dict, site: Site, meraki_tag: Tag):
        """Sync a single device"""
        serial = device['serial']
        name = device.get('name', serial)
        model = device.get('model', 'Unknown')
        product_type = device.get('productType', '')
        
        logger.debug(f"Syncing device: {name} ({serial})")
        
        # Get plugin settings
        plugin_settings = PluginSettings.get_settings()
        
        # Get or create manufacturer
        manufacturer, _ = Manufacturer.objects.get_or_create(
            name='Cisco Meraki'
        )
        
        # Get or create device type
        device_type, _ = DeviceType.objects.get_or_create(
            model=model,
            manufacturer=manufacturer,
            defaults={
                'slug': model.lower().replace(' ', '-'),
            }
        )
        
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
        
        # Prepare proposed data
        proposed_data = {
            'name': name,
            'serial': serial,
            'model': model,
            'manufacturer': 'Cisco Meraki',
            'role': role_name,
            'site': site.name,
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
        
        # If review or dry run mode, create review item instead of modifying
        if self.sync_mode in ['review', 'dry_run']:
            self._create_review_item(
                item_type='device',
                action_type=action_type,
                object_name=name,
                object_identifier=serial,
                proposed_data=proposed_data,
                current_data=current_data
            )
            logger.info(f"Created review item for device: {name} ({action_type})")
            return
        
        # Auto mode - create or update device immediately
        netbox_device, created = Device.objects.update_or_create(
            serial=serial,
            defaults={
                'name': name,
                'device_type': device_type,
                'device_role': device_role,
                'site': site,
                'status': 'active' if device.get('status') != 'offline' else 'offline',
                'comments': f"MAC: {device.get('mac', 'N/A')}\n"
                           f"LAN IP: {device.get('lanIp', 'N/A')}\n"
                           f"Firmware: {device.get('firmware', 'N/A')}\n"
                           f"Product Type: {device.get('productType', 'N/A')}",
            }
        )
        
        if created:
            logger.info(f"Created device: {name}")
        
        netbox_device.tags.add(meraki_tag)
        
        # Sync interfaces if available
        if device.get('lanIp'):
            self._sync_device_interface(netbox_device, device)
    
    def _sync_device_interface(self, device: Device, meraki_device: Dict):
        """Sync primary interface for a device"""
        lan_ip = meraki_device.get('lanIp')
        mac = meraki_device.get('mac')
        
        if not lan_ip:
            return
        
        # Create or update management interface
        interface, created = Interface.objects.get_or_create(
            device=device,
            name='Management',
            defaults={
                'type': 'other',
                'mac_address': mac if mac else None,
            }
        )
        
        # Create or update IP address
        try:
            ip_address, created = IPAddress.objects.get_or_create(
                address=f"{lan_ip}/32",
                defaults={
                    'status': 'active',
                    'assigned_object': interface,
                }
            )
            
            if not created and ip_address.assigned_object != interface:
                ip_address.assigned_object = interface
                ip_address.save()
            
            # Set as primary IP
            if not device.primary_ip4:
                device.primary_ip4 = ip_address
                device.save()
                
        except Exception as e:
            logger.warning(f"Could not create IP address {lan_ip} for device {device.name}: {e}")
    
    def _sync_vlans(self, network_id: str, site: Site, meraki_tag: Tag):
        """Sync VLANs for a network"""
        vlans = self.client.get_appliance_vlans(network_id)
        
        if not vlans:
            return
        
        logger.info(f"Syncing {len(vlans)} VLANs for {site.name}")
        
        # Create or get VLAN group for this site
        vlan_group, _ = VLANGroup.objects.get_or_create(
            name=f"{site.name} VLANs",
            defaults={
                'slug': f"{site.name.lower().replace(' ', '-')}-vlans",
            }
        )
        
        for vlan_data in vlans:
            vlan_id = vlan_data.get('id')
            vlan_name = vlan_data.get('name', f"VLAN {vlan_id}")
            
            try:
                vlan, created = VLAN.objects.update_or_create(
                    vid=vlan_id,
                    group=vlan_group,
                    defaults={
                        'name': vlan_name,
                        'status': 'active',
                        'description': f"Subnet: {vlan_data.get('subnet', 'N/A')}",
                    }
                )
                
                if created:
                    logger.debug(f"Created VLAN {vlan_id}: {vlan_name}")
                
                vlan.tags.add(meraki_tag)
                self.stats['vlans'] += 1
                
            except Exception as e:
                logger.warning(f"Could not sync VLAN {vlan_id}: {e}")
    
    def _sync_prefixes(self, network_id: str, site: Site, meraki_tag: Tag):
        """Sync prefixes/subnets for a network"""
        subnets = self.client.get_appliance_subnets(network_id)
        
        if not subnets:
            return
        
        logger.info(f"Syncing {len(subnets)} prefixes for {site.name}")
        
        for subnet_data in subnets:
            subnet = subnet_data.get('subnet')
            
            if not subnet:
                continue
            
            try:
                # Validate subnet format
                network = ip_network(subnet, strict=False)
                
                prefix, created = Prefix.objects.update_or_create(
                    prefix=str(network),
                    defaults={
                        'site': site,
                        'status': 'active',
                        'description': f"VLAN {subnet_data.get('vlan_id')}: {subnet_data.get('vlan_name', '')}",
                    }
                )
                
                if created:
                    logger.debug(f"Created prefix: {network}")
                
                prefix.tags.add(meraki_tag)
                self.stats['prefixes'] += 1
                
            except Exception as e:
                logger.warning(f"Could not sync prefix {subnet}: {e}")
    
    def _create_review_item(self, item_type: str, action_type: str, object_name: str, 
                           object_identifier: str, proposed_data: Dict, current_data: Optional[Dict] = None):
        """Create a review item for manual approval"""
        if not self.review:
            return None
        
        return ReviewItem.objects.create(
            review=self.review,
            item_type=item_type,
            action_type=action_type,
            object_name=object_name,
            object_identifier=object_identifier,
            proposed_data=proposed_data,
            current_data=current_data,
            status='pending'
        )
    
    def _should_execute(self) -> bool:
        """Check if sync should actually modify database"""
        return self.sync_mode == 'auto'
    
    def apply_review_item(self, item: 'ReviewItem'):
        """Apply an approved review item"""
        item_type = item.item_type
        proposed_data = item.proposed_data
        
        try:
            if item_type == 'site':
                Site.objects.update_or_create(
                    name=proposed_data['name'],
                    defaults={
                        'description': proposed_data.get('description', ''),
                        'comments': proposed_data.get('comments', ''),
                    }
                )
            elif item_type == 'device':
                manufacturer, _ = Manufacturer.objects.get_or_create(
                    name=proposed_data.get('manufacturer', 'Cisco Meraki')
                )
                device_type, _ = DeviceType.objects.get_or_create(
                    model=proposed_data['model'],
                    manufacturer=manufacturer,
                    defaults={'slug': proposed_data['model'].lower().replace(' ', '-')}
                )
                device_role, _ = DeviceRole.objects.get_or_create(
                    name=proposed_data['role'],
                    defaults={
                        'slug': proposed_data['role'].lower().replace(' ', '-'),
                        'color': '2196f3'
                    }
                )
                site = Site.objects.get(name=proposed_data['site'])
                
                Device.objects.update_or_create(
                    serial=proposed_data['serial'],
                    defaults={
                        'name': proposed_data['name'],
                        'device_type': device_type,
                        'device_role': device_role,
                        'site': site,
                        'status': proposed_data.get('status', 'active'),
                        'comments': proposed_data.get('comments', ''),
                    }
                )
            elif item_type == 'vlan':
                site = Site.objects.get(name=proposed_data['site'])
                vlan_group, _ = VLANGroup.objects.get_or_create(
                    name=f"{site.name} VLANs",
                    defaults={'slug': f"{site.name.lower().replace(' ', '-')}-vlans"}
                )
                VLAN.objects.update_or_create(
                    vid=proposed_data['vid'],
                    group=vlan_group,
                    defaults={
                        'name': proposed_data['name'],
                        'status': 'active',
                        'description': proposed_data.get('description', ''),
                    }
                )
            elif item_type == 'prefix':
                site = Site.objects.get(name=proposed_data['site'])
                Prefix.objects.update_or_create(
                    prefix=proposed_data['prefix'],
                    defaults={
                        'site': site,
                        'status': 'active',
                        'description': proposed_data.get('description', ''),
                    }
                )
            
            logger.info(f"Applied review item: {item.action_type} {item.item_type} - {item.object_name}")
            
        except Exception as e:
            logger.error(f"Failed to apply review item {item.id}: {e}")
            raise
