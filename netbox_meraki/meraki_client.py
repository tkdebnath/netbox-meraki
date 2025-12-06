"""
Meraki API Client for interacting with Cisco Meraki Dashboard API
"""
import requests
import logging
from typing import List, Dict, Optional
from django.conf import settings


logger = logging.getLogger('netbox_meraki')


class MerakiAPIClient:
    """Client for Cisco Meraki Dashboard API"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize Meraki API client
        
        Args:
            api_key: Meraki Dashboard API key
            base_url: Meraki API base URL
        """
        plugin_config = settings.PLUGINS_CONFIG.get('netbox_meraki', {})
        
        self.api_key = api_key or plugin_config.get('meraki_api_key', '')
        self.base_url = base_url or plugin_config.get('meraki_base_url', 'https://api.meraki.com/api/v1')
        
        if not self.api_key:
            raise ValueError("Meraki API key is required")
        
        self.session = requests.Session()
        self.session.headers.update({
            'X-Cisco-Meraki-API-Key': self.api_key,
            'Content-Type': 'application/json'
        })
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        Make API request to Meraki Dashboard
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request arguments
            
        Returns:
            Response JSON data
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.RequestException as e:
            logger.error(f"Meraki API request failed: {e}")
            raise
    
    def get_organizations(self) -> List[Dict]:
        """Get all organizations"""
        return self._request('GET', 'organizations')
    
    def get_organization(self, org_id: str) -> Dict:
        """Get organization details"""
        return self._request('GET', f'organizations/{org_id}')
    
    def get_networks(self, org_id: str) -> List[Dict]:
        """Get all networks in an organization"""
        return self._request('GET', f'organizations/{org_id}/networks')
    
    def get_network(self, network_id: str) -> Dict:
        """Get network details"""
        return self._request('GET', f'networks/{network_id}')
    
    def get_devices(self, network_id: str) -> List[Dict]:
        """Get all devices in a network"""
        return self._request('GET', f'networks/{network_id}/devices')
    
    def get_device(self, serial: str) -> Dict:
        """Get device details"""
        return self._request('GET', f'devices/{serial}')
    
    def get_device_statuses(self, org_id: str) -> List[Dict]:
        """Get device statuses for an organization"""
        return self._request('GET', f'organizations/{org_id}/devices/statuses')
    
    def get_appliance_vlans(self, network_id: str) -> List[Dict]:
        """Get VLANs configured on MX appliance"""
        try:
            return self._request('GET', f'networks/{network_id}/appliance/vlans')
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # VLANs not enabled on this network
                return []
            raise
    
    def get_appliance_ports(self, network_id: str) -> List[Dict]:
        """Get appliance port configuration"""
        try:
            return self._request('GET', f'networks/{network_id}/appliance/ports')
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return []
            raise
    
    def get_switch_ports(self, serial: str) -> List[Dict]:
        """Get switch port configuration"""
        try:
            return self._request('GET', f'devices/{serial}/switch/ports')
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return []
            raise
    
    def get_appliance_subnets(self, network_id: str) -> List[Dict]:
        """Get subnets/prefixes from appliance VLANs"""
        vlans = self.get_appliance_vlans(network_id)
        subnets = []
        
        for vlan in vlans:
            if vlan.get('subnet'):
                subnets.append({
                    'vlan_id': vlan.get('id'),
                    'vlan_name': vlan.get('name'),
                    'subnet': vlan.get('subnet'),
                    'appliance_ip': vlan.get('applianceIp'),
                })
        
        return subnets
    
    def get_organization_inventory(self, org_id: str) -> List[Dict]:
        """Get organization inventory devices"""
        return self._request('GET', f'organizations/{org_id}/inventoryDevices')
