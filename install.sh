#!/bin/bash
#
# NetBox Meraki Plugin Installation Helper Script
# This script helps install and configure the NetBox Meraki plugin
#

set -e

echo "=================================================="
echo "NetBox Meraki Plugin - Installation Helper"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "$1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    print_error "Please do not run this script as root"
    exit 1
fi

# Default paths
NETBOX_PATH="/opt/netbox"
PLUGIN_PATH=$(pwd)

# Ask for NetBox path
print_info "Enter NetBox installation path [${NETBOX_PATH}]:"
read -r input_path
if [ -n "$input_path" ]; then
    NETBOX_PATH="$input_path"
fi

# Verify NetBox installation
if [ ! -d "$NETBOX_PATH" ]; then
    print_error "NetBox not found at $NETBOX_PATH"
    exit 1
fi

if [ ! -f "$NETBOX_PATH/netbox/manage.py" ]; then
    print_error "NetBox manage.py not found. Invalid NetBox installation?"
    exit 1
fi

print_success "Found NetBox installation at $NETBOX_PATH"

# Check virtual environment
if [ ! -d "$NETBOX_PATH/venv" ]; then
    print_error "NetBox virtual environment not found at $NETBOX_PATH/venv"
    exit 1
fi

print_success "Found NetBox virtual environment"

# Activate virtual environment
source "$NETBOX_PATH/venv/bin/activate"

# Check Python version
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
print_info "Python version: $PYTHON_VERSION"

# Install plugin
print_info ""
print_info "Installing NetBox Meraki plugin..."
pip install -e "$PLUGIN_PATH"
print_success "Plugin installed"

# Ask for API key
print_info ""
print_info "Enter your Meraki Dashboard API key:"
print_info "(You can skip this and add it manually later)"
read -r -s MERAKI_API_KEY
echo ""

if [ -z "$MERAKI_API_KEY" ]; then
    print_warning "No API key provided. You'll need to add it to configuration.py or .env file"
fi

# Create or update .env file
ENV_FILE="$NETBOX_PATH/netbox/netbox/.env"
if [ -n "$MERAKI_API_KEY" ]; then
    print_info "Updating environment file..."
    if [ -f "$ENV_FILE" ]; then
        # Check if MERAKI_API_KEY already exists
        if grep -q "MERAKI_API_KEY" "$ENV_FILE"; then
            print_warning "MERAKI_API_KEY already exists in .env file. Skipping..."
        else
            echo "" >> "$ENV_FILE"
            echo "# Meraki Plugin Configuration" >> "$ENV_FILE"
            echo "MERAKI_API_KEY=$MERAKI_API_KEY" >> "$ENV_FILE"
            print_success "Added API key to .env file"
        fi
    else
        echo "# Meraki Plugin Configuration" > "$ENV_FILE"
        echo "MERAKI_API_KEY=$MERAKI_API_KEY" >> "$ENV_FILE"
        print_success "Created .env file with API key"
    fi
fi

# Check configuration.py
CONFIG_FILE="$NETBOX_PATH/netbox/netbox/configuration.py"
print_info ""
print_info "Checking NetBox configuration..."

if ! grep -q "netbox_meraki" "$CONFIG_FILE"; then
    print_warning "Plugin not found in configuration.py PLUGINS list"
    print_info ""
    print_info "Add the following to your configuration.py:"
    print_info ""
    cat << 'EOF'
# Enable NetBox Meraki Plugin
PLUGINS = [
    'netbox_meraki',
    # ... other plugins ...
]

# Configure NetBox Meraki Plugin
PLUGINS_CONFIG = {
    'netbox_meraki': {
        'meraki_api_key': os.environ.get('MERAKI_API_KEY', ''),
        'meraki_base_url': 'https://api.meraki.com/api/v1',
        'sync_interval': 3600,
        'auto_create_sites': True,
        'auto_create_device_types': True,
        'auto_create_device_roles': True,
        'auto_create_manufacturers': True,
        'default_device_role': 'Network Device',
        'default_manufacturer': 'Cisco Meraki',
    },
}
EOF
    print_info ""
    print_warning "Please update configuration.py manually before continuing"
    print_info "Press Enter when ready to continue..."
    read -r
else
    print_success "Plugin configuration found in configuration.py"
fi

# Run migrations
print_info ""
print_info "Running database migrations..."
cd "$NETBOX_PATH/netbox"
python manage.py migrate netbox_meraki

if [ $? -eq 0 ]; then
    print_success "Migrations completed successfully"
else
    print_error "Migration failed. Please check the error messages above"
    exit 1
fi

# Collect static files
print_info ""
print_info "Collecting static files..."
python manage.py collectstatic --no-input > /dev/null 2>&1
print_success "Static files collected"

# Check if we can restart services
print_info ""
print_info "Installation complete! You need to restart NetBox services."
print_info ""
print_info "For systemd-managed NetBox, run:"
print_info "  sudo systemctl restart netbox netbox-rq"
print_info ""
print_info "For Docker-based NetBox, run:"
print_info "  docker-compose restart netbox netbox-worker"
print_info ""

# Ask if user wants to restart services
print_info "Restart NetBox services now? (requires sudo) [y/N]:"
read -r restart_choice

if [ "$restart_choice" = "y" ] || [ "$restart_choice" = "Y" ]; then
    if command -v systemctl &> /dev/null; then
        print_info "Restarting NetBox services..."
        sudo systemctl restart netbox netbox-rq
        print_success "Services restarted"
    else
        print_warning "systemctl not found. Please restart services manually"
    fi
fi

# Run a test
print_info ""
print_info "Testing plugin installation..."
cd "$NETBOX_PATH/netbox"
python manage.py showmigrations netbox_meraki

if [ $? -eq 0 ]; then
    print_success "Plugin is properly installed!"
else
    print_error "Plugin test failed"
    exit 1
fi

# Final instructions
print_info ""
print_success "=================================================="
print_success "Installation Complete!"
print_success "=================================================="
print_info ""
print_info "Next steps:"
print_info "1. Access NetBox web interface"
print_info "2. Navigate to Plugins > Meraki Sync"
print_info "3. Configure device role mappings in Configuration"
print_info "4. Run your first sync in 'Review' mode"
print_info ""
print_info "For detailed usage instructions, see:"
print_info "  - INSTALLATION_GUIDE.md"
print_info "  - QUICKSTART.md"
print_info "  - EXAMPLES.md"
print_info ""
print_info "To test the sync command:"
print_info "  cd $NETBOX_PATH/netbox"
print_info "  source $NETBOX_PATH/venv/bin/activate"
print_info "  python manage.py sync_meraki --mode dry_run"
print_info ""
