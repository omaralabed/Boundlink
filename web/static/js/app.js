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
            statusBadge.className = 'status-badge connected';
            statusBadge.innerHTML = '<span class="status-dot"></span><span class="status-text">Connected</span>';
        } else {
            statusBadge.className = 'status-badge disconnected';
            statusBadge.innerHTML = '<span class="status-dot"></span><span class="status-text">Disconnected</span>';
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
        document.getElementById('healthyInterfaces').textContent = `${wanInterfaces.healthy} / ${wanInterfaces.total}`;
    }
    
    setupCharts() {
        const uploadCanvas = document.getElementById('uploadGraph');
        const downloadCanvas = document.getElementById('downloadGraph');
        
        this.uploadChart = uploadCanvas.getContext('2d');
        this.downloadChart = downloadCanvas.getContext('2d');
    }
    
    updateCharts() {
        this.drawChart(this.uploadChart, this.uploadHistory, '#7AC943', '#68B336');
        this.drawChart(this.downloadChart, this.downloadHistory, '#FF6B35', '#E85A2B');
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
        gradient.addColorStop(0, colorStart + '60');
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
        ctx.lineWidth = 2.5;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
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
        document.getElementById('totalPackets').textContent = this.formatNumber(totalPacketsSent + totalPacketsRecv);
    }
    
    createInterfaceCard(iface) {
        const card = document.createElement('div');
        card.className = `interface-card ${iface.enabled ? 'active' : ''}`;
        card.id = `interface-${iface.name}`;
        
        const healthStatus = iface.health.is_healthy ? 'healthy' : 
                           iface.health.packet_loss > 10 ? 'down' : 'degraded';
        
        card.innerHTML = `
            <div class="interface-header">
                <div class="interface-title-section">
                    <div class="interface-icon">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                            <rect x="2" y="5" width="20" height="14" rx="2" stroke-width="2.5"/>
                            <line x1="8" y1="2" x2="8" y2="5" stroke-width="2.5"/>
                            <line x1="16" y1="2" x2="16" y2="5" stroke-width="2.5"/>
                            <circle cx="7" cy="10" r="1" fill="currentColor"/>
                            <circle cx="12" cy="10" r="1" fill="currentColor"/>
                            <circle cx="17" cy="10" r="1" fill="currentColor"/>
                        </svg>
                    </div>
                    <div class="interface-title-info">
                        <h3>${iface.name}</h3>
                        <div class="interface-subtitle">${iface.interface}</div>
                    </div>
                </div>
                <label class="toggle-switch">
                    <input type="checkbox" ${iface.enabled ? 'checked' : ''} 
                           onchange="dashboard.toggleInterface('${iface.name}', this.checked)">
                    <span class="toggle-slider"></span>
                </label>
            </div>
            
            <div class="interface-body">
                <div class="interface-info-row">
                    <span class="info-label">Status</span>
                    <span class="health-status ${healthStatus}">
                        <span class="health-dot"></span>
                        ${healthStatus.toUpperCase()}
                    </span>
                </div>
                <div class="interface-info-row">
                    <span class="info-label">IP Address</span>
                    <span class="info-value">${iface.ip_address || 'N/A'}</span>
                </div>
                <div class="interface-info-row">
                    <span class="info-label">Latency</span>
                    <span class="info-value">${iface.health.latency_ms.toFixed(0)} ms</span>
                </div>
                <div class="interface-info-row">
                    <span class="info-label">Packet Loss</span>
                    <span class="info-value">${iface.health.packet_loss.toFixed(1)}%</span>
                </div>
            </div>
            
            <div class="speed-chart-container">
                <div class="speed-label">Real-time Speed</div>
                <div class="speed-values">
                    <div class="speed-item">
                        <div class="speed-item-label">Upload</div>
                        <div class="speed-item-value upload" id="${iface.name}-upload">${iface.stats.send_rate_mbps.toFixed(2)} Mbps</div>
                    </div>
                    <div class="speed-item">
                        <div class="speed-item-label">Download</div>
                        <div class="speed-item-value download" id="${iface.name}-download">${iface.stats.recv_rate_mbps.toFixed(2)} Mbps</div>
                    </div>
                </div>
                <canvas id="chart-${iface.name}" width="300" height="80"></canvas>
            </div>
        `;
        
        return card;
    }
    
    updateInterfaceStats(interfaces) {
        interfaces.forEach(iface => {
            const card = document.getElementById(`interface-${iface.name}`);
            if (!card) return;
            
            // Update card active state
            if (iface.enabled) {
                card.classList.add('active');
            } else {
                card.classList.remove('active');
            }
            
            // Update health status
            const healthStatus = iface.health.is_healthy ? 'healthy' : 
                               iface.health.packet_loss > 10 ? 'down' : 'degraded';
            const healthBadge = card.querySelector('.health-status');
            if (healthBadge) {
                healthBadge.className = `health-status ${healthStatus}`;
                healthBadge.innerHTML = `<span class="health-dot"></span>${healthStatus.toUpperCase()}`;
            }
            
            // Update speed values
            const uploadElem = document.getElementById(`${iface.name}-upload`);
            const downloadElem = document.getElementById(`${iface.name}-download`);
            if (uploadElem) uploadElem.textContent = `${iface.stats.send_rate_mbps.toFixed(2)} Mbps`;
            if (downloadElem) downloadElem.textContent = `${iface.stats.recv_rate_mbps.toFixed(2)} Mbps`;
            
            // Update latency and packet loss
            const infoValues = card.querySelectorAll('.info-value');
            if (infoValues.length >= 3) {
                infoValues[1].textContent = `${iface.health.latency_ms.toFixed(0)} ms`;
                infoValues[2].textContent = `${iface.health.packet_loss.toFixed(1)}%`;
            }
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
