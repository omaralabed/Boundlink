"""Unit tests for WAN interface manager"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock

from client.core.config import WANInterfaceConfig, HealthCheckConfig
from client.network.wan_manager import WANInterfaceManager, InterfaceStatus


@pytest.fixture
def wan_configs():
    """Create test WAN configurations"""
    return [
        WANInterfaceConfig(
            name="wan1",
            interface="eth0",
            priority=1,
            weight=1.0,
            enabled=True
        ),
        WANInterfaceConfig(
            name="wan2",
            interface="eth1",
            priority=2,
            weight=1.0,
            enabled=True
        )
    ]


@pytest.fixture
def health_config():
    """Create test health check configuration"""
    return HealthCheckConfig(
        enabled=True,
        interval=5,
        timeout=3,
        failure_threshold=3,
        recovery_threshold=2,
        ping_targets=["8.8.8.8"]
    )


@pytest.fixture
def wan_manager(wan_configs, health_config):
    """Create WAN interface manager instance"""
    return WANInterfaceManager(wan_configs, health_config)


def test_wan_manager_initialization(wan_manager):
    """Test WAN manager initializes correctly"""
    assert len(wan_manager.interfaces) == 2
    assert "wan1" in wan_manager.interfaces
    assert "wan2" in wan_manager.interfaces
    assert wan_manager.interfaces["wan1"].config.interface == "eth0"


def test_get_interface(wan_manager):
    """Test getting individual interface"""
    wan = wan_manager.get_interface("wan1")
    assert wan is not None
    assert wan.config.name == "wan1"
    
    wan = wan_manager.get_interface("nonexistent")
    assert wan is None


def test_get_all_interfaces(wan_manager):
    """Test getting all interfaces"""
    interfaces = wan_manager.get_all_interfaces()
    assert len(interfaces) == 2
    assert "wan1" in interfaces
    assert "wan2" in interfaces


@pytest.mark.asyncio
async def test_enable_disable_interface(wan_manager):
    """Test enabling and disabling interfaces"""
    # Disable interface
    success = await wan_manager.disable_interface("wan1")
    assert success is True
    assert wan_manager.interfaces["wan1"].enabled is False
    
    # Enable interface
    success = await wan_manager.enable_interface("wan1")
    assert success is True
    assert wan_manager.interfaces["wan1"].enabled is True
    
    # Test nonexistent interface
    success = await wan_manager.disable_interface("nonexistent")
    assert success is False


def test_get_healthy_interfaces(wan_manager):
    """Test getting healthy interfaces"""
    # Mark wan1 as healthy and up
    wan_manager.interfaces["wan1"].status = InterfaceStatus.UP
    wan_manager.interfaces["wan1"].health.is_healthy = True
    wan_manager.interfaces["wan1"].enabled = True
    
    # Mark wan2 as down
    wan_manager.interfaces["wan2"].status = InterfaceStatus.DOWN
    
    healthy = wan_manager.get_healthy_interfaces()
    assert len(healthy) == 1
    assert healthy[0].config.name == "wan1"


def test_get_total_bandwidth(wan_manager):
    """Test total bandwidth calculation"""
    # Set bandwidth for both interfaces
    wan_manager.interfaces["wan1"].stats.send_rate = 1000000  # 1 MB/s
    wan_manager.interfaces["wan1"].stats.recv_rate = 2000000  # 2 MB/s
    wan_manager.interfaces["wan1"].status = InterfaceStatus.UP
    wan_manager.interfaces["wan1"].health.is_healthy = True
    
    wan_manager.interfaces["wan2"].stats.send_rate = 500000  # 0.5 MB/s
    wan_manager.interfaces["wan2"].stats.recv_rate = 1000000  # 1 MB/s
    wan_manager.interfaces["wan2"].status = InterfaceStatus.UP
    wan_manager.interfaces["wan2"].health.is_healthy = True
    
    send_rate, recv_rate = wan_manager.get_total_bandwidth()
    assert send_rate == 1500000  # 1.5 MB/s
    assert recv_rate == 3000000  # 3 MB/s


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
