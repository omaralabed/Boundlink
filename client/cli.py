"""CLI tool for Bondlink client"""

import click
import requests
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
import time

console = Console()

API_BASE = "http://localhost/api"


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Bondlink Client CLI - Manage your multi-WAN bonding router"""
    pass


@cli.command()
def status():
    """Show overall system status"""
    try:
        response = requests.get(f"{API_BASE}/status", timeout=5)
        response.raise_for_status()
        data = response.json()
        
        console.print("\n[bold cyan]Bondlink Client Status[/bold cyan]\n")
        
        table = Table(show_header=False, box=None)
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Status", data["status"].upper())
        table.add_row("Total WAN Interfaces", str(data["wan_interfaces"]["total"]))
        table.add_row("Healthy Interfaces", str(data["wan_interfaces"]["healthy"]))
        table.add_row("Degraded Interfaces", str(data["wan_interfaces"]["degraded"]))
        table.add_row("Down Interfaces", str(data["wan_interfaces"]["down"]))
        table.add_row("Upload Speed", f"{data['total_bandwidth']['upload_mbps']:.2f} Mbps")
        table.add_row("Download Speed", f"{data['total_bandwidth']['download_mbps']:.2f} Mbps")
        
        console.print(table)
        console.print()
        
    except requests.exceptions.ConnectionError:
        console.print("[red]Error: Cannot connect to Bondlink daemon. Is it running?[/red]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")


@cli.command()
def interfaces():
    """List all WAN interfaces"""
    try:
        response = requests.get(f"{API_BASE}/interfaces", timeout=5)
        response.raise_for_status()
        data = response.json()
        
        console.print("\n[bold cyan]WAN Interfaces[/bold cyan]\n")
        
        table = Table(show_header=True)
        table.add_column("Name", style="cyan")
        table.add_column("Interface", style="white")
        table.add_column("Status", style="white")
        table.add_column("Enabled", style="white")
        table.add_column("IP Address", style="white")
        table.add_column("Upload", style="green")
        table.add_column("Download", style="green")
        table.add_column("Latency", style="yellow")
        table.add_column("Health", style="white")
        
        for iface in data["interfaces"]:
            status_color = "green" if iface["status"] == "up" else "red" if iface["status"] == "down" else "yellow"
            enabled = "✓" if iface["enabled"] else "✗"
            health = "✓" if iface["health"]["is_healthy"] else "✗"
            
            table.add_row(
                iface["name"],
                iface["interface"],
                f"[{status_color}]{iface['status'].upper()}[/{status_color}]",
                f"[{'green' if iface['enabled'] else 'red'}]{enabled}[/{'green' if iface['enabled'] else 'red'}]",
                iface["ip_address"] or "N/A",
                f"{iface['stats']['send_rate_mbps']:.2f} Mbps",
                f"{iface['stats']['recv_rate_mbps']:.2f} Mbps",
                f"{iface['health']['latency_ms']:.0f} ms",
                f"[{'green' if iface['health']['is_healthy'] else 'red'}]{health}[/{'green' if iface['health']['is_healthy'] else 'red'}]"
            )
        
        console.print(table)
        console.print()
        
    except requests.exceptions.ConnectionError:
        console.print("[red]Error: Cannot connect to Bondlink daemon. Is it running?[/red]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")


@cli.command()
@click.argument('interface_name')
def enable(interface_name):
    """Enable a WAN interface"""
    try:
        response = requests.post(f"{API_BASE}/interfaces/{interface_name}/enable", timeout=5)
        response.raise_for_status()
        console.print(f"[green]✓ Interface '{interface_name}' enabled[/green]")
    except requests.exceptions.ConnectionError:
        console.print("[red]Error: Cannot connect to Bondlink daemon. Is it running?[/red]")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            console.print(f"[red]Error: Interface '{interface_name}' not found[/red]")
        else:
            console.print(f"[red]Error: {str(e)}[/red]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")


@cli.command()
@click.argument('interface_name')
def disable(interface_name):
    """Disable a WAN interface"""
    try:
        response = requests.post(f"{API_BASE}/interfaces/{interface_name}/disable", timeout=5)
        response.raise_for_status()
        console.print(f"[yellow]✓ Interface '{interface_name}' disabled[/yellow]")
    except requests.exceptions.ConnectionError:
        console.print("[red]Error: Cannot connect to Bondlink daemon. Is it running?[/red]")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            console.print(f"[red]Error: Interface '{interface_name}' not found[/red]")
        else:
            console.print(f"[red]Error: {str(e)}[/red]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")


@cli.command()
@click.option('--interval', '-i', default=1, help='Update interval in seconds')
def monitor(interval):
    """Real-time monitoring dashboard"""
    try:
        with Live(console=console, refresh_per_second=1) as live:
            while True:
                try:
                    response = requests.get(f"{API_BASE}/interfaces", timeout=5)
                    response.raise_for_status()
                    data = response.json()
                    
                    # Get status
                    status_response = requests.get(f"{API_BASE}/status", timeout=5)
                    status_data = status_response.json()
                    
                    # Create dashboard
                    layout = Layout()
                    layout.split_column(
                        Layout(name="header", size=3),
                        Layout(name="body")
                    )
                    
                    # Header
                    header_text = Text()
                    header_text.append("Bondlink Client Monitor", style="bold cyan")
                    header_text.append(f" | Upload: {status_data['total_bandwidth']['upload_mbps']:.2f} Mbps", style="green")
                    header_text.append(f" | Download: {status_data['total_bandwidth']['download_mbps']:.2f} Mbps", style="green")
                    layout["header"].update(Panel(header_text))
                    
                    # Body - interfaces table
                    table = Table(show_header=True)
                    table.add_column("Name", style="cyan")
                    table.add_column("Status", style="white")
                    table.add_column("Upload", style="green")
                    table.add_column("Download", style="green")
                    table.add_column("Latency", style="yellow")
                    table.add_column("Loss", style="white")
                    
                    for iface in data["interfaces"]:
                        status_color = "green" if iface["status"] == "up" else "red" if iface["status"] == "down" else "yellow"
                        
                        table.add_row(
                            iface["name"],
                            f"[{status_color}]●[/{status_color}] {iface['status'].upper()}",
                            f"{iface['stats']['send_rate_mbps']:.2f} Mbps",
                            f"{iface['stats']['recv_rate_mbps']:.2f} Mbps",
                            f"{iface['health']['latency_ms']:.0f} ms",
                            f"{iface['health']['packet_loss']:.1f}%"
                        )
                    
                    layout["body"].update(table)
                    live.update(layout)
                    
                    time.sleep(interval)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    console.print(f"[red]Error: {str(e)}[/red]")
                    time.sleep(interval)
                    
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped[/yellow]")


def main():
    """Main entry point"""
    cli()


if __name__ == "__main__":
    main()
