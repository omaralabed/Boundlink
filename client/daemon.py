"""Main daemon for Bondlink client"""

import asyncio
import sys
import signal
from pathlib import Path

from client.core.config import Config
from client.core.logger import setup_logging, get_logger
from client.network.wan_manager import WANInterfaceManager
from client.network.tunnel_manager import TunnelManager
from client.api.server import BondlinkAPI

logger = None


class BondlinkDaemon:
    """Main Bondlink client daemon"""
    
    def __init__(self, config_path: str = None):
        """Initialize daemon
        
        Args:
            config_path: Path to configuration file
        """
        self.config = Config(config_path)
        self.wan_manager = None
        self.tunnel_manager = None
        self.api_server = None
        self._shutdown_event = asyncio.Event()
    
    async def start(self):
        """Start all services"""
        global logger
        
        # Setup logging
        logger = setup_logging(self.config.logging)
        logger.info("bondlink_daemon_starting", version="1.0.0")
        
        # Validate configuration
        errors = self.config.validate()
        if errors:
            logger.error("configuration_validation_failed", errors=errors)
            for error in errors:
                print(f"Configuration error: {error}", file=sys.stderr)
            sys.exit(1)
        
        logger.info("configuration_loaded", config_path=str(self.config.config_path))
        
        # Setup system (IP forwarding, etc.)
        await self._setup_system()
        
        # Initialize WAN manager
        self.wan_manager = WANInterfaceManager(
            self.config.wan_interfaces,
            self.config.health_check
        )
        
        # Initialize tunnel manager
        self.tunnel_manager = TunnelManager(
            self.config.server,
            self.config.tunnel,
            self.wan_manager.get_all_interfaces()
        )
        
        # Initialize API server
        self.api_server = BondlinkAPI(
            self.wan_manager,
            host="0.0.0.0",
            port=80
        )
        
        # Start services
        logger.info("starting_services")
        
        await self.wan_manager.start()
        logger.info("wan_manager_started")
        
        await self.tunnel_manager.start()
        logger.info("tunnel_manager_started")
        
        # Start API server in background
        api_task = asyncio.create_task(self.api_server.start())
        logger.info("api_server_started")
        
        logger.info("bondlink_daemon_started")
        print("✓ Bondlink client started successfully")
        print(f"✓ Web UI available at: http://localhost")
        print(f"✓ Monitoring {len(self.config.wan_interfaces)} WAN interfaces")
        print(f"✓ Press Ctrl+C to stop")
        
        # Wait for shutdown signal
        await self._shutdown_event.wait()
        
        # Stop services
        await self.stop()
    
    async def stop(self):
        """Stop all services"""
        logger.info("bondlink_daemon_stopping")
        
        if self.tunnel_manager:
            await self.tunnel_manager.stop()
            logger.info("tunnel_manager_stopped")
        
        if self.wan_manager:
            await self.wan_manager.stop()
            logger.info("wan_manager_stopped")
        
        # API server stops when main loop exits
        
        logger.info("bondlink_daemon_stopped")
        print("\n✓ Bondlink client stopped")
    
    async def _setup_system(self):
        """Setup system networking (IP forwarding, NAT, etc.)"""
        if not self.config.system.enable_forwarding:
            return
        
        logger.info("setting_up_system_networking")
        
        try:
            # Enable IP forwarding
            import subprocess
            
            # IPv4 forwarding
            result = await asyncio.create_subprocess_exec(
                "sysctl", "-w", "net.ipv4.ip_forward=1",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            
            if result.returncode == 0:
                logger.info("ipv4_forwarding_enabled")
            else:
                logger.warning("ipv4_forwarding_failed")
            
            # Setup NAT/Masquerading if enabled
            if self.config.system.enable_masquerading:
                await self._setup_nat()
            
        except Exception as e:
            logger.error("system_setup_error", error=str(e))
    
    async def _setup_nat(self):
        """Setup NAT/masquerading with iptables"""
        logger.info("setting_up_nat")
        
        try:
            # Flush existing NAT rules
            await self._run_command(["iptables", "-t", "nat", "-F"])
            
            # Add masquerading for each LAN interface
            for lan in self.config.lan_interfaces:
                # Masquerade traffic from LAN
                await self._run_command([
                    "iptables", "-t", "nat", "-A", "POSTROUTING",
                    "-s", f"{lan.ip}/{lan.netmask}",
                    "-j", "MASQUERADE"
                ])
            
            # Allow forwarding
            await self._run_command([
                "iptables", "-A", "FORWARD",
                "-j", "ACCEPT"
            ])
            
            logger.info("nat_setup_complete")
            
        except Exception as e:
            logger.error("nat_setup_error", error=str(e))
    
    async def _run_command(self, cmd: list):
        """Run system command
        
        Args:
            cmd: Command and arguments as list
        """
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.warning("command_failed", cmd=" ".join(cmd), 
                         stderr=stderr.decode() if stderr else "")
    
    def handle_signal(self, sig):
        """Handle shutdown signals
        
        Args:
            sig: Signal number
        """
        logger.info("received_signal", signal=sig)
        self._shutdown_event.set()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Bondlink Client Daemon")
    parser.add_argument(
        "-c", "--config",
        default=None,
        help="Path to configuration file"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version and exit"
    )
    
    args = parser.parse_args()
    
    if args.version:
        print("Bondlink Client v1.0.0")
        sys.exit(0)
    
    # Create daemon
    daemon = BondlinkDaemon(config_path=args.config)
    
    # Setup signal handlers
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig,
            lambda s=sig: daemon.handle_signal(s)
        )
    
    # Run daemon
    try:
        loop.run_until_complete(daemon.start())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


if __name__ == "__main__":
    main()
