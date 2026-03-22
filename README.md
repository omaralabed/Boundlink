# Bondlink Client

**Professional Multi-WAN Bonding Router for Ubuntu 24.04**

Bondlink Client is a production-ready, high-performance multi-WAN bonding router that aggregates multiple internet connections (4 WAN ports) into a single, high-bandwidth tunnel to a VPS server. Perfect for streaming, gaming, business continuity, and high-availability internet connectivity.

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Ubuntu%2024.04-orange.svg)

## ✨ Features

### 🚀 **Core Features**
- **4 WAN Interface Bonding** - Aggregate up to 4 internet connections
- **Intelligent Load Balancing** - Round-robin, weighted, latency-based, and adaptive modes
- **Automatic Failover** - Seamless switching when a WAN link fails
- **Real-time Health Monitoring** - Continuous ping tests and latency tracking
- **Packet Reordering** - TCP optimization for multi-path transmission

### 🎨 **Professional Web UI**
- **Stunning Dashboard** - Real-time bandwidth graphs and statistics
- **Port Management** - Enable/disable WAN ports with a click
- **Live Monitoring** - WebSocket-powered real-time updates
- **Health Visualization** - Per-port latency, packet loss, and status
- **Total Bonding Stats** - Aggregate upload/download speeds

### 🛠️ **Management Tools**
- **CLI Interface** - Full command-line control
- **REST API** - Programmatic access to all features
- **Systemd Integration** - Production-ready service management
- **Structured Logging** - JSON and text logging with rotation

### 🔒 **Production Ready**
- **Secure Tunneling** - Encrypted connections to VPS
- **NAT/Masquerading** - Full routing and NAT support
- **IPv4 Forwarding** - Complete routing capabilities
- **Error Handling** - Robust reconnection and recovery logic
- **Resource Monitoring** - Prometheus metrics support

## 📋 Requirements

### Hardware
- **Mini PC** with Ubuntu 24.04
- **4 WAN Ports** (USB-to-Ethernet adapters supported)
- **4 LAN Ports** (for local network)
- **Minimum 2GB RAM** (4GB recommended)
- **VPS Server** for tunnel aggregation (setup separately)

### Software
- Ubuntu 24.04 LTS
- Python 3.10 or higher
- Root/sudo access
- Active internet connection on at least one WAN port

## 🚀 Quick Start

### 1. Clone Repository

```bash
cd /Users/viewvision/Desktop/Bondlink
```

### 2. Run Installation Script

```bash
cd scripts
sudo bash install.sh
```

The installer will:
- Install Python dependencies
- Create system directories
- Install systemd service
- Create command symlinks

### 3. Configure

Edit the configuration file:

```bash
sudo nano /etc/bondlink/client.yaml
```

**Required Configuration:**

1. **Server Settings** - Set your VPS details:
```yaml
server:
  host: "YOUR_VPS_IP"  # Replace with your VPS IP
  port: 8443
  auth_token: "YOUR_SECURE_TOKEN"  # Generate with: openssl rand -hex 32
```

2. **WAN Interfaces** - Configure your WAN ports:
```yaml
wan_interfaces:
  - name: "wan1"
    interface: "enp1s0"  # Run 'ip link' to find interface names
    priority: 1
    enabled: true
```

3. **LAN Interfaces** - Configure your LAN ports:
```yaml
lan_interfaces:
  - name: "lan1"
    interface: "enp5s0"
    ip: "192.168.1.1"
    netmask: "255.255.255.0"
    dhcp_enabled: true
```

### 4. Find Interface Names

```bash
ip link show
```

Look for interfaces like `enp1s0`, `enp2s0`, `eth0`, `eth1`, etc.

### 5. Start Service

```bash
sudo systemctl enable bondlink-client
sudo systemctl start bondlink-client
```

### 6. Check Status

```bash
sudo systemctl status bondlink-client
bondlink status
```

### 7. Open Web UI

Open your browser and navigate to:
```
http://MINI_PC_IP
```

**Note:** The Web UI runs on port 80 (standard HTTP), so no port number is needed in the URL.

## 📱 Web UI Features

The professional web dashboard provides:

- **Real-time Bandwidth Graphs** - Live upload/download charts
- **Port Control** - Toggle switches to enable/disable ports
- **Health Status** - Visual indicators for each WAN link
- **Latency Monitoring** - Per-port latency in milliseconds
- **Packet Loss Tracking** - Real-time packet loss percentage
- **Total Bonding Stats** - Aggregate bandwidth across all ports
- **Tunnel Status** - Connection status for each tunnel

### Dashboard Screenshots

The UI features:
- Dark theme with glassmorphism effects
- Gradient accents and smooth animations
- Responsive design for mobile and desktop
- WebSocket-powered live updates (no page refresh needed)

## 🎮 CLI Commands

### Status and Monitoring

```bash
# Show system status
bondlink status

# List all interfaces
bondlink interfaces

# Real-time monitoring
bondlink monitor

# Monitor with custom interval (2 seconds)
bondlink monitor -i 2
```

### Port Management

```bash
# Enable a WAN interface
bondlink enable wan1

# Disable a WAN interface
bondlink disable wan2
```

### Service Management

```bash
# Start service
sudo systemctl start bondlink-client

# Stop service
sudo systemctl stop bondlink-client

# Restart service
sudo systemctl restart bondlink-client

# View logs
sudo journalctl -u bondlink-client -f

# View application logs
sudo tail -f /var/log/bondlink/client.log
```

## 📊 API Endpoints

REST API available at `http://localhost:8080/api`

### GET Endpoints

```bash
# Get system status
curl http://localhost/api/status

# Get all interfaces
curl http://localhost/api/interfaces

# Get specific interface
curl http://localhost/api/interfaces/wan1
```

### POST Endpoints

```bash
# Enable interface
curl -X POST http://localhost/api/interfaces/wan1/enable

# Disable interface
curl -X POST http://localhost/api/interfaces/wan1/disable
```

### WebSocket

```javascript
// Connect to WebSocket for live updates
const ws = new WebSocket('ws://localhost/ws');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data);  // Real-time updates
};
```

## ⚙️ Configuration Reference

### Traffic Modes

- **round_robin** - Distribute packets evenly across all WANs
- **weighted** - Distribute based on interface weights
- **latency_based** - Prefer lower-latency connections
- **adaptive** - Dynamically adjust based on performance

### Tunnel Protocols

- **udp** - Lower overhead, better for high-bandwidth (recommended)
- **tcp** - More reliable, better for unstable connections

### Health Check

Configure ping targets and thresholds:

```yaml
health_check:
  enabled: true
  interval: 5  # Check every 5 seconds
  timeout: 3
  failure_threshold: 3  # Mark down after 3 failures
  recovery_threshold: 2  # Mark up after 2 successes
  ping_targets:
    - "8.8.8.8"
    - "1.1.1.1"
```

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u bondlink-client -n 50

# Check configuration
bondlink-daemon -c /etc/bondlink/client.yaml --version

# Verify Python dependencies
source /opt/bondlink/venv/bin/activate
pip list
```

### Interface Not Found

```bash
# List all network interfaces
ip link show

# Check if interface is up
sudo ip link set enp1s0 up
```

### Cannot Connect to Web UI

```bash
# Check if service is running
sudo systemctl status bondlink-client

# Check if port 80 is accessible
sudo netstat -tulpn | grep :80

# Check firewall
sudo ufw status
sudo ufw allow 80/tcp
```

### No Internet Through Bondlink

```bash
# Check IP forwarding
sysctl net.ipv4.ip_forward

# Check NAT rules
sudo iptables -t nat -L -n -v

# Check routing
ip route show
```

## 📁 Project Structure

```
Bondlink/
├── client/                 # Client application
│   ├── api/               # REST API and WebSocket
│   ├── core/              # Configuration and logging
│   ├── network/           # WAN manager and tunnels
│   ├── cli.py             # CLI interface
│   └── daemon.py          # Main daemon
├── web/                   # Web UI
│   ├── index.html         # Dashboard HTML
│   └── static/
│       ├── css/           # Stylesheets
│       └── js/            # JavaScript
├── config/                # Configuration files
│   └── client.yaml        # Main configuration
├── scripts/               # Installation scripts
│   ├── install.sh         # Installation script
│   └── bondlink-client.service  # Systemd service
├── requirements.txt       # Python dependencies
├── setup.py              # Package setup
└── README.md             # This file
```

## 🔄 Next Steps

After setting up the client, you need to:

1. **Setup VPS Server** - Install server component on your VPS
2. **Generate Auth Token** - Create secure token: `openssl rand -hex 32`
3. **Configure Firewall** - Open port 8443 on VPS
4. **Test Connection** - Verify tunnels connect successfully
5. **Optimize Settings** - Tune based on your connection types

## 📞 Support

- **Issues**: Report bugs and request features
- **Documentation**: Full API docs and guides
- **Community**: Join discussions and get help

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

Built with:
- FastAPI - Modern web framework
- asyncio - Asynchronous I/O
- structlog - Structured logging
- Rich - Beautiful terminal output
- Uvicorn - ASGI server

---

**Made with ❤️ for reliable, high-performance internet connectivity**
