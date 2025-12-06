#!/bin/bash

# Script to set up NetBox Meraki plugin for development

echo "Setting up NetBox Meraki plugin..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Configure NetBox with the plugin settings"
echo "2. Run migrations: python manage.py migrate netbox_meraki"
echo "3. Restart NetBox services"
echo ""
echo "For development:"
echo "- Activate venv: source venv/bin/activate"
echo "- Run tests: python manage.py test netbox_meraki"
