"""Web API for Bondlink client - REST endpoints and WebSocket"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Set
import asyncio
import json
from pathlib import Path

from client.core.logger import get_logger
from client.network.wan_manager import WANInterfaceManager, InterfaceStatus

logger = get_logger(__name__)


class ConnectionManager:
    """Manage WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("websocket_connected", total_connections=len(self.active_connections))
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.active_connections.discard(websocket)
        logger.info("websocket_disconnected", total_connections=len(self.active_connections))
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
        
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error("websocket_broadcast_error", error=str(e))
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


class BondlinkAPI:
    """FastAPI application for Bondlink web interface"""
    
    def __init__(self, wan_manager: WANInterfaceManager, host: str = "0.0.0.0", port: int = 8080):
        """Initialize API
        
        Args:
            wan_manager: WAN interface manager instance
            host: Host to bind to
            port: Port to bind to
        """
        self.wan_manager = wan_manager
        self.host = host
        self.port = port
        self.app = FastAPI(title="Bondlink Client API", version="1.0.0")
        self.ws_manager = ConnectionManager()
        self._broadcast_task = None
        
        # Setup CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Setup routes
        self._setup_routes()
        
        # Mount static files
        static_dir = Path(__file__).parent.parent.parent / "web" / "static"
        if static_dir.exists():
            self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def root():
            """Serve main dashboard page"""
            html_path = Path(__file__).parent.parent.parent / "web" / "index.html"
            if html_path.exists():
                return html_path.read_text()
            return "<h1>Bondlink Client</h1><p>Web UI not found. Please check installation.</p>"
        
        @self.app.get("/api/status")
        async def get_status():
            """Get overall system status"""
            interfaces = self.wan_manager.get_all_interfaces()
            healthy_count = len(self.wan_manager.get_healthy_interfaces())
            send_rate, recv_rate = self.wan_manager.get_total_bandwidth()
            
            return {
                "status": "running",
                "timestamp": asyncio.get_event_loop().time(),
                "wan_interfaces": {
                    "total": len(interfaces),
                    "healthy": healthy_count,
                    "degraded": sum(1 for w in interfaces.values() if w.status == InterfaceStatus.DEGRADED),
                    "down": sum(1 for w in interfaces.values() if w.status == InterfaceStatus.DOWN),
                },
                "total_bandwidth": {
                    "upload_bps": send_rate,
                    "download_bps": recv_rate,
                    "upload_mbps": send_rate / (1024 * 1024),
                    "download_mbps": recv_rate / (1024 * 1024),
                }
            }
        
        @self.app.get("/api/interfaces")
        async def get_interfaces():
            """Get all WAN interfaces with detailed stats"""
            interfaces = self.wan_manager.get_all_interfaces()
            
            return {
                "interfaces": [
                    {
                        "name": wan.config.name,
                        "interface": wan.config.interface,
                        "enabled": wan.enabled,
                        "status": wan.status.value,
                        "priority": wan.config.priority,
                        "weight": wan.config.weight,
                        "ip_address": wan.ip_address,
                        "gateway": wan.gateway,
                        "tunnel_connected": wan.tunnel_connected,
                        "stats": {
                            "bytes_sent": wan.stats.bytes_sent,
                            "bytes_recv": wan.stats.bytes_recv,
                            "packets_sent": wan.stats.packets_sent,
                            "packets_recv": wan.stats.packets_recv,
                            "send_rate_bps": wan.stats.send_rate,
                            "recv_rate_bps": wan.stats.recv_rate,
                            "send_rate_mbps": wan.stats.send_rate / (1024 * 1024),
                            "recv_rate_mbps": wan.stats.recv_rate / (1024 * 1024),
                            "errors_in": wan.stats.errors_in,
                            "errors_out": wan.stats.errors_out,
                            "drops_in": wan.stats.drops_in,
                            "drops_out": wan.stats.drops_out,
                        },
                        "health": {
                            "is_healthy": wan.health.is_healthy,
                            "latency_ms": round(wan.health.latency_ms, 2),
                            "packet_loss": round(wan.health.packet_loss * 100, 2),
                            "consecutive_failures": wan.health.consecutive_failures,
                            "consecutive_successes": wan.health.consecutive_successes,
                        }
                    }
                    for wan in interfaces.values()
                ]
            }
        
        @self.app.get("/api/interfaces/{name}")
        async def get_interface(name: str):
            """Get specific interface details"""
            wan = self.wan_manager.get_interface(name)
            if not wan:
                raise HTTPException(status_code=404, detail="Interface not found")
            
            return {
                "name": wan.config.name,
                "interface": wan.config.interface,
                "enabled": wan.enabled,
                "status": wan.status.value,
                "priority": wan.config.priority,
                "weight": wan.config.weight,
                "ip_address": wan.ip_address,
                "gateway": wan.gateway,
                "tunnel_connected": wan.tunnel_connected,
                "stats": {
                    "bytes_sent": wan.stats.bytes_sent,
                    "bytes_recv": wan.stats.bytes_recv,
                    "send_rate_bps": wan.stats.send_rate,
                    "recv_rate_bps": wan.stats.recv_rate,
                    "send_rate_mbps": wan.stats.send_rate / (1024 * 1024),
                    "recv_rate_mbps": wan.stats.recv_rate / (1024 * 1024),
                },
                "health": {
                    "is_healthy": wan.health.is_healthy,
                    "latency_ms": round(wan.health.latency_ms, 2),
                    "packet_loss": round(wan.health.packet_loss * 100, 2),
                }
            }
        
        @self.app.post("/api/interfaces/{name}/enable")
        async def enable_interface(name: str):
            """Enable a WAN interface"""
            success = await self.wan_manager.enable_interface(name)
            if not success:
                raise HTTPException(status_code=404, detail="Interface not found")
            return {"status": "success", "message": f"Interface {name} enabled"}
        
        @self.app.post("/api/interfaces/{name}/disable")
        async def disable_interface(name: str):
            """Disable a WAN interface"""
            success = await self.wan_manager.disable_interface(name)
            if not success:
                raise HTTPException(status_code=404, detail="Interface not found")
            return {"status": "success", "message": f"Interface {name} disabled"}
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates"""
            await self.ws_manager.connect(websocket)
            try:
                while True:
                    # Keep connection alive and handle incoming messages
                    data = await websocket.receive_text()
                    # Echo back for testing
                    await websocket.send_json({"type": "pong", "data": data})
            except WebSocketDisconnect:
                self.ws_manager.disconnect(websocket)
            except Exception as e:
                logger.error("websocket_error", error=str(e))
                self.ws_manager.disconnect(websocket)
    
    async def start_broadcasting(self):
        """Start broadcasting updates to WebSocket clients"""
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info("api_broadcast_started")
    
    async def _broadcast_loop(self):
        """Broadcast loop for real-time updates"""
        while True:
            try:
                # Gather current stats
                interfaces = self.wan_manager.get_all_interfaces()
                send_rate, recv_rate = self.wan_manager.get_total_bandwidth()
                
                message = {
                    "type": "update",
                    "timestamp": asyncio.get_event_loop().time(),
                    "total_bandwidth": {
                        "upload_bps": send_rate,
                        "download_bps": recv_rate,
                        "upload_mbps": round(send_rate / (1024 * 1024), 2),
                        "download_mbps": round(recv_rate / (1024 * 1024), 2),
                    },
                    "interfaces": [
                        {
                            "name": wan.config.name,
                            "enabled": wan.enabled,
                            "status": wan.status.value,
                            "tunnel_connected": wan.tunnel_connected,
                            "send_rate_mbps": round(wan.stats.send_rate / (1024 * 1024), 2),
                            "recv_rate_mbps": round(wan.stats.recv_rate / (1024 * 1024), 2),
                            "latency_ms": round(wan.health.latency_ms, 2),
                            "packet_loss": round(wan.health.packet_loss * 100, 2),
                            "is_healthy": wan.health.is_healthy,
                        }
                        for wan in interfaces.values()
                    ]
                }
                
                await self.ws_manager.broadcast(message)
                await asyncio.sleep(1)  # Broadcast every second
                
            except Exception as e:
                logger.error("broadcast_loop_error", error=str(e))
                await asyncio.sleep(5)
    
    async def start(self):
        """Start API server"""
        import uvicorn
        
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
            access_log=False,
        )
        server = uvicorn.Server(config)
        
        # Start broadcasting task
        await self.start_broadcasting()
        
        logger.info("api_server_starting", host=self.host, port=self.port)
        await server.serve()
