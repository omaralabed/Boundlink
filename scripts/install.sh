#!/bin/bash
#
# Bondlink Client Installation Script for Ubuntu 24.04
# Run with: sudo bash install.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "================================================"
echo "  Bondlink Client Installation"
echo "  Multi-WAN Bonding Router"
echo "================================================"
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: This script must be run as root${NC}"
    echo "Please run: sudo bash install.sh"
    exit 1
fi

# Check Ubuntu version
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [[ "$ID" != "ubuntu" ]]; then
        echo -e "${YELLOW}Warning: This script is designed for Ubuntu. Your OS: $ID${NC}"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

echo -e "${GREEN}✓ Starting installation...${NC}\n"

# Update system
echo -e "${BLUE}[1/7] Updating system packages...${NC}"
apt-get update -qq
apt-get upgrade -y -qq

# Install Python 3.11+ and dependencies
echo -e "${BLUE}[2/7] Installing Python and system dependencies...${NC}"
apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    iptables \
    iproute2 \
    iputils-ping \
    net-tools \
    git

# Create installation directory
echo -e "${BLUE}[3/7] Creating installation directories...${NC}"
mkdir -p /opt/bondlink
mkdir -p /etc/bondlink
mkdir -p /var/log/bondlink
mkdir -p /var/run/bondlink

# Copy files
echo -e "${BLUE}[4/7] Installing Bondlink files...${NC}"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

# Copy application files
cp -r client/ /opt/bondlink/
cp -r web/ /opt/bondlink/
cp -r common/ /opt/bondlink/ 2>/dev/null || true
cp requirements.txt /opt/bondlink/
cp setup.py /opt/bondlink/

# Copy configuration
if [ ! -f /etc/bondlink/client.yaml ]; then
    cp config/client.yaml /etc/bondlink/client.yaml
    echo -e "${YELLOW}  Configuration file created at /etc/bondlink/client.yaml${NC}"
    echo -e "${YELLOW}  Please edit this file with your VPS details and interface names${NC}"
else
    echo -e "${YELLOW}  Configuration file already exists, skipping...${NC}"
fi

# Create virtual environment and install Python packages
echo -e "${BLUE}[5/7] Installing Python dependencies...${NC}"
cd /opt/bondlink
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel -q
pip install -r requirements.txt -q
pip install -e . -q

# Create symlinks for commands
echo -e "${BLUE}[6/7] Creating command symlinks...${NC}"
cat > /usr/local/bin/bondlink-daemon << 'EOF'
#!/bin/bash
source /opt/bondlink/venv/bin/activate
exec python3 -m client.daemon "$@"
EOF

cat > /usr/local/bin/bondlink << 'EOF'
#!/bin/bash
source /opt/bondlink/venv/bin/activate
exec python3 -m client.cli "$@"
EOF

chmod +x /usr/local/bin/bondlink-daemon
chmod +x /usr/local/bin/bondlink

# Install systemd service
echo -e "${BLUE}[7/7] Installing systemd service...${NC}"
cp "$SCRIPT_DIR/bondlink-client.service" /etc/systemd/system/
systemctl daemon-reload

echo -e "\n${GREEN}================================================${NC}"
echo -e "${GREEN}  Installation Complete!${NC}"
echo -e "${GREEN}================================================${NC}\n"

echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Edit configuration: ${BLUE}sudo nano /etc/bondlink/client.yaml${NC}"
echo -e "     - Set your VPS IP address and auth token"
echo -e "     - Configure WAN interface names (run 'ip link' to see interfaces)"
echo -e "     - Configure LAN interface names and IP addresses"
echo -e ""
echo -e "  2. Enable and start the service:"
echo -e "     ${BLUE}sudo systemctl enable bondlink-client${NC}"
echo -e "     ${BLUE}sudo systemctl start bondlink-client${NC}"
echo -e ""
echo -e "  3. Check status:"
echo -e "     ${BLUE}sudo systemctl status bondlink-client${NC}"
echo -e "     ${BLUE}bondlink status${NC}"
echo -e ""
echo -e "  4. Open Web UI:"
echo -e "     ${BLUE}http://$(hostname -I | awk '{print $1}')${NC}"
echo -e ""
echo -e "${YELLOW}Useful commands:${NC}"
echo -e "  ${BLUE}bondlink status${NC}          - Show system status"
echo -e "  ${BLUE}bondlink interfaces${NC}      - List WAN interfaces"
echo -e "  ${BLUE}bondlink monitor${NC}         - Real-time monitoring"
echo -e "  ${BLUE}bondlink enable wan1${NC}     - Enable interface"
echo -e "  ${BLUE}bondlink disable wan1${NC}    - Disable interface"
echo -e ""
echo -e "${YELLOW}Logs:${NC}"
echo -e "  ${BLUE}sudo journalctl -u bondlink-client -f${NC}"
echo -e "  ${BLUE}sudo tail -f /var/log/bondlink/client.log${NC}"
echo -e ""

echo -e "${GREEN}Installation successful!${NC}\n"
