// Bondlink Dashboard - Real-time Data Visualization

class BondlinkDashboard {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 3000;
        
        // Data history for graphs
        this.uploadHistory = [];
        this.downloadHistory = [];
        this.maxHistoryPoints = 60;
        
        // Chart contexts
        this.uploadChart = null;
        this.downloadChart = null;
        
        this.init();
    }
    
    init() {
        this.setupWebSocket();
        this.fetchInitialData();
        this.setupCharts();
        
        // Refresh data every 2 seconds as fallback
        setInterval(() => this.fetchStatus(), 2000);
    }
    
    setupWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this.updateSystemStatus(true);
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'update') {
                this.handleRealtimeUpdate(data);
            }
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.updateSystemStatus(false);
            this.reconnectWebSocket();
        };
    }
    
    reconnectWebSocket() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`);
            setTimeout(() => this.setupWebSocket(), this.reconnectDelay);
        }
    }
    
    async fetchInitialData() {
        await Promise.all([
            this.fetchStatus(),
            this.fetchInterfaces()
        ]);
    }
    
    async fetchStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            this.updateTotalBandwidth(data.total_bandwidth);
            this.updateStats(data.wan_interfaces);
        } catch (error) {
            console.error('Error fetching status:', error);
        }
    }
    
    async fetchInterfaces() {
        try {
            const response = await fetch('/api/interfaces');
            const data = await response.json();
            this.renderInterfaces(data.interfaces);
        } catch (error) {
            console.error('Error fetching interfaces:', error);
        }
    }
    
    handleRealtimeUpdate(data) {
        // Update total bandwidth
        if (data.total_bandwidth) {
            this.updateTotalBandwidth(data.total_bandwidth);
        }
        
        // Update interfaces
        if (data.interfaces) {
            this.updateInterfaceStats(data.interfaces);
        }
    }
    
    updateSystemStatus(connected) {
        const statusBadge = document.getElementById('systemStatus');
        if (connected) {
            statusBadge.innerHTML = '<span class="status-dot"></span><span>Connected</span>';
            statusBadge.style.background = 'rgba(16, 185, 129, 0.1)';
            statusBadge.style.borderColor = 'rgba(16, 185, 129, 0.3)';
            statusBadge.style.color = '#10b981';
        } else {
            statusBadge.innerHTML = '<span class="status-dot"></span><span>Disconnected</span>';
            statusBadge.style.background = 'rgba(239, 68, 68, 0.1)';
            statusBadge.style.borderColor = 'rgba(239, 68, 68, 0.3)';
            statusBadge.style.color = '#ef4444';
        }
    }
    
    updateTotalBandwidth(bandwidth) {
        const uploadMbps = bandwidth.upload_mbps.toFixed(2);
        const downloadMbps = bandwidth.download_mbps.toFixed(2);
        
        document.getElementById('totalUpload').textContent = uploadMbps;
        document.getElementById('totalDownload').textContent = downloadMbps;
        
        // Update graph history
        this.uploadHistory.push(parseFloat(uploadMbps));
        this.downloadHistory.push(parseFloat(downloadMbps));
        
        if (this.uploadHistory.length > this.maxHistoryPoints) {
            this.uploadHistory.shift();
            this.downloadHistory.shift();
        }
        
        this.updateCharts();
    }
    
    updateStats(wanInterfaces) {
        document.getElementById('activeLinks').textContent = wanInterfaces.total;
        document.getElementById('healthyInterfaces').textContent = wanInterfaces.healthy;
    }
    
    setupCharts() {
        const uploadCanvas = document.getElementById('uploadGraph');
        const downloadCanvas = document.getElementById('downloadGraph');
        
        this.uploadChart = uploadCanvas.getContext('2d');
        this.downloadChart = downloadCanvas.getContext('2d');
    }
    
    updateCharts() {
        this.drawChart(this.uploadChart, this.uploadHistory, '#f59e0b', '#ef4444');
        this.drawChart(this.downloadChart, this.downloadHistory, '#10b981', '#3b82f6');
    }
    
    drawChart(ctx, data, colorStart, colorEnd) {
        const canvas = ctx.canvas;
        const width = canvas.width;
        const height = canvas.height;
        
        // Clear canvas
        ctx.clearRect(0, 0, width, height);
        
        if (data.length < 2) return;
        
        // Calculate scale
        const maxValue = Math.max(...data, 1);
        const xStep = width / (this.maxHistoryPoints - 1);
        
        // Create gradient
        const gradient = ctx.createLinearGradient(0, 0, 0, height);
        gradient.addColorStop(0, colorStart + '40');
        gradient.addColorStop(1, colorEnd + '10');
        
        // Draw area
        ctx.beginPath();
        ctx.moveTo(0, height);
        
        data.forEach((value, index) => {
            const x = index * xStep;
            const y = height - (value / maxValue) * height;
            ctx.lineTo(x, y);
        });
        
        ctx.lineTo(width, height);
        ctx.closePath();
        ctx.fillStyle = gradient;
        ctx.fill();
        
        // Draw line
        ctx.beginPath();
        data.forEach((value, index) => {
            const x = index * xStep;
            const y = height - (value / maxValue) * height;
            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        
        ctx.strokeStyle = colorStart;
        ctx.lineWidth = 2;
        ctx.stroke();
    }
    
    renderInterfaces(interfaces) {
        const grid = document.getElementById('interfacesGrid');
        grid.innerHTML = '';
        
        let totalPacketsSent = 0;
        let totalPacketsRecv = 0;
        
        interfaces.forEach(iface => {
            totalPacketsSent += iface.stats.packets_sent;
            totalPacketsRecv += iface.stats.packets_recv;
            
            const card = this.createInterfaceCard(iface);
            grid.appendChild(card);
        });
        
        document.getElementById('totalPacketsSent').textContent = this.formatNumber(totalPacketsSent);
        document.getElementById('totalPacketsRecv').textContent = this.formatNumber(totalPacketsRecv);
    }
    
    createInterfaceCard(iface) {
        const card = document.createElement('div');
        card.className = `interface-card status-${iface.status}`;
        card.id = `interface-${iface.name}`;
        
        const statusClass = iface.health.is_healthy ? 'good' : 'bad';
        const latencyClass = iface.health.latency_ms < 50 ? 'good' : 
                            iface.health.latency_ms < 100 ? 'warning' : 'bad';
        
        card.innerHTML = `
            <div class="interface-header">
                <div class="interface-name">${iface.name}</div>
                <label class="interface-toggle">
                    <input type="checkbox" ${iface.enabled ? 'checked' : ''} 
                           onchange="dashboard.toggleInterface('${iface.name}', this.checked)">
                    <span class="toggle-slider"></span>
                </label>
            </div>
            
            <div class="interface-status ${iface.status}">
                <span>●</span> ${iface.status.toUpperCase()}
                ${iface.tunnel_connected ? ' • Tunnel Active' : ''}
            </div>
            
            <div class="interface-stats">
                <div class="stat-row">
                    <span class="stat-label">Interface</span>
                    <span class="stat-value">${iface.interface}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">IP Address</span>
                    <span class="stat-value">${iface.ip_address || 'N/A'}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Upload</span>
                    <span class="stat-value">${iface.stats.send_rate_mbps.toFixed(2)} Mbps</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Download</span>
                    <span class="stat-value">${iface.stats.recv_rate_mbps.toFixed(2)} Mbps</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Latency</span>
                    <span class="stat-value ${latencyClass}">${iface.health.latency_ms.toFixed(0)} ms</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Packet Loss</span>
                    <span class="stat-value ${statusClass}">${iface.health.packet_loss.toFixed(1)}%</span>
                </div>
            </div>
        `;
        
        return card;
    }
    
    updateInterfaceStats(interfaces) {
        interfaces.forEach(iface => {
            const card = document.getElementById(`interface-${iface.name}`);
            if (!card) return;
            
            // Update status class
            card.className = `interface-card status-${iface.status}`;
            
            // Update stats values
            const stats = card.querySelector('.interface-stats');
            const statValues = stats.querySelectorAll('.stat-value');
            
            statValues[1].textContent = `${iface.send_rate_mbps} Mbps`;
            statValues[2].textContent = `${iface.recv_rate_mbps} Mbps`;
            statValues[3].textContent = `${iface.latency_ms} ms`;
            statValues[3].className = `stat-value ${iface.latency_ms < 50 ? 'good' : iface.latency_ms < 100 ? 'warning' : 'bad'}`;
            statValues[4].textContent = `${iface.packet_loss}%`;
            statValues[4].className = `stat-value ${iface.is_healthy ? 'good' : 'bad'}`;
            
            // Update status badge
            const statusBadge = card.querySelector('.interface-status');
            statusBadge.className = `interface-status ${iface.status}`;
            statusBadge.innerHTML = `<span>●</span> ${iface.status.toUpperCase()} ${iface.tunnel_connected ? ' • Tunnel Active' : ''}`;
        });
    }
    
    async toggleInterface(name, enabled) {
        try {
            const endpoint = enabled ? 'enable' : 'disable';
            const response = await fetch(`/api/interfaces/${name}/${endpoint}`, {
                method: 'POST'
            });
            
            if (response.ok) {
                console.log(`Interface ${name} ${enabled ? 'enabled' : 'disabled'}`);
                // Refresh interface data
                await this.fetchInterfaces();
            } else {
                console.error(`Failed to ${endpoint} interface ${name}`);
                // Revert toggle
                const checkbox = document.querySelector(`#interface-${name} input[type="checkbox"]`);
                if (checkbox) checkbox.checked = !enabled;
            }
        } catch (error) {
            console.error('Error toggling interface:', error);
        }
    }
    
    formatNumber(num) {
        if (num >= 1000000000) return (num / 1000000000).toFixed(2) + 'B';
        if (num >= 1000000) return (num / 1000000).toFixed(2) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(2) + 'K';
        return num.toString();
    }
}

// Initialize dashboard
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new BondlinkDashboard();
});
