"""WAN Interface Manager - Monitor and manage WAN connections"""

import asyncio
import time
import psutil
import netifaces
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum
import subprocess
import platform

from client.core.config import WANInterfaceConfig, HealthCheckConfig
from client.core.logger import get_logger

logger = get_logger(__name__)


class InterfaceStatus(Enum):
    """Interface status enumeration"""
    UP = "up"
    DOWN = "down"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class InterfaceStats:
    """Network interface statistics"""
    bytes_sent: int = 0
    bytes_recv: int = 0
    packets_sent: int = 0
    packets_recv: int = 0
    errors_in: int = 0
    errors_out: int = 0
    drops_in: int = 0
    drops_out: int = 0
    
    # Rate calculations (bytes per second)
    send_rate: float = 0.0
    recv_rate: float = 0.0
    
    # Timestamp for rate calculation
    last_update: float = field(default_factory=time.time)


@dataclass
class HealthStatus:
    """Health check status for a WAN interface"""
    is_healthy: bool = False
    latency_ms: float = 0.0
    packet_loss: float = 0.0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_check: float = field(default_factory=time.time)
    last_success: Optional[float] = None
    last_failure: Optional[float] = None


@dataclass
class WANInterface:
    """WAN Interface state"""
    config: WANInterfaceConfig
    status: InterfaceStatus = InterfaceStatus.UNKNOWN
    stats: InterfaceStats = field(default_factory=InterfaceStats)
    health: HealthStatus = field(default_factory=HealthStatus)
    ip_address: Optional[str] = None
    gateway: Optional[str] = None
    enabled: bool = True
    tunnel_connected: bool = False


class WANInterfaceManager:
    """Manages WAN interfaces, health checks, and statistics"""
    
    def __init__(
        self,
        wan_configs: List[WANInterfaceConfig],
        health_config: HealthCheckConfig
    ):
        """Initialize WAN interface manager
        
        Args:
            wan_configs: List of WAN interface configurations
            health_config: Health check configuration
        """
        self.wan_configs = wan_configs
        self.health_config = health_config
        self.interfaces: Dict[str, WANInterface] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
        
        # Initialize interfaces
        for config in wan_configs:
            self.interfaces[config.name] = WANInterface(
                config=config,
                enabled=config.enabled
            )
        
        logger.info("wan_manager_initialized", interface_count=len(self.interfaces))
    
    async def start(self) -> None:
        """Start monitoring WAN interfaces"""
        if self._running:
            logger.warning("wan_manager_already_running")
            return
        
        self._running = True
        logger.info("wan_manager_starting")
        
        # Start monitoring tasks
        self._tasks = [
            asyncio.create_task(self._monitor_interfaces()),
            asyncio.create_task(self._update_statistics()),
        ]
        
        if self.health_config.enabled:
            self._tasks.append(asyncio.create_task(self._health_check_loop()))
        
        logger.info("wan_manager_started", tasks=len(self._tasks))
    
    async def stop(self) -> None:
        """Stop monitoring WAN interfaces"""
        if not self._running:
            return
        
        logger.info("wan_manager_stopping")
        self._running = False
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        
        logger.info("wan_manager_stopped")
    
    async def _monitor_interfaces(self) -> None:
        """Monitor interface status continuously"""
        while self._running:
            try:
                for name, wan in self.interfaces.items():
                    # Check if interface exists
                    if wan.config.interface not in netifaces.interfaces():
                        wan.status = InterfaceStatus.UNKNOWN
                        wan.ip_address = None
                        wan.gateway = None
                        logger.debug("interface_not_found", interface=wan.config.interface)
                        continue
                    
                    # Get interface addresses
                    addrs = netifaces.ifaddresses(wan.config.interface)
                    
                    # Get IPv4 address
                    if netifaces.AF_INET in addrs:
                        wan.ip_address = addrs[netifaces.AF_INET][0].get('addr')
                    
                    # Get gateway
                    gateways = netifaces.gateways()
                    if 'default' in gateways and netifaces.AF_INET in gateways['default']:
                        default_gw = gateways['default'][netifaces.AF_INET]
                        if default_gw[1] == wan.config.interface:
                            wan.gateway = default_gw[0]
                    
                    # Check if interface is up
                    try:
                        stats = psutil.net_if_stats().get(wan.config.interface)
                        if stats and stats.isup:
                            if wan.status == InterfaceStatus.DOWN:
                                logger.info("interface_up", interface=wan.config.interface)
                            wan.status = InterfaceStatus.UP
                        else:
                            if wan.status == InterfaceStatus.UP:
                                logger.warning("interface_down", interface=wan.config.interface)
                            wan.status = InterfaceStatus.DOWN
                    except Exception as e:
                        logger.error("interface_check_error", interface=wan.config.interface, error=str(e))
                        wan.status = InterfaceStatus.UNKNOWN
                
                await asyncio.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                logger.error("monitor_interfaces_error", error=str(e))
                await asyncio.sleep(5)
    
    async def _update_statistics(self) -> None:
        """Update interface statistics and calculate rates"""
        while self._running:
            try:
                io_counters = psutil.net_io_counters(pernic=True)
                current_time = time.time()
                
                for name, wan in self.interfaces.items():
                    if wan.config.interface not in io_counters:
                        continue
                    
                    counter = io_counters[wan.config.interface]
                    
                    # Calculate rates
                    time_delta = current_time - wan.stats.last_update
                    if time_delta > 0:
                        bytes_sent_delta = counter.bytes_sent - wan.stats.bytes_sent
                        bytes_recv_delta = counter.bytes_recv - wan.stats.bytes_recv
                        
                        wan.stats.send_rate = bytes_sent_delta / time_delta
                        wan.stats.recv_rate = bytes_recv_delta / time_delta
                    
                    # Update counters
                    wan.stats.bytes_sent = counter.bytes_sent
                    wan.stats.bytes_recv = counter.bytes_recv
                    wan.stats.packets_sent = counter.packets_sent
                    wan.stats.packets_recv = counter.packets_recv
                    wan.stats.errors_in = counter.errin
                    wan.stats.errors_out = counter.errout
                    wan.stats.drops_in = counter.dropin
                    wan.stats.drops_out = counter.dropout
                    wan.stats.last_update = current_time
                
                await asyncio.sleep(1)  # Update every second
                
            except Exception as e:
                logger.error("update_statistics_error", error=str(e))
                await asyncio.sleep(5)
    
    async def _health_check_loop(self) -> None:
        """Perform periodic health checks on all WAN interfaces"""
        while self._running:
            try:
                # Check all enabled interfaces
                tasks = []
                for name, wan in self.interfaces.items():
                    if wan.enabled and wan.status == InterfaceStatus.UP:
                        tasks.append(self._check_interface_health(wan))
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                await asyncio.sleep(self.health_config.interval)
                
            except Exception as e:
                logger.error("health_check_loop_error", error=str(e))
                await asyncio.sleep(self.health_config.interval)
    
    async def _check_interface_health(self, wan: WANInterface) -> None:
        """Check health of a single WAN interface
        
        Args:
            wan: WAN interface to check
        """
        try:
            results = []
            
            # Ping each target
            for target in self.health_config.ping_targets:
                success, latency = await self._ping_via_interface(
                    wan.config.interface,
                    target,
                    self.health_config.timeout
                )
                results.append((success, latency))
            
            # Calculate packet loss and average latency
            successful = [r for r in results if r[0]]
            packet_loss = 1.0 - (len(successful) / len(results))
            avg_latency = sum(r[1] for r in successful) / len(successful) if successful else 0.0
            
            wan.health.packet_loss = packet_loss
            wan.health.latency_ms = avg_latency
            wan.health.last_check = time.time()
            
            # Determine health status
            if len(successful) >= len(results) // 2:  # At least 50% success
                wan.health.is_healthy = True
                wan.health.consecutive_successes += 1
                wan.health.consecutive_failures = 0
                wan.health.last_success = time.time()
                
                if wan.status == InterfaceStatus.DEGRADED:
                    if wan.health.consecutive_successes >= self.health_config.recovery_threshold:
                        wan.status = InterfaceStatus.UP
                        logger.info("interface_recovered", interface=wan.config.interface)
            else:
                wan.health.is_healthy = False
                wan.health.consecutive_failures += 1
                wan.health.consecutive_successes = 0
                wan.health.last_failure = time.time()
                
                if wan.health.consecutive_failures >= self.health_config.failure_threshold:
                    if wan.status == InterfaceStatus.UP:
                        wan.status = InterfaceStatus.DEGRADED
                        logger.warning("interface_degraded", interface=wan.config.interface,
                                     packet_loss=packet_loss, latency=avg_latency)
        
        except Exception as e:
            logger.error("health_check_error", interface=wan.config.interface, error=str(e))
    
    async def _ping_via_interface(
        self,
        interface: str,
        target: str,
        timeout: int
    ) -> tuple[bool, float]:
        """Ping a target via specific interface
        
        Args:
            interface: Network interface name
            target: IP address to ping
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (success, latency_ms)
        """
        try:
            # Use ping command with interface binding
            cmd = [
                "ping",
                "-I", interface,
                "-c", "1",
                "-W", str(timeout),
                target
            ]
            
            start_time = time.time()
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout + 1
            )
            
            latency = (time.time() - start_time) * 1000  # Convert to ms
            
            return process.returncode == 0, latency
            
        except asyncio.TimeoutError:
            return False, 0.0
        except Exception as e:
            logger.debug("ping_error", interface=interface, target=target, error=str(e))
            return False, 0.0
    
    def get_interface(self, name: str) -> Optional[WANInterface]:
        """Get WAN interface by name
        
        Args:
            name: Interface name
            
        Returns:
            WANInterface or None if not found
        """
        return self.interfaces.get(name)
    
    def get_all_interfaces(self) -> Dict[str, WANInterface]:
        """Get all WAN interfaces
        
        Returns:
            Dictionary of all WAN interfaces
        """
        return self.interfaces
    
    def get_healthy_interfaces(self) -> List[WANInterface]:
        """Get list of healthy WAN interfaces
        
        Returns:
            List of healthy WAN interfaces
        """
        return [
            wan for wan in self.interfaces.values()
            if wan.enabled and wan.status == InterfaceStatus.UP and wan.health.is_healthy
        ]
    
    def get_total_bandwidth(self) -> tuple[float, float]:
        """Get total bandwidth across all healthy interfaces
        
        Returns:
            Tuple of (send_rate, recv_rate) in bytes per second
        """
        healthy = self.get_healthy_interfaces()
        send_rate = sum(wan.stats.send_rate for wan in healthy)
        recv_rate = sum(wan.stats.recv_rate for wan in healthy)
        return send_rate, recv_rate
    
    async def enable_interface(self, name: str) -> bool:
        """Enable a WAN interface
        
        Args:
            name: Interface name
            
        Returns:
            True if successful
        """
        wan = self.interfaces.get(name)
        if not wan:
            logger.error("interface_not_found", interface=name)
            return False
        
        wan.enabled = True
        logger.info("interface_enabled", interface=name)
        return True
    
    async def disable_interface(self, name: str) -> bool:
        """Disable a WAN interface
        
        Args:
            name: Interface name
            
        Returns:
            True if successful
        """
        wan = self.interfaces.get(name)
        if not wan:
            logger.error("interface_not_found", interface=name)
            return False
        
        wan.enabled = False
        wan.status = InterfaceStatus.DOWN
        logger.info("interface_disabled", interface=name)
        return True
