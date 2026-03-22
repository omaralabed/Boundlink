"""Configuration management for Bondlink client"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ServerConfig:
    """Server connection configuration"""
    host: str
    port: int
    auth_token: str
    connect_timeout: int = 10
    reconnect_interval: int = 5
    max_reconnect_attempts: int = 0


@dataclass
class WANInterfaceConfig:
    """WAN interface configuration"""
    name: str
    interface: str
    priority: int
    weight: float = 1.0
    enabled: bool = True


@dataclass
class LANInterfaceConfig:
    """LAN interface configuration"""
    name: str
    interface: str
    ip: str
    netmask: str
    dhcp_enabled: bool = False
    dhcp_range_start: Optional[str] = None
    dhcp_range_end: Optional[str] = None


@dataclass
class HealthCheckConfig:
    """Health check configuration"""
    enabled: bool = True
    interval: int = 5
    timeout: int = 3
    failure_threshold: int = 3
    recovery_threshold: int = 2
    ping_targets: List[str] = field(default_factory=lambda: ["8.8.8.8", "1.1.1.1"])


@dataclass
class TrafficConfig:
    """Traffic distribution configuration"""
    mode: str = "round_robin"
    packet_reordering: bool = True
    reorder_buffer_size: int = 1000
    failover_enabled: bool = True
    failover_delay: int = 2


@dataclass
class TunnelConfig:
    """Tunnel configuration"""
    protocol: str = "udp"
    mtu: int = 1400
    encryption: bool = True
    compression: bool = False
    send_buffer_size: int = 2097152
    recv_buffer_size: int = 2097152


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    file: str = "/var/log/bondlink/client.log"
    max_size_mb: int = 100
    backup_count: int = 5
    console: bool = True
    format: str = "json"


@dataclass
class MonitoringConfig:
    """Monitoring configuration"""
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    stats_interval: int = 10


@dataclass
class SystemConfig:
    """System configuration"""
    run_as_user: str = "root"
    pid_file: str = "/var/run/bondlink/client.pid"
    enable_forwarding: bool = True
    enable_masquerading: bool = True


class Config:
    """Main configuration class"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration
        
        Args:
            config_path: Path to configuration file. If None, uses default locations.
        """
        self.config_path = self._find_config_path(config_path)
        self._raw_config: Dict[str, Any] = {}
        self.load()
        
    def _find_config_path(self, config_path: Optional[str] = None) -> Path:
        """Find configuration file path
        
        Args:
            config_path: Explicit config path or None to search default locations
            
        Returns:
            Path to configuration file
        """
        if config_path:
            return Path(config_path)
            
        # Search order: CWD, /etc/bondlink, package config dir
        search_paths = [
            Path.cwd() / "config" / "client.yaml",
            Path("/etc/bondlink/client.yaml"),
            Path(__file__).parent.parent.parent / "config" / "client.yaml",
        ]
        
        for path in search_paths:
            if path.exists():
                return path
                
        # Return default path even if it doesn't exist
        return search_paths[0]
    
    def load(self) -> None:
        """Load configuration from file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
        with open(self.config_path, "r") as f:
            self._raw_config = yaml.safe_load(f)
            
        # Parse configuration sections
        self.server = self._parse_server()
        self.wan_interfaces = self._parse_wan_interfaces()
        self.lan_interfaces = self._parse_lan_interfaces()
        self.health_check = self._parse_health_check()
        self.traffic = self._parse_traffic()
        self.tunnel = self._parse_tunnel()
        self.logging = self._parse_logging()
        self.monitoring = self._parse_monitoring()
        self.system = self._parse_system()
        
    def _parse_server(self) -> ServerConfig:
        """Parse server configuration"""
        server = self._raw_config.get("server", {})
        return ServerConfig(
            host=server.get("host", ""),
            port=server.get("port", 8443),
            auth_token=server.get("auth_token", ""),
            connect_timeout=server.get("connect_timeout", 10),
            reconnect_interval=server.get("reconnect_interval", 5),
            max_reconnect_attempts=server.get("max_reconnect_attempts", 0),
        )
    
    def _parse_wan_interfaces(self) -> List[WANInterfaceConfig]:
        """Parse WAN interface configurations"""
        wan_list = self._raw_config.get("wan_interfaces", [])
        return [
            WANInterfaceConfig(
                name=wan.get("name", ""),
                interface=wan.get("interface", ""),
                priority=wan.get("priority", 0),
                weight=wan.get("weight", 1.0),
                enabled=wan.get("enabled", True),
            )
            for wan in wan_list
        ]
    
    def _parse_lan_interfaces(self) -> List[LANInterfaceConfig]:
        """Parse LAN interface configurations"""
        lan_list = self._raw_config.get("lan_interfaces", [])
        return [
            LANInterfaceConfig(
                name=lan.get("name", ""),
                interface=lan.get("interface", ""),
                ip=lan.get("ip", ""),
                netmask=lan.get("netmask", ""),
                dhcp_enabled=lan.get("dhcp_enabled", False),
                dhcp_range_start=lan.get("dhcp_range_start"),
                dhcp_range_end=lan.get("dhcp_range_end"),
            )
            for lan in lan_list
        ]
    
    def _parse_health_check(self) -> HealthCheckConfig:
        """Parse health check configuration"""
        hc = self._raw_config.get("health_check", {})
        return HealthCheckConfig(
            enabled=hc.get("enabled", True),
            interval=hc.get("interval", 5),
            timeout=hc.get("timeout", 3),
            failure_threshold=hc.get("failure_threshold", 3),
            recovery_threshold=hc.get("recovery_threshold", 2),
            ping_targets=hc.get("ping_targets", ["8.8.8.8", "1.1.1.1"]),
        )
    
    def _parse_traffic(self) -> TrafficConfig:
        """Parse traffic configuration"""
        traffic = self._raw_config.get("traffic", {})
        return TrafficConfig(
            mode=traffic.get("mode", "round_robin"),
            packet_reordering=traffic.get("packet_reordering", True),
            reorder_buffer_size=traffic.get("reorder_buffer_size", 1000),
            failover_enabled=traffic.get("failover_enabled", True),
            failover_delay=traffic.get("failover_delay", 2),
        )
    
    def _parse_tunnel(self) -> TunnelConfig:
        """Parse tunnel configuration"""
        tunnel = self._raw_config.get("tunnel", {})
        return TunnelConfig(
            protocol=tunnel.get("protocol", "udp"),
            mtu=tunnel.get("mtu", 1400),
            encryption=tunnel.get("encryption", True),
            compression=tunnel.get("compression", False),
            send_buffer_size=tunnel.get("send_buffer_size", 2097152),
            recv_buffer_size=tunnel.get("recv_buffer_size", 2097152),
        )
    
    def _parse_logging(self) -> LoggingConfig:
        """Parse logging configuration"""
        logging = self._raw_config.get("logging", {})
        return LoggingConfig(
            level=logging.get("level", "INFO"),
            file=logging.get("file", "/var/log/bondlink/client.log"),
            max_size_mb=logging.get("max_size_mb", 100),
            backup_count=logging.get("backup_count", 5),
            console=logging.get("console", True),
            format=logging.get("format", "json"),
        )
    
    def _parse_monitoring(self) -> MonitoringConfig:
        """Parse monitoring configuration"""
        monitoring = self._raw_config.get("monitoring", {})
        return MonitoringConfig(
            prometheus_enabled=monitoring.get("prometheus_enabled", True),
            prometheus_port=monitoring.get("prometheus_port", 9090),
            stats_interval=monitoring.get("stats_interval", 10),
        )
    
    def _parse_system(self) -> SystemConfig:
        """Parse system configuration"""
        system = self._raw_config.get("system", {})
        return SystemConfig(
            run_as_user=system.get("run_as_user", "root"),
            pid_file=system.get("pid_file", "/var/run/bondlink/client.pid"),
            enable_forwarding=system.get("enable_forwarding", True),
            enable_masquerading=system.get("enable_masquerading", True),
        )
    
    def validate(self) -> List[str]:
        """Validate configuration
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Validate server config
        if not self.server.host:
            errors.append("server.host is required")
        if not self.server.auth_token or self.server.auth_token == "CHANGE_ME_GENERATE_SECURE_TOKEN":
            errors.append("server.auth_token must be set to a secure value")
            
        # Validate WAN interfaces
        if not self.wan_interfaces:
            errors.append("At least one WAN interface is required")
        for wan in self.wan_interfaces:
            if not wan.interface:
                errors.append(f"WAN interface {wan.name} is missing interface name")
                
        # Validate LAN interfaces
        if not self.lan_interfaces:
            errors.append("At least one LAN interface is required")
        for lan in self.lan_interfaces:
            if not lan.interface:
                errors.append(f"LAN interface {lan.name} is missing interface name")
            if not lan.ip:
                errors.append(f"LAN interface {lan.name} is missing IP address")
                
        return errors
    
    def get_enabled_wan_interfaces(self) -> List[WANInterfaceConfig]:
        """Get list of enabled WAN interfaces
        
        Returns:
            List of enabled WAN interface configurations
        """
        return [wan for wan in self.wan_interfaces if wan.enabled]
