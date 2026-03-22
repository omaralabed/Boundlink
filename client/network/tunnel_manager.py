"""Tunnel Manager - Establish and maintain tunnels to VPS server"""

import asyncio
import socket
import struct
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any
from enum import Enum

from client.core.config import ServerConfig, TunnelConfig
from client.core.logger import get_logger
from client.network.wan_manager import WANInterface, InterfaceStatus

logger = get_logger(__name__)


class TunnelState(Enum):
    """Tunnel connection state"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class TunnelStats:
    """Statistics for a tunnel"""
    bytes_sent: int = 0
    bytes_recv: int = 0
    packets_sent: int = 0
    packets_recv: int = 0
    connected_at: Optional[float] = None
    last_activity: float = field(default_factory=time.time)
    reconnect_count: int = 0


@dataclass
class Tunnel:
    """Tunnel instance for a WAN interface"""
    wan_interface: WANInterface
    state: TunnelState = TunnelState.DISCONNECTED
    stats: TunnelStats = field(default_factory=TunnelStats)
    reader: Optional[asyncio.StreamReader] = None
    writer: Optional[asyncio.StreamWriter] = None
    socket: Optional[Any] = None  # socket.socket


class TunnelManager:
    """Manages tunnels to VPS server over each WAN interface"""
    
    def __init__(
        self,
        server_config: ServerConfig,
        tunnel_config: TunnelConfig,
        wan_interfaces: Dict[str, WANInterface]
    ):
        """Initialize tunnel manager
        
        Args:
            server_config: Server connection configuration
            tunnel_config: Tunnel configuration
            wan_interfaces: Dictionary of WAN interfaces
        """
        self.server_config = server_config
        self.tunnel_config = tunnel_config
        self.wan_interfaces = wan_interfaces
        self.tunnels: Dict[str, Tunnel] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
        
        # Initialize tunnels for each WAN
        for name, wan in wan_interfaces.items():
            self.tunnels[name] = Tunnel(wan_interface=wan)
        
        logger.info("tunnel_manager_initialized", tunnel_count=len(self.tunnels))
    
    async def start(self) -> None:
        """Start managing tunnels"""
        if self._running:
            logger.warning("tunnel_manager_already_running")
            return
        
        self._running = True
        logger.info("tunnel_manager_starting")
        
        # Start tunnel management tasks for each WAN
        for name in self.tunnels.keys():
            task = asyncio.create_task(self._manage_tunnel(name))
            self._tasks.append(task)
        
        # Start heartbeat task
        self._tasks.append(asyncio.create_task(self._heartbeat_loop()))
        
        logger.info("tunnel_manager_started", tasks=len(self._tasks))
    
    async def stop(self) -> None:
        """Stop managing tunnels"""
        if not self._running:
            return
        
        logger.info("tunnel_manager_stopping")
        self._running = False
        
        # Disconnect all tunnels
        for name in self.tunnels.keys():
            await self._disconnect_tunnel(name)
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        
        logger.info("tunnel_manager_stopped")
    
    async def _manage_tunnel(self, name: str) -> None:
        """Manage a single tunnel lifecycle
        
        Args:
            name: WAN interface name
        """
        tunnel = self.tunnels[name]
        
        while self._running:
            try:
                wan = tunnel.wan_interface
                
                # Only connect if WAN is enabled and healthy
                if not wan.enabled or wan.status != InterfaceStatus.UP:
                    if tunnel.state != TunnelState.DISCONNECTED:
                        await self._disconnect_tunnel(name)
                    await asyncio.sleep(5)
                    continue
                
                # Connect if not connected
                if tunnel.state == TunnelState.DISCONNECTED:
                    await self._connect_tunnel(name)
                
                # Maintain connection
                if tunnel.state == TunnelState.CONNECTED:
                    # Check if connection is still alive
                    if not await self._check_tunnel_health(name):
                        logger.warning("tunnel_health_check_failed", interface=name)
                        await self._reconnect_tunnel(name)
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error("tunnel_management_error", interface=name, error=str(e))
                tunnel.state = TunnelState.FAILED
                await asyncio.sleep(5)
    
    async def _connect_tunnel(self, name: str) -> bool:
        """Establish tunnel connection
        
        Args:
            name: WAN interface name
            
        Returns:
            True if connection successful
        """
        tunnel = self.tunnels[name]
        wan = tunnel.wan_interface
        
        if tunnel.state == TunnelState.CONNECTING:
            return False
        
        tunnel.state = TunnelState.CONNECTING
        logger.info("tunnel_connecting", interface=name, 
                   server=f"{self.server_config.host}:{self.server_config.port}")
        
        try:
            if self.tunnel_config.protocol == "udp":
                success = await self._connect_udp_tunnel(name)
            else:
                success = await self._connect_tcp_tunnel(name)
            
            if success:
                tunnel.state = TunnelState.CONNECTED
                tunnel.stats.connected_at = time.time()
                wan.tunnel_connected = True
                logger.info("tunnel_connected", interface=name)
                return True
            else:
                tunnel.state = TunnelState.FAILED
                return False
                
        except Exception as e:
            logger.error("tunnel_connect_error", interface=name, error=str(e))
            tunnel.state = TunnelState.FAILED
            return False
    
    async def _connect_tcp_tunnel(self, name: str) -> bool:
        """Connect TCP tunnel
        
        Args:
            name: WAN interface name
            
        Returns:
            True if successful
        """
        tunnel = self.tunnels[name]
        wan = tunnel.wan_interface
        
        try:
            # Create socket bound to specific interface
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, 
                          wan.config.interface.encode())
            sock.setblocking(False)
            
            # Connect to server
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(
                    self.server_config.host,
                    self.server_config.port,
                    sock=sock
                ),
                timeout=self.server_config.connect_timeout
            )
            
            # Send authentication
            auth_packet = self._build_auth_packet(name)
            writer.write(auth_packet)
            await writer.drain()
            
            # Wait for auth response
            response = await asyncio.wait_for(
                reader.read(4),
                timeout=5
            )
            
            if response != b'OK\r\n':
                logger.error("tunnel_auth_failed", interface=name)
                writer.close()
                await writer.wait_closed()
                return False
            
            tunnel.reader = reader
            tunnel.writer = writer
            tunnel.socket = sock
            
            # Start tunnel I/O task
            task = asyncio.create_task(self._tunnel_io_loop(name))
            self._tasks.append(task)
            
            return True
            
        except Exception as e:
            logger.error("tcp_tunnel_connect_error", interface=name, error=str(e))
            return False
    
    async def _connect_udp_tunnel(self, name: str) -> bool:
        """Connect UDP tunnel
        
        Args:
            name: WAN interface name
            
        Returns:
            True if successful
        """
        tunnel = self.tunnels[name]
        wan = tunnel.wan_interface
        
        try:
            # Create UDP socket bound to specific interface
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE,
                          wan.config.interface.encode())
            sock.setblocking(False)
            
            # Set socket options
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 
                          self.tunnel_config.send_buffer_size)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF,
                          self.tunnel_config.recv_buffer_size)
            
            # Connect to server
            sock.connect((self.server_config.host, self.server_config.port))
            
            # Send authentication packet
            auth_packet = self._build_auth_packet(name)
            sock.send(auth_packet)
            
            # Wait for response (with timeout)
            loop = asyncio.get_event_loop()
            try:
                response = await asyncio.wait_for(
                    loop.sock_recv(sock, 4),
                    timeout=5
                )
                
                if response != b'OK\r\n':
                    logger.error("tunnel_auth_failed", interface=name)
                    sock.close()
                    return False
                    
            except asyncio.TimeoutError:
                logger.error("tunnel_auth_timeout", interface=name)
                sock.close()
                return False
            
            tunnel.socket = sock
            
            # Start tunnel I/O task
            task = asyncio.create_task(self._tunnel_io_loop(name))
            self._tasks.append(task)
            
            return True
            
        except Exception as e:
            logger.error("udp_tunnel_connect_error", interface=name, error=str(e))
            return False
    
    def _build_auth_packet(self, interface_name: str) -> bytes:
        """Build authentication packet
        
        Args:
            interface_name: Interface name
            
        Returns:
            Authentication packet bytes
        """
        # Packet format: AUTH|<interface_name>|<auth_token>
        auth_data = f"AUTH|{interface_name}|{self.server_config.auth_token}"
        return auth_data.encode('utf-8')
    
    async def _tunnel_io_loop(self, name: str) -> None:
        """Tunnel I/O loop for handling data
        
        Args:
            name: WAN interface name
        """
        tunnel = self.tunnels[name]
        
        # This is a placeholder - actual implementation will handle
        # packet routing between LAN and tunnel
        while self._running and tunnel.state == TunnelState.CONNECTED:
            try:
                await asyncio.sleep(0.1)
                # TODO: Handle packet forwarding
            except Exception as e:
                logger.error("tunnel_io_error", interface=name, error=str(e))
                break
    
    async def _disconnect_tunnel(self, name: str) -> None:
        """Disconnect a tunnel
        
        Args:
            name: WAN interface name
        """
        tunnel = self.tunnels[name]
        
        if tunnel.state == TunnelState.DISCONNECTED:
            return
        
        logger.info("tunnel_disconnecting", interface=name)
        
        try:
            if tunnel.writer:
                tunnel.writer.close()
                await tunnel.writer.wait_closed()
            
            if tunnel.socket:
                tunnel.socket.close()
            
            tunnel.reader = None
            tunnel.writer = None
            tunnel.socket = None
            tunnel.state = TunnelState.DISCONNECTED
            tunnel.wan_interface.tunnel_connected = False
            
            logger.info("tunnel_disconnected", interface=name)
            
        except Exception as e:
            logger.error("tunnel_disconnect_error", interface=name, error=str(e))
    
    async def _reconnect_tunnel(self, name: str) -> None:
        """Reconnect a tunnel
        
        Args:
            name: WAN interface name
        """
        tunnel = self.tunnels[name]
        tunnel.state = TunnelState.RECONNECTING
        tunnel.stats.reconnect_count += 1
        
        logger.info("tunnel_reconnecting", interface=name, 
                   reconnect_count=tunnel.stats.reconnect_count)
        
        await self._disconnect_tunnel(name)
        await asyncio.sleep(self.server_config.reconnect_interval)
        await self._connect_tunnel(name)
    
    async def _check_tunnel_health(self, name: str) -> bool:
        """Check if tunnel is healthy
        
        Args:
            name: WAN interface name
            
        Returns:
            True if tunnel is healthy
        """
        tunnel = self.tunnels[name]
        
        # Check if connection is still alive
        if tunnel.socket and tunnel.socket.fileno() == -1:
            return False
        
        # Check last activity time
        if time.time() - tunnel.stats.last_activity > 30:
            return False
        
        return True
    
    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats on all connected tunnels"""
        while self._running:
            try:
                for name, tunnel in self.tunnels.items():
                    if tunnel.state == TunnelState.CONNECTED:
                        await self._send_heartbeat(name)
                
                await asyncio.sleep(10)  # Send heartbeat every 10 seconds
                
            except Exception as e:
                logger.error("heartbeat_loop_error", error=str(e))
                await asyncio.sleep(10)
    
    async def _send_heartbeat(self, name: str) -> None:
        """Send heartbeat packet
        
        Args:
            name: WAN interface name
        """
        tunnel = self.tunnels[name]
        
        try:
            heartbeat = b'HEARTBEAT'
            
            if tunnel.writer:
                tunnel.writer.write(heartbeat)
                await tunnel.writer.drain()
            elif tunnel.socket:
                tunnel.socket.send(heartbeat)
            
            tunnel.stats.last_activity = time.time()
            
        except Exception as e:
            logger.error("heartbeat_send_error", interface=name, error=str(e))
    
    def get_connected_tunnels(self) -> List[str]:
        """Get list of connected tunnel names
        
        Returns:
            List of connected tunnel interface names
        """
        return [
            name for name, tunnel in self.tunnels.items()
            if tunnel.state == TunnelState.CONNECTED
        ]
    
    def get_tunnel_stats(self, name: str) -> Optional[TunnelStats]:
        """Get tunnel statistics
        
        Args:
            name: WAN interface name
            
        Returns:
            Tunnel stats or None
        """
        tunnel = self.tunnels.get(name)
        return tunnel.stats if tunnel else None
