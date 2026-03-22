# Bondlink Client - Quick Start Guide

## 🚀 10-Minute Setup

### Step 1: Identify Your Network Interfaces

```bash
ip link show
```

You'll see output like:
```
1: lo: ...
2: enp1s0: ...  ← WAN 1
3: enp2s0: ...  ← WAN 2
4: enp3s0: ...  ← WAN 3
5: enp4s0: ...  ← WAN 4
6: enp5s0: ...  ← LAN 1
7: enp6s0: ...  ← LAN 2
8: enp7s0: ...  ← LAN 3
9: enp8s0: ...  ← LAN 4
```

Write down your interface names!

### Step 2: Generate Auth Token

```bash
openssl rand -hex 32
```

Save this token - you'll need it for both client and server!

### Step 3: Install

```bash
cd /Users/viewvision/Desktop/Bondlink
cd scripts
sudo bash install.sh
```

### Step 4: Configure

```bash
sudo nano /etc/bondlink/client.yaml
```

**Minimal working config:**

```yaml
server:
  host: "YOUR_VPS_IP"
  port: 8443
  auth_token: "YOUR_TOKEN_FROM_STEP_2"

wan_interfaces:
  - name: "wan1"
    interface: "enp1s0"  # YOUR INTERFACE
    priority: 1
    enabled: true
  - name: "wan2"
    interface: "enp2s0"  # YOUR INTERFACE
    priority: 2
    enabled: true
  - name: "wan3"
    interface: "enp3s0"  # YOUR INTERFACE
    priority: 3
    enabled: true
  - name: "wan4"
    interface: "enp4s0"  # YOUR INTERFACE
    priority: 4
    enabled: true

lan_interfaces:
  - name: "lan1"
    interface: "enp5s0"  # YOUR INTERFACE
    ip: "192.168.1.1"
    netmask: "255.255.255.0"
    dhcp_enabled: true
    dhcp_range_start: "192.168.1.100"
    dhcp_range_end: "192.168.1.200"
```

### Step 5: Start

```bash
sudo systemctl enable bondlink-client
sudo systemctl start bondlink-client
```

### Step 6: Verify

```bash
# Check service
sudo systemctl status bondlink-client

# Check interfaces
bondlink interfaces

# Monitor live
bondlink monitor
```

### Step 7: Open Web UI

```bash
# Get your IP
hostname -I
```

Open browser: `http://YOUR_IP`

**Note:** No port number needed - runs on standard HTTP port 80

## ✅ Success Checklist

- [ ] All WAN interfaces show as "UP"
- [ ] Web UI is accessible
- [ ] At least one tunnel shows "Connected"
- [ ] Can ping external IPs through bonded connection
- [ ] Bandwidth graphs show activity

## 🆘 Common Issues

### "Interface not found"
```bash
# Check if interface exists
ip link show YOUR_INTERFACE

# Bring it up
sudo ip link set YOUR_INTERFACE up
```

### "Cannot connect to VPS"
- Verify VPS IP is correct
- Check VPS server is running
- Verify firewall allows port 8443
- Check auth token matches

### "No web UI"
```bash
# Check if port 8080 is listening
sudo netstat -tulpn | grep 8080

# Allow in firewall
sudo ufw allow 8080
```

### "Tunnels won't connect"
```bash
# Check logs
sudo journalctl -u bondlink-client -f

# Verify WAN interfaces have internet
ping -I enp1s0 8.8.8.8
```

## 📊 Testing Bandwidth

```bash
# Install speedtest
sudo apt install speedtest-cli

# Test individual WAN
speedtest --interface enp1s0

# Test bonded (after LAN connection)
speedtest
```

## 🎯 Next: Setup VPS Server

After client is working, set up the server side in:
`/Users/viewvision/Desktop/Server-side bondlink`

Server will:
- Accept tunnel connections from client
- Aggregate bandwidth
- Route traffic to internet
- Monitor health

---

**Need help?** Check logs: `sudo journalctl -u bondlink-client -f`
