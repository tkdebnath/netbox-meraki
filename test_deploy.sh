#!/bin/bash
# Quick deployment test script

echo "=== Copying plugin to NetBox ==="
sudo cp -r /home/tdebnath/ra_netbox_meraki/netbox_meraki /opt/netbox/netbox/

echo ""
echo "=== Restarting NetBox services ==="
sudo systemctl restart netbox netbox-rq

echo ""
echo "=== Waiting for services to start ==="
sleep 5

echo ""
echo "=== Checking service status ==="
sudo systemctl status netbox --no-pager -l | head -20
echo ""
sudo systemctl status netbox-rq --no-pager -l | head -20

echo ""
echo "=== Recent NetBox logs (last 50 lines) ==="
sudo journalctl -u netbox -n 50 --no-pager

echo ""
echo "=== Recent RQ worker logs (last 50 lines) ==="
sudo journalctl -u netbox-rq -n 50 --no-pager

echo ""
echo "=== Deploy complete! ==="
echo "Now try creating a scheduled sync with specific networks selected"
echo "Check logs with: sudo journalctl -u netbox -f"
