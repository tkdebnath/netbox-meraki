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
from .models import SyncLog


logger = logging.getLogger('netbox_meraki')


class MerakiSyncService:
    """Service for synchronizing Meraki data to NetBox"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize sync service"""
        self.client = MerakiAPIClient(api_key=api_key)
        self.sync_log = None
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
        
        # Create sync log
        self.sync_log = SyncLog.objects.create(
            status='running',
            message='Starting synchronization...'
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
            status = 'success' if not self.errors else 'partial' if self.stats['devices'] > 0 else 'failed'
            
            self.sync_log.status = status
            self.sync_log.message = f"Synchronized {self.stats['organizations']} organizations"
            self.sync_log.organizations_synced = self.stats['organizations']
            self.sync_log.networks_synced = self.stats['networks']
            self.sync_log.devices_synced = self.stats['devices']
            self.sync_log.vlans_synced = self.stats['vlans']
            self.sync_log.prefixes_synced = self.stats['prefixes']
            self.sync_log.errors = self.errors
            self.sync_log.duration_seconds = duration
            self.sync_log.save()
            
            logger.info(f"Synchronization completed in {duration:.2f} seconds")
            
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
        
        # Create or update site for this network
        site, created = Site.objects.update_or_create(
            name=network_name,
            defaults={
                'description': f"Meraki Network - {org_name}",
                'comments': f"Meraki Network ID: {network_id}\nTimezone: {network.get('timeZone', 'N/A')}",
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
        
        logger.debug(f"Syncing device: {name} ({serial})")
        
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
        
        # Get or create device role
        device_role, _ = DeviceRole.objects.get_or_create(
            name='Network Device',
            defaults={
                'slug': 'network-device',
                'color': '2196f3',
            }
        )
        
        # Create or update device
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
