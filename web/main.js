// === PERSISTENT TTS QUEUE ENGINE ===
window.activeUtterances = new Set();

function cleanTextForSpeech(rawText) {
    return rawText
        .replace(/[*#_`]/g, '')                     // Strip markdown syntax
        .replace(/•/g, '')                          // Strip bullet points
        .replace(/\$([0-9]+(\.[0-9]+)?)/g, '$1 dollars') // Read tickers/prices naturally
        .replace(/σ/g, 'sigma')                     // Read sigma volatility
        .replace(/cuda:[0-1]/gi, 'Cuda')            // Clean hardware labels
        .replace(/\s+/g, ' ')
        .trim();
}

function speakText(text) {
    if (!('speechSynthesis' in window)) return;
    
    // Cancel existing audio stream
    window.speechSynthesis.cancel();
    window.activeUtterances.clear();

    const sanitized = cleanTextForSpeech(text);
    // Split into natural sentences / clauses
    const chunks = sanitized.match(/[^.!?:\n]+[.!?:\n]+/g) || [sanitized];

    chunks.forEach((chunk, index) => {
        const cleanChunk = chunk.trim();
        if (!cleanChunk) return;

        const utterance = new SpeechSynthesisUtterance(cleanChunk);
        utterance.rate = 1.05;
        utterance.pitch = 1.0;

        // Retain reference to avoid Chromium GC collection mid-playback
        window.activeUtterances.add(utterance);

        utterance.onend = () => {
            window.activeUtterances.delete(utterance);
        };

        utterance.onerror = (e) => {
            console.error(`TTS Chunk Error at index ${index}:`, e);
            window.activeUtterances.delete(utterance);
        };

        window.speechSynthesis.speak(utterance);
    });
}

// System Stats Update Loop
async function updateStats() {
    try {
        let stats = await eel.get_system_stats()();
        if (stats) {
            document.getElementById('ramBadge').innerText = `● RAM: ${stats.ram_percent}%`;
            document.getElementById('engineBadge').innerText = `● OLLAMA: ${stats.model}`;
        }
    } catch (e) {
        console.log("Stats fetch error:", e);
    }
}
setInterval(updateStats, 3000);
updateStats();

// Append Log Message
function addLog(msg) {
    let logBox = document.getElementById('logBox');
    let entry = document.createElement('div');
    entry.innerText = msg;
    logBox.appendChild(entry);
    logBox.scrollTop = logBox.scrollHeight;
}

// Append Chat Message
function addChatMessage(sender, text) {
    let chatDrawer = document.getElementById('chatDrawer');
    let bubble = document.createElement('div');
    bubble.className = `chat-entry ${sender === 'Pierre' ? 'chat-user' : 'chat-julie'}`;
    bubble.innerHTML = `<strong>${sender}:</strong> ${text}`;
    chatDrawer.appendChild(bubble);
    chatDrawer.scrollTop = chatDrawer.scrollHeight;
}

// Set Status State
function setStatus(state, text) {
    let statusDesc = document.getElementById('statusDesc');
    statusDesc.innerText = text;
    if (state === 'listening') {
        statusDesc.style.color = '#34D399';
    } else if (state === 'processing') {
        statusDesc.style.color = '#F59E0B';
    } else {
        statusDesc.style.color = '#64748B';
    }
}

// Trigger Microphone Voice Input
async function triggerMicInput() {
    let micBtn = document.getElementById('micBtn');
    let micBadge = document.getElementById('micBadge');
    
    micBtn.disabled = true;
    micBadge.innerText = '● MIC: LISTENING...';
    micBadge.style.color = '#34D399';
    setStatus('listening', 'LISTENING...');
    addLog('[MIC] Activating voice input thread...');

    try {
        let text = await eel.listen_voice()();
        if (text && text.trim().length > 0) {
            addLog(`[STT RECOGNIZED] '${text}'`);
            document.getElementById('cmdInput').value = text;
            dispatchQuery();
        } else {
            addLog('[MIC] Timeout - No speech detected.');
            setStatus('standby', 'STANDBY');
        }
    } catch (e) {
        addLog(`[MIC Error] ${e}`);
        setStatus('standby', 'STANDBY');
    } finally {
        micBtn.disabled = false;
        micBadge.innerText = '● MIC: READY';
        micBadge.style.color = '#A5B4FC';
    }
}

// Dispatch Query Execution
async function dispatchQuery() {
    let inputField = document.getElementById('cmdInput');
    let prompt = inputField.value ? inputField.value.trim() : '';
    if (!prompt) return;

    let sendBtn = document.getElementById('sendBtn');
    sendBtn.disabled = true;

    addChatMessage('Pierre', prompt);
    addLog(`[QUERY] Dispatched: '${prompt}'`);
    inputField.value = '';
    setStatus('processing', 'PROCESSING...');

    try {
        let response = await eel.run_query(prompt)();
        addChatMessage('Julie', response || 'Execution completed.');
        addLog('[COMPLETE] Execution and voice response finished.');
    } catch (e) {
        addLog(`[EXECUTION ERROR] ${e}`);
        addChatMessage('Julie', 'Execution encountered an error.');
    } finally {
        sendBtn.disabled = false;
        setStatus('standby', 'STANDBY');
    }
}

function handleKeyDown(event) {
    if (event.key === 'Enter') {
        dispatchQuery();
    }
}

// === REACTIVE HUD TELEMETRY DISPATCHER & BUCKET TABS ===
let currentSelectedBucket = 'CORE';

function setupBucketTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentSelectedBucket = btn.getAttribute('data-bucket') || 'CORE';
            updatePortfolioTelemetryHUD();
        });
    });
}

function renderCard(pos, isPinned) {
    const isBreached = pos.spot_price > 0 && pos.spot_price <= pos.invalidation_stop;
    const tfmClass = pos.timesfm_delta_pct >= 0 ? 'bullish' : 'bearish';
    const chrClass = pos.chronos_delta_pct >= 0 ? 'bullish' : 'bearish';
    const spreadWarning = pos.model_spread_delta > 5.0 ? 'warning' : '';

    return `
        <div class="ticker-card ${isBreached ? 'breach-alert' : ''}">
            <div class="ticker-card-header">
                <span class="ticker-symbol">$${pos.ticker} ${isPinned ? '<span style="color:#ff3366;font-size:0.7rem;font-weight:900;">[BREACH]</span>' : ''}</span>
                <span class="ticker-spot">$${Number(pos.spot_price).toFixed(2)}</span>
            </div>
            <div class="model-vectors">
                <span class="vector-badge ${tfmClass}">TFM: ${pos.timesfm_delta_pct > 0 ? '+' : ''}${Number(pos.timesfm_delta_pct).toFixed(2)}%</span>
                <span class="vector-badge ${chrClass}">CHR: ${pos.chronos_delta_pct > 0 ? '+' : ''}${Number(pos.chronos_delta_pct).toFixed(2)}%</span>
            </div>
            <div class="invalidation-risk-line">
                <span>Stop: $${Number(pos.invalidation_stop).toFixed(2)} (1.8x ATR)</span>
                <span class="spread-badge ${spreadWarning}">Δ ${Number(pos.model_spread_delta).toFixed(2)}%</span>
            </div>
        </div>
    `;
}

async function updatePortfolioTelemetryHUD() {
    try {
        if (!window.eel || !eel.get_portfolio_hud_telemetry) return;
        const telemetry = await eel.get_portfolio_hud_telemetry()();
        if (!telemetry || !telemetry.positions) return;

        const riskBadge = document.getElementById('portfolio-risk-badge');
        if (riskBadge && typeof telemetry.systemic_risk_score === 'number') {
            riskBadge.textContent = `σ: ${telemetry.systemic_risk_score.toFixed(2)}%`;
        }

        const breachContainer = document.getElementById('pinned-breach-container');
        const activeContainer = document.getElementById('active-portfolio-container');

        const allPositions = telemetry.positions;
        const breachedPositions = allPositions.filter(p => p.spot_price > 0 && p.spot_price <= p.invalidation_stop);
        const currentBucketPositions = allPositions.filter(p => (p.bucket || 'SWING').toUpperCase() === currentSelectedBucket.toUpperCase());

        // Update Tab Counts
        const coreCount = allPositions.filter(p => (p.bucket || '').toUpperCase() === 'CORE').length;
        const swingCount = allPositions.filter(p => (p.bucket || '').toUpperCase() === 'SWING').length;
        const irsCount = allPositions.filter(p => (p.bucket || '').toUpperCase() === 'IRS').length;

        const btnCore = document.querySelector('.tab-btn[data-bucket="CORE"]');
        const btnSwing = document.querySelector('.tab-btn[data-bucket="SWING"]');
        const btnIrs = document.querySelector('.tab-btn[data-bucket="IRS"]');
        if (btnCore) btnCore.innerText = `CORE (${coreCount})`;
        if (btnSwing) btnSwing.innerText = `SWING (${swingCount})`;
        if (btnIrs) btnIrs.innerText = `IRS (${irsCount})`;

        // Render Pinned Breaches
        if (breachContainer) {
            breachContainer.innerHTML = breachedPositions.map(pos => renderCard(pos, true)).join('');
        }

        // Render Current Tab Holdings
        if (activeContainer) {
            if (currentBucketPositions.length === 0) {
                activeContainer.innerHTML = `<div class="telemetry-placeholder">No active ${currentSelectedBucket} positions.</div>`;
            } else {
                activeContainer.innerHTML = currentBucketPositions.map(pos => renderCard(pos, false)).join('');
            }
        }
    } catch (err) {
        console.error("HUD Telemetry Poll Error:", err);
    }
}

// 2000ms Event Loop Hook
setInterval(updatePortfolioTelemetryHUD, 2000);
document.addEventListener('DOMContentLoaded', () => {
    setupBucketTabs();
    updatePortfolioTelemetryHUD();
});
setTimeout(() => {
    setupBucketTabs();
    updatePortfolioTelemetryHUD();
}, 500);
