# Bondlink System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        BONDLINK CLIENT (Mini PC)                         │
│                          Ubuntu 24.04 LTS                                │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                              WEB UI LAYER                                │
├─────────────────────────────────────────────────────────────────────────┤
│  Browser (http://localhost) - Port 80                                   │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  📊 Dashboard                                                   │    │
│  │  ├─ Real-time Bandwidth Graphs (Upload/Download)              │    │
│  │  ├─ 4x WAN Interface Cards                                     │    │
│  │  │  ├─ Enable/Disable Toggle                                   │    │
│  │  │  ├─ Status (Up/Down/Degraded)                              │    │
│  │  │  ├─ Speed (Mbps)                                            │    │
│  │  │  ├─ Latency (ms)                                            │    │
│  │  │  └─ Packet Loss (%)                                         │    │
│  │  └─ System Statistics                                          │    │
│  │     ├─ Active Links                                            │    │
│  │     ├─ Healthy Interfaces                                      │    │
│  │     └─ Total Packets                                           │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                          ↕ WebSocket (real-time)                        │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                              API SERVER                                  │
├─────────────────────────────────────────────────────────────────────────┤
│  FastAPI + Uvicorn (Port 80)                                           │
│  ├─ REST API Endpoints                                                  │
│  │  ├─ GET /api/status                                                 │
│  │  ├─ GET /api/interfaces                                             │
│  │  ├─ POST /api/interfaces/{name}/enable                             │
│  │  └─ POST /api/interfaces/{name}/disable                            │
│  └─ WebSocket /ws (broadcasts every 1 second)                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↕
┌─────────────────────────────────────────────────────────────────────────┐
│                          DAEMON ORCHESTRATOR                             │
├─────────────────────────────────────────────────────────────────────────┤
│  Main Process (bondlink-daemon)                                        │
│  ├─ Configuration Loader                                                │
│  ├─ System Setup (IP Forwarding, NAT)                                  │
│  ├─ Signal Handling (SIGINT, SIGTERM)                                  │
│  └─ Component Coordinator                                               │
└─────────────────────────────────────────────────────────────────────────┘
       ↕                      ↕                        ↕
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  WAN MANAGER     │  │ TUNNEL MANAGER   │  │  LOGGING         │
├──────────────────┤  ├──────────────────┤  ├──────────────────┤
│ ┌──────────────┐ │  │ ┌──────────────┐ │  │ • Structured     │
│ │ Monitor Loop │ │  │ │ Tunnel 1     │ │  │ • JSON Format    │
│ │ (every 2s)   │ │  │ │ (WAN 1)      │ │  │ • Rotation       │
│ └──────────────┘ │  │ └──────────────┘ │  │ • Console        │
│                  │  │                  │  └──────────────────┘
│ ┌──────────────┐ │  │ ┌──────────────┐ │
│ │ Stats Update │ │  │ │ Tunnel 2     │ │
│ │ (every 1s)   │ │  │ │ (WAN 2)      │ │
│ └──────────────┘ │  │ └──────────────┘ │
│                  │  │                  │
│ ┌──────────────┐ │  │ ┌──────────────┐ │
│ │ Health Check │ │  │ │ Tunnel 3     │ │
│ │ (every 5s)   │ │  │ │ (WAN 3)      │ │
│ └──────────────┘ │  │ └──────────────┘ │
│                  │  │                  │
│ • 4 Interfaces   │  │ ┌──────────────┐ │
│ • Ping Tests     │  │ │ Tunnel 4     │ │
│ • Latency Track  │  │ │ (WAN 4)      │ │
│ • Failover       │  │ └──────────────┘ │
│ • Statistics     │  │                  │
└──────────────────┘  │ • UDP/TCP        │
                      │ • Encryption     │
                      │ • Heartbeat      │
                      │ • Reconnect      │
                      └──────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         NETWORK INTERFACES                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  WAN INTERFACES (Internet)           LAN INTERFACES (Local Network)    │
│  ┌─────────────────────────┐        ┌────────────────────────────┐    │
│  │ WAN 1 (enp1s0)          │        │ LAN 1 (enp5s0)             │    │
│  │ Priority: 1             │        │ 192.168.1.1/24             │    │
│  │ ↕ ISP 1 (Cable)         │        │ DHCP Server                │    │
│  └─────────────────────────┘        │ ↕ Local Devices            │    │
│                                     └────────────────────────────┘    │
│  ┌─────────────────────────┐        ┌────────────────────────────┐    │
│  │ WAN 2 (enp2s0)          │        │ LAN 2 (enp6s0)             │    │
│  │ Priority: 2             │        │ 192.168.2.1/24             │    │
│  │ ↕ ISP 2 (DSL)           │        └────────────────────────────┘    │
│  └─────────────────────────┘                                          │
│                                     ┌────────────────────────────┐    │
│  ┌─────────────────────────┐        │ LAN 3 (enp7s0)             │    │
│  │ WAN 3 (enp3s0)          │        │ 192.168.3.1/24             │    │
│  │ Priority: 3             │        └────────────────────────────┘    │
│  │ ↕ ISP 3 (LTE)           │                                          │
│  └─────────────────────────┘        ┌────────────────────────────┐    │
│                                     │ LAN 4 (enp8s0)             │    │
│  ┌─────────────────────────┐        │ 192.168.4.1/24             │    │
│  │ WAN 4 (enp4s0)          │        └────────────────────────────┘    │
│  │ Priority: 4             │                                          │
│  │ ↕ ISP 4 (5G)            │                                          │
│  └─────────────────────────┘                                          │
└─────────────────────────────────────────────────────────────────────────┘
         │                │                │                │
         └────────────────┴────────────────┴────────────────┘
                              │
                              ↓
              ┌───────────────────────────────┐
              │    ENCRYPTED TUNNELS (UDP)    │
              │         Port 8443             │
              └───────────────────────────────┘
                              │
                              ↓
              ════════════════════════════════
                      INTERNET
              ════════════════════════════════
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    VPS SERVER (Cloud Server)                             │
│                   /Users/viewvision/Desktop/                            │
│                     Server-side bondlink                                │
├─────────────────────────────────────────────────────────────────────────┤
│  • Tunnel Aggregation                                                   │
│  • Traffic Routing                                                      │
│  • Load Balancing                                                       │
│  • Packet Reordering                                                    │
│  • Health Monitoring                                                    │
│  • Statistics Tracking                                                  │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ↓
              ════════════════════════════════
                  INTERNET DESTINATIONS
              ════════════════════════════════


DATA FLOW:
──────────
1. LAN device → LAN interface → NAT/Routing
2. Daemon distributes packets across tunnels (load balancing)
3. Each tunnel → WAN interface → ISP → Internet
4. Packets arrive at VPS via multiple tunnels
5. VPS aggregates and reorders packets
6. VPS routes to internet destination
7. Return traffic follows reverse path

MONITORING:
───────────
• WAN Manager checks health every 5 seconds
• Statistics updated every 1 second
• WebSocket broadcasts to UI every 1 second
• Tunnels send heartbeat every 10 seconds
• Automatic failover on WAN failure
• Automatic reconnection on tunnel failure
```

## Key Features Illustrated

### Real-Time Updates
- WebSocket pushes updates to browser every second
- No page refresh needed
- Instant feedback on port enable/disable

### Intelligent Failover
- Continuous health monitoring
- Automatic rerouting on failure
- Seamless user experience

### Load Balancing
- Traffic distributed across all healthy WANs
- Multiple modes: round-robin, weighted, latency-based
- Packet reordering for TCP

### Production Ready
- Systemd service with auto-restart
- Structured logging with rotation
- Configuration validation
- Error handling and recovery
