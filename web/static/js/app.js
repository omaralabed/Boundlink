// Bondlink Dashboard - Real-time Data Visualization

class BondlinkDashboard {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 3000;

        // Data history for global graphs
        this.uploadHistory = [];
        this.downloadHistory = [];
        this.maxHistoryPoints = 60;

        // Per-interface chart histories  { ifaceName: { upload: [], download: [] } }
        this.ifaceHistories = {};

        // Chart canvas contexts (set after DOM ready)
        this.uploadChart = null;
        this.downloadChart = null;

        // Polling interval handle
        this._pollInterval = null;
    }

    init() {
        // Prevent double-init (e.g. if called twice by accident)
        if (this._pollInterval) return;

        // setupCharts needs the canvas elements — called here, after DOM is ready
        this.setupCharts();
        this.setupWebSocket();
        this.fetchInitialData();

        // Poll every 2 seconds as fallback — only one interval, started once
        this._pollInterval = setInterval(() => this.fetchStatus(), 2000);
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
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'update') {
                    this.handleRealtimeUpdate(data);
                }
            } catch (e) {
                console.warn('Received non-JSON WebSocket message:', event.data);
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
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.warn('Max reconnect attempts reached. Will retry in 60 s.');
            // Reset so the next scheduled retry can proceed — prevents permanent lockout
            setTimeout(() => {
                this.reconnectAttempts = 0;
                this.setupWebSocket();
            }, 60000);
            return;
        }
        this.reconnectAttempts++;
        const delay = Math.min(this.reconnectDelay * this.reconnectAttempts, 30000);
        console.log(`Reconnecting in ${delay}ms... (attempt ${this.reconnectAttempts})`);
        setTimeout(() => this.setupWebSocket(), delay);
    }
    
    async fetchInitialData() {
        // Run both in parallel — fetchStatus does NOT overlap with the poll
        // interval because the interval hasn't fired yet at this point
        await Promise.all([
            this.fetchStatus(),
            this.fetchInterfaces()
        ]);
    }

    async fetchStatus() {
        try {
            const response = await fetch('/api/status');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            if (data.total_bandwidth) this.updateTotalBandwidth(data.total_bandwidth);
            if (data.wan_interfaces)  this.updateStats(data.wan_interfaces);
        } catch (error) {
            console.error('Error fetching status:', error);
        }
    }

    async fetchInterfaces() {
        try {
            const response = await fetch('/api/interfaces');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            // Guard: API may return an object without the interfaces key
            if (Array.isArray(data.interfaces)) this.renderInterfaces(data.interfaces);
        } catch (error) {
            console.error('Error fetching interfaces:', error);
        }
    }
    
    handleRealtimeUpdate(data) {
        if (data.total_bandwidth) this.updateTotalBandwidth(data.total_bandwidth);
        // Re-use renderInterfaces which now does incremental updates
        if (data.interfaces)  this.renderInterfaces(data.interfaces);
    }
    
    updateSystemStatus(connected) {
        const statusBadge = document.getElementById('systemStatus');
        if (!statusBadge) return;   // guard: element may not exist on every page
        if (connected) {
            statusBadge.className = 'status-badge connected';
            statusBadge.innerHTML = '<span class="status-dot"></span><span class="status-text">Connected</span>';
        } else {
            statusBadge.className = 'status-badge disconnected';
            statusBadge.innerHTML = '<span class="status-dot"></span><span class="status-text">Disconnected</span>';
        }
    }
    
    updateTotalBandwidth(bandwidth) {
        const uploadMbps   = (bandwidth.upload_mbps   ?? 0).toFixed(2);
        const downloadMbps = (bandwidth.download_mbps ?? 0).toFixed(2);
        
        const upEl   = document.getElementById('totalUpload');
        const downEl = document.getElementById('totalDownload');
        if (upEl)   upEl.textContent   = uploadMbps;
        if (downEl) downEl.textContent = downloadMbps;
        
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
        const activeEl   = document.getElementById('activeLinks');
        const healthyEl  = document.getElementById('healthyInterfaces');
        if (activeEl)  activeEl.textContent  = wanInterfaces.total;
        if (healthyEl) healthyEl.textContent = `${wanInterfaces.healthy} / ${wanInterfaces.total}`;
    }
    
    setupCharts() {
        const uploadCanvas   = document.getElementById('uploadGraph');
        const downloadCanvas = document.getElementById('downloadGraph');
        
        if (uploadCanvas)   this.uploadChart   = uploadCanvas.getContext('2d');
        if (downloadCanvas) this.downloadChart = downloadCanvas.getContext('2d');
    }
    
    updateCharts() {
        if (this.uploadChart)   this.drawChart(this.uploadChart,   this.uploadHistory,   '#7AC943', '#68B336');
        if (this.downloadChart) this.drawChart(this.downloadChart, this.downloadHistory, '#FF6B35', '#E85A2B');
    }

    // Two-color area chart for the global bandwidth cards
    drawChart(ctx, data, colorStart, colorEnd) {
        const canvas = ctx.canvas;
        const width  = canvas.width;
        const height = canvas.height;

        ctx.clearRect(0, 0, width, height);
        if (data.length < 2) return;

        const maxValue = Math.max(...data, 1);
        // Use actual data length so the line always fills the canvas,
        // even when the buffer hasn't reached maxHistoryPoints yet.
        const xStep    = width / Math.max(data.length - 1, 1);

        const gradient = ctx.createLinearGradient(0, 0, 0, height);
        gradient.addColorStop(0, colorStart + '60');
        gradient.addColorStop(1, colorEnd   + '10');

        // Filled area
        ctx.beginPath();
        ctx.moveTo(0, height);
        data.forEach((value, i) => {
            ctx.lineTo(i * xStep, height - (value / maxValue) * height);
        });
        ctx.lineTo((data.length - 1) * xStep, height);
        ctx.closePath();
        ctx.fillStyle = gradient;
        ctx.fill();

        // Stroke line
        ctx.beginPath();
        data.forEach((value, i) => {
            const x = i * xStep;
            const y = height - (value / maxValue) * height;
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        });
        ctx.strokeStyle = colorStart;
        ctx.lineWidth   = 2.5;
        ctx.lineCap     = 'round';
        ctx.lineJoin    = 'round';
        ctx.stroke();
    }

    // Dual-line chart for per-interface cards (upload=green, download=orange)
    drawDualChart(ctx, uploadData, downloadData) {
        const canvas = ctx.canvas;
        const width  = canvas.width;
        const height = canvas.height;

        ctx.clearRect(0, 0, width, height);

        const combined = [...uploadData, ...downloadData];
        if (combined.length < 2) return;

        const maxValue = Math.max(...combined, 1);
        const pts      = Math.max(uploadData.length, downloadData.length);
        const xStep    = pts > 1 ? width / (pts - 1) : width;

        const drawLine = (data, color) => {
            if (data.length < 2) return;
            ctx.beginPath();
            data.forEach((v, i) => {
                const x = i * xStep;
                const y = height - (v / maxValue) * height;
                i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
            });
            ctx.strokeStyle = color;
            ctx.lineWidth   = 2;
            ctx.lineCap     = 'round';
            ctx.lineJoin    = 'round';
            ctx.stroke();
        };

        drawLine(uploadData,   '#7AC943');
        drawLine(downloadData, '#FF6B35');
    }
    
    renderInterfaces(interfaces) {
        const grid = document.getElementById('interfacesGrid');
        if (!grid) return;

        let totalPacketsSent = 0;
        let totalPacketsRecv = 0;

        const incomingNames = new Set(interfaces.map(iface => iface.name));

        // Remove cards for interfaces that are no longer reported by the server
        [...grid.querySelectorAll('[data-iface-name]')].forEach(card => {
            if (!incomingNames.has(card.dataset.ifaceName)) card.remove();
        });

        interfaces.forEach(iface => {
            totalPacketsSent += iface.stats.packets_sent;
            totalPacketsRecv += iface.stats.packets_recv;

            // Only create the card if it doesn't already exist — preserves
            // per-card canvas elements and their drawing contexts on each poll
            if (!document.getElementById(`interface-${iface.name}`)) {
                const card = this.createInterfaceCard(iface);
                grid.appendChild(card);
            } else {
                // Card already exists — just update the live values
                this.updateSingleInterfaceCard(iface);
            }
        });

        const sent = document.getElementById('totalPacketsSent');
        const recv = document.getElementById('totalPacketsRecv');
        const total = document.getElementById('totalPackets');
        if (sent)  sent.textContent  = this.formatNumber(totalPacketsSent);
        if (recv)  recv.textContent  = this.formatNumber(totalPacketsRecv);
        if (total) total.textContent = this.formatNumber(totalPacketsSent + totalPacketsRecv);
    }

    // Returns the canonical health string for an interface object
    _healthClass(iface) {
        if (iface.health.is_healthy)           return 'healthy';
        if (iface.health.packet_loss > 10)     return 'down';
        return 'degraded';
    }

    createInterfaceCard(iface) {
        const card = document.createElement('div');
        card.className = `interface-card ${iface.enabled ? 'active' : ''}`;
        card.id = `interface-${iface.name}`;
        card.dataset.ifaceName = iface.name;   // used by stale-card cleanup in renderInterfaces

        const healthStatus = this._healthClass(iface);
        // Escape name for safe use in HTML text content and in the onchange attribute
        const safeName = this._escapeHtml(iface.name);
        // Escape for insertion into a JS string attribute (the onchange handler)
        const safeNameJs = iface.name.replace(/\\/g, '\\\\').replace(/'/g, "\\'");

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
                        <h3>${safeName}</h3>
                        <div class="interface-subtitle">${this._escapeHtml(iface.interface)}</div>
                    </div>
                </div>
                <label class="toggle-switch">
                    <input type="checkbox" ${iface.enabled ? 'checked' : ''}
                           onchange="dashboard.toggleInterface('${safeNameJs}', this.checked)">
                    <span class="toggle-slider"></span>
                </label>
            </div>

            <div class="interface-body">
                <div class="interface-info-row">
                    <span class="info-label">Status</span>
                    <span class="health-status ${healthStatus}" id="${iface.name}-health">
                        <span class="health-dot"></span>
                        ${healthStatus.toUpperCase()}
                    </span>
                </div>
                <div class="interface-info-row">
                    <span class="info-label">IP Address</span>
                    <span class="info-value" id="${iface.name}-ip">${this._escapeHtml(iface.ip_address || 'N/A')}</span>
                </div>
                <div class="interface-info-row">
                    <span class="info-label">Latency</span>
                    <span class="info-value" id="${iface.name}-latency">${iface.health.latency_ms.toFixed(0)} ms</span>
                </div>
                <div class="interface-info-row">
                    <span class="info-label">Packet Loss</span>
                    <span class="info-value" id="${iface.name}-loss">${iface.health.packet_loss.toFixed(1)}%</span>
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

    // Simple HTML-escape helper (same trick as server's escapeHtml)
    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }

    updateSingleInterfaceCard(iface) {
        const card = document.getElementById(`interface-${iface.name}`);
        if (!card) return;

        // Active class
        card.classList.toggle('active', !!iface.enabled);

        // Health badge — use stable ID, not fragile nth-child
        const healthStatus = this._healthClass(iface);
        const healthBadge = document.getElementById(`${iface.name}-health`);
        if (healthBadge) {
            healthBadge.className = `health-status ${healthStatus}`;
            healthBadge.innerHTML = `<span class="health-dot"></span>${healthStatus.toUpperCase()}`;
        }

        // Stable-ID fields
        const ip      = document.getElementById(`${iface.name}-ip`);
        const latency = document.getElementById(`${iface.name}-latency`);
        const loss    = document.getElementById(`${iface.name}-loss`);
        const upload  = document.getElementById(`${iface.name}-upload`);
        const download = document.getElementById(`${iface.name}-download`);

        if (ip)       ip.textContent       = iface.ip_address || 'N/A';
        if (latency)  latency.textContent  = `${iface.health.latency_ms.toFixed(0)} ms`;
        if (loss)     loss.textContent     = `${iface.health.packet_loss.toFixed(1)}%`;
        if (upload)   upload.textContent   = `${iface.stats.send_rate_mbps.toFixed(2)} Mbps`;
        if (download) download.textContent = `${iface.stats.recv_rate_mbps.toFixed(2)} Mbps`;

        // Update per-interface chart history
        if (!this.ifaceHistories[iface.name]) {
            this.ifaceHistories[iface.name] = { upload: [], download: [] };
        }
        const hist = this.ifaceHistories[iface.name];
        hist.upload.push(iface.stats.send_rate_mbps);
        hist.download.push(iface.stats.recv_rate_mbps);
        if (hist.upload.length   > this.maxHistoryPoints) hist.upload.shift();
        if (hist.download.length > this.maxHistoryPoints) hist.download.shift();

        const canvas = document.getElementById(`chart-${iface.name}`);
        if (canvas) {
            const ctx = canvas.getContext('2d');
            this.drawDualChart(ctx, hist.upload, hist.download);
        }
    }
    
    async toggleInterface(name, enabled) {
        try {
            const endpoint = enabled ? 'enable' : 'disable';
            const response = await fetch(`/api/interfaces/${encodeURIComponent(name)}/${endpoint}`, {
                method: 'POST'
            });
            
            if (response.ok) {
                console.log(`Interface ${name} ${enabled ? 'enabled' : 'disabled'}`);
                // Refresh both interface cards and aggregate stats (activeLinks count)
                await Promise.all([this.fetchInterfaces(), this.fetchStatus()]);
            } else {
                console.error(`Failed to ${endpoint} interface ${name}`);
                // Revert toggle — look up card by data attribute, not CSS id selector,
                // so names with special characters don't break querySelector
                const card = document.querySelector(`[data-iface-name="${CSS.escape(name)}"]`);
                const checkbox = card ? card.querySelector('input[type="checkbox"]') : null;
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
        // Use toFixed(0) so floats don't render as e.g. "1234.5678"
        return Number.isInteger(num) ? num.toString() : num.toFixed(0);
    }
}

// Initialize dashboard after DOM is fully ready
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new BondlinkDashboard();
    dashboard.init();
});
