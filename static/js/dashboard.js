document.addEventListener('DOMContentLoaded', function() {
    const navItems = document.querySelectorAll('.nav-item');
    const sections = document.querySelectorAll('.content-section');
    const pageTitle = document.getElementById('page-title');
    
    const titles = {
        'likes': 'Send Likes',
        'tokens': 'Token Manager',
        'stats': 'Statistics',
        'health': 'System Health'
    };
    
    navItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const section = this.dataset.section;
            
            navItems.forEach(nav => nav.classList.remove('active'));
            this.classList.add('active');
            
            sections.forEach(sec => sec.classList.remove('active'));
            document.getElementById(`${section}-section`).classList.add('active');
            
            pageTitle.textContent = titles[section];
            
            if (section === 'tokens') loadTokenStatus();
            if (section === 'stats') loadStats();
            if (section === 'health') loadHealth();
        });
    });
    
    document.getElementById('likeForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const uid = document.getElementById('uid').value;
        const server = document.getElementById('server').value;
        const btn = document.getElementById('sendBtn');
        const resultBox = document.getElementById('likeResult');
        
        btn.disabled = true;
        btn.innerHTML = '<svg class="spinner" width="16" height="16" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" opacity="0.25"/><path d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" fill="currentColor"/></svg> Processing...';
        
        try {
            const response = await fetch(`/like?uid=${uid}&server_name=${server}`);
            const data = await response.json();
            
            if (response.ok) {
                resultBox.className = 'result-box success';
                resultBox.innerHTML = `
                    <h4 style="margin-bottom: 0.5rem;">✓ Success!</h4>
                    <div style="display: grid; gap: 0.5rem; font-size: 0.875rem;">
                        <div><strong>Player:</strong> ${data.PlayerNickname}</div>
                        <div><strong>UID:</strong> ${data.UID}</div>
                        <div><strong>Likes Given:</strong> ${data.LikesGivenByAPI}</div>
                        <div><strong>Before:</strong> ${data.LikesbeforeCommand} → <strong>After:</strong> ${data.LikesafterCommand}</div>
                    </div>
                `;
            } else {
                throw new Error(data.error || 'Failed to send likes');
            }
        } catch (error) {
            resultBox.className = 'result-box error';
            resultBox.innerHTML = `<h4>✗ Error</h4><p>${error.message}</p>`;
        } finally {
            resultBox.style.display = 'block';
            btn.disabled = false;
            btn.innerHTML = '<svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20"><path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z"/></svg> Send Likes';
        }
    });
    
    document.getElementById('refreshTokensBtn').addEventListener('click', async function() {
        const btn = this;
        const resultBox = document.getElementById('refreshResult');
        
        btn.disabled = true;
        resultBox.className = 'result-box info';
        resultBox.style.display = 'block';
        resultBox.innerHTML = `
            <h4>🔄 Refreshing Tokens...</h4>
            <div id="progressBar" style="width: 100%; height: 8px; background: var(--gray); border-radius: 4px; margin: 1rem 0; overflow: hidden;">
                <div id="progressFill" style="width: 0%; height: 100%; background: linear-gradient(90deg, var(--primary), var(--secondary)); transition: width 0.3s;"></div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
                <div><strong>Progress:</strong> <span id="progressText">0/0</span></div>
                <div><strong>Success:</strong> <span id="successText">0</span></div>
                <div><strong>Failed:</strong> <span id="failedText">0</span></div>
            </div>
            <div id="latestUid" style="font-size: 0.875rem; color: var(--text-light); max-height: 100px; overflow-y: auto;"></div>
        `;
        
        const eventSource = new EventSource('/refresh-tokens-stream?region=IND');
        const latestUidDiv = document.getElementById('latestUid');
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        const successText = document.getElementById('successText');
        const failedText = document.getElementById('failedText');
        
        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            
            if (data.ping) return;
            
            if (data.uid) {
                const status = data.success ? '✓' : '✗';
                const color = data.success ? 'var(--success)' : 'var(--danger)';
                latestUidDiv.innerHTML = `<div style="color: ${color};">${status} UID: ${data.uid}</div>` + latestUidDiv.innerHTML;
                
                const progress = (data.current / data.total) * 100;
                progressFill.style.width = progress + '%';
                progressText.textContent = `${data.current}/${data.total}`;
                successText.textContent = data.success_count;
                failedText.textContent = data.failed_count;
            }
            
            if (data.done) {
                eventSource.close();
                resultBox.className = 'result-box success';
                resultBox.innerHTML = `
                    <h4>✓ ${data.message || 'Token Refresh Complete!'}</h4>
                    ${data.success ? `
                        <div style="margin-top: 0.75rem; display: grid; gap: 0.5rem; font-size: 0.875rem;">
                            <div><strong>Success:</strong> ${data.success} tokens</div>
                            <div><strong>Failed:</strong> ${data.failed} tokens</div>
                            <div><strong>Total:</strong> ${data.total} accounts</div>
                        </div>
                    ` : ''}
                `;
                btn.disabled = false;
                loadTokenStatus();
                loadStats();
            }
            
            if (data.error) {
                eventSource.close();
                resultBox.className = 'result-box error';
                resultBox.innerHTML = `<h4>✗ Error</h4><p>${data.error}</p>`;
                btn.disabled = false;
            }
        };
        
        eventSource.onerror = function() {
            eventSource.close();
            btn.disabled = false;
        };
    });
    
    document.getElementById('generateAllTokensBtn').addEventListener('click', async function() {
        const btn = this;
        const resultBox = document.getElementById('refreshResult');
        
        if (!confirm('This will generate tokens for ALL 4707 accounts. This may take 10-20 minutes. Continue?')) {
            return;
        }
        
        btn.disabled = true;
        resultBox.className = 'result-box info';
        resultBox.style.display = 'block';
        resultBox.innerHTML = `
            <h4>⚡ Generating All Tokens...</h4>
            <div id="progressBar" style="width: 100%; height: 8px; background: var(--gray); border-radius: 4px; margin: 1rem 0; overflow: hidden;">
                <div id="progressFill" style="width: 0%; height: 100%; background: linear-gradient(90deg, var(--primary), var(--secondary)); transition: width 0.3s;"></div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
                <div><strong>Progress:</strong> <span id="progressText">0/4707</span></div>
                <div><strong>Success:</strong> <span id="successText">0</span></div>
                <div><strong>Failed:</strong> <span id="failedText">0</span></div>
            </div>
            <div id="latestUid" style="font-size: 0.875rem; color: var(--text-light); max-height: 100px; overflow-y: auto; border: 1px solid var(--border); border-radius: 0.5rem; padding: 0.5rem;"></div>
        `;
        
        const eventSource = new EventSource('/generate-all-tokens-stream?region=IND');
        const latestUidDiv = document.getElementById('latestUid');
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        const successText = document.getElementById('successText');
        const failedText = document.getElementById('failedText');
        
        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            
            if (data.ping) return;
            
            if (data.uid) {
                const status = data.success ? '✓' : '✗';
                const color = data.success ? 'var(--success)' : 'var(--danger)';
                latestUidDiv.innerHTML = `<div style="color: ${color}; padding: 0.25rem 0;">${status} UID: ${data.uid}</div>` + latestUidDiv.innerHTML;
                
                const progress = (data.current / data.total) * 100;
                progressFill.style.width = progress + '%';
                progressText.textContent = `${data.current}/${data.total}`;
                successText.textContent = data.success_count;
                failedText.textContent = data.failed_count;
            }
            
            if (data.done) {
                eventSource.close();
                resultBox.className = 'result-box success';
                resultBox.innerHTML = `
                    <h4>✓ Token Generation Complete!</h4>
                    <div style="margin-top: 0.75rem; display: grid; gap: 0.5rem; font-size: 0.875rem;">
                        <div><strong>Success:</strong> ${data.success} tokens</div>
                        <div><strong>Failed:</strong> ${data.failed} tokens</div>
                        <div><strong>Total Accounts:</strong> ${data.total}</div>
                    </div>
                `;
                btn.disabled = false;
                loadTokenStatus();
                loadStats();
            }
            
            if (data.error) {
                eventSource.close();
                resultBox.className = 'result-box error';
                resultBox.innerHTML = `<h4>✗ Error</h4><p>${data.error}</p>`;
                btn.disabled = false;
            }
        };
        
        eventSource.onerror = function() {
            eventSource.close();
            btn.disabled = false;
        };
    });
    
    async function loadTokenStatus() {
        const content = document.getElementById('tokenStatusContent');
        content.innerHTML = '<div class="loading">Loading...</div>';
        
        try {
            const response = await fetch('/token-status');
            const data = await response.json();
            
            let html = '<div style="display: grid; gap: 0.75rem;">';
            
            for (const [region, info] of Object.entries(data.regions)) {
                html += `
                    <div style="padding: 1rem; background: var(--light); border-radius: 0.5rem;">
                        <h4 style="margin-bottom: 0.75rem; color: var(--primary);">${region} Server</h4>
                        <div class="token-info">
                            <span class="token-label">Total Tokens</span>
                            <span class="token-value">${info.token_count || 0}</span>
                        </div>
                        ${info.expires_at ? `
                            <div class="token-info">
                                <span class="token-label">Expires At</span>
                                <span class="token-value">${new Date(info.expires_at).toLocaleString()}</span>
                            </div>
                            <div class="token-info">
                                <span class="token-label">Time Until Expiry</span>
                                <span class="token-value">${info.time_until_expiry}</span>
                            </div>
                        ` : ''}
                    </div>
                `;
            }
            
            html += '</div>';
            content.innerHTML = html;
        } catch (error) {
            content.innerHTML = `<div class="result-box error">Failed to load token status</div>`;
        }
    }
    
    async function loadStats() {
        try {
            const response = await fetch('/stats');
            const data = await response.json();
            
            document.getElementById('totalTokens').textContent = Object.values(data.per_region_stats).reduce((sum, r) => sum + r.valid, 0);
            document.getElementById('tokensGenerated').textContent = data.total_tokens_generated;
            document.getElementById('tokensFailed').textContent = data.total_failures;
            document.getElementById('refreshInterval').textContent = `${data.refresh_interval_seconds}s`;
            
            let detailedHtml = '<div style="display: grid; gap: 1rem;">';
            
            for (const [region, stats] of Object.entries(data.per_region_stats)) {
                detailedHtml += `
                    <div style="padding: 1rem; background: var(--light); border-radius: 0.5rem;">
                        <h4 style="margin-bottom: 0.75rem;">${region} Region</h4>
                        <div class="health-item">
                            <span class="health-label">Valid Tokens</span>
                            <span class="health-value" style="color: var(--success);">${stats.valid}</span>
                        </div>
                        <div class="health-item">
                            <span class="health-label">Failed</span>
                            <span class="health-value" style="color: var(--danger);">${stats.failed}</span>
                        </div>
                    </div>
                `;
            }
            
            detailedHtml += `
                <div style="padding: 1rem; background: var(--light); border-radius: 0.5rem;">
                    <h4 style="margin-bottom: 0.75rem;">Service Status</h4>
                    <div class="health-item">
                        <span class="health-label">Service Running</span>
                        <span class="health-value">${data.service_running ? '✓ Yes' : '✗ No'}</span>
                    </div>
                    <div class="health-item">
                        <span class="health-label">Concurrent Limit</span>
                        <span class="health-value">${data.concurrent_limit}</span>
                    </div>
                    <div class="health-item">
                        <span class="health-label">Last Refresh</span>
                        <span class="health-value">${data.last_refresh || 'Never'}</span>
                    </div>
                </div>
            `;
            
            detailedHtml += '</div>';
            document.getElementById('detailedStats').innerHTML = detailedHtml;
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    }
    
    async function loadHealth() {
        const content = document.getElementById('healthContent');
        content.innerHTML = '<div class="loading">Loading...</div>';
        
        try {
            const [tokenStatus, stats] = await Promise.all([
                fetch('/token-status').then(r => r.json()),
                fetch('/stats').then(r => r.json())
            ]);
            
            let html = '<div style="display: grid; gap: 1rem;">';
            
            html += `
                <div style="padding: 1rem; background: var(--light); border-radius: 0.5rem;">
                    <h4 style="margin-bottom: 0.75rem;">Overall System Health</h4>
                    <div class="health-item">
                        <span class="health-label">Token Service</span>
                        <span class="health-value" style="color: ${stats.service_running ? 'var(--success)' : 'var(--danger)'};">
                            ${stats.service_running ? '✓ Running' : '✗ Stopped'}
                        </span>
                    </div>
                    <div class="health-item">
                        <span class="health-label">Total Active Tokens</span>
                        <span class="health-value">${Object.values(tokenStatus.regions).reduce((sum, r) => sum + (r.token_count || 0), 0)}</span>
                    </div>
                    <div class="health-item">
                        <span class="health-label">Success Rate</span>
                        <span class="health-value">
                            ${stats.total_tokens_generated > 0 
                                ? ((stats.total_tokens_generated / (stats.total_tokens_generated + stats.total_failures)) * 100).toFixed(1) 
                                : 100}%
                        </span>
                    </div>
                </div>
            `;
            
            for (const [region, info] of Object.entries(tokenStatus.regions)) {
                const healthStatus = info.token_count > 0 ? 'Healthy' : 'No Tokens';
                const healthColor = info.token_count > 0 ? 'var(--success)' : 'var(--warning)';
                
                html += `
                    <div style="padding: 1rem; background: var(--light); border-radius: 0.5rem;">
                        <h4 style="margin-bottom: 0.75rem;">${region} Server Health</h4>
                        <div class="health-item">
                            <span class="health-label">Status</span>
                            <span class="health-value" style="color: ${healthColor};">${healthStatus}</span>
                        </div>
                        <div class="health-item">
                            <span class="health-label">Available Tokens</span>
                            <span class="health-value">${info.token_count || 0}</span>
                        </div>
                        ${info.time_until_expiry ? `
                            <div class="health-item">
                                <span class="health-label">Token Validity</span>
                                <span class="health-value">${info.time_until_expiry}</span>
                            </div>
                        ` : ''}
                    </div>
                `;
            }
            
            html += '</div>';
            content.innerHTML = html;
        } catch (error) {
            content.innerHTML = `<div class="result-box error">Failed to load health data</div>`;
        }
    }
    
    loadStats();
});

const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    .spinner {
        animation: spin 1s linear infinite;
    }
`;
document.head.appendChild(style);
