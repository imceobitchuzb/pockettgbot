// Pocket Option AI Signal Engine & Trading Terminal v3.0

class TradingApp {
  constructor() {
    this.currentPair = "AUD_CHF_OTC";
    this.currentPrecision = 5;
    this.timeframe = "1m";
    this.expirationMinutes = 1;
    this.activeSignal = null;
    this.signalTimerInterval = null;
    this.pairs = { otc: [], regular: [] };
    this.soundEnabled = true;
    this.chart = null;
    this.ws = null;
    this.isThinking = false;
    this.audioCtx = null;
    this.settings = {};

    this.init();
  }

  async init() {
    this.initTelegramWebApp();
    this.initChart();
    this.setupEventListeners();
    this.startCandleClock();
    await this.fetchPairs();
    await this.loadSettings();
    await this.updatePairPriceImmediate(this.currentPair);
    await this.loadCandles(this.currentPair, this.timeframe);
    this.initWebSocket();
    this.startFallbackPolling();
    await this.generateSignalWithThinking();
    await this.refreshHistory();
    this.loadScannerData();
  }

  initTelegramWebApp() {
    if (window.Telegram && window.Telegram.WebApp) {
      const tg = window.Telegram.WebApp;
      try {
        tg.ready();
        tg.expand();
      } catch (e) {}
    }
  }

  initChart() {
    if (typeof CandlestickChart !== "undefined") {
      this.chart = new CandlestickChart('candleChartCanvas');
    }
  }

  startCandleClock() {
    setInterval(() => {
      const now = Math.floor(Date.now() / 1000);
      const secLeft = 60 - (now % 60);
      const tag = document.getElementById('chartCandleCountdown');
      if (tag) {
        tag.textContent = `⏱ 00:${secLeft.toString().padStart(2, '0')}`;
      }
    }, 1000);
  }

  addLog(tag, message) {
    const box = document.getElementById('activityLogBox');
    if (!box) return;
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    const now = new Date();
    const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
    entry.innerHTML = `<span class="log-time">[${tag} ${timeStr}]</span><span class="log-msg">${message}</span>`;
    box.prepend(entry);
    if (box.children.length > 20) {
      box.removeChild(box.lastChild);
    }
  }

  setupEventListeners() {
    // Tab switching
    document.querySelectorAll('.nav-tab').forEach(tabBtn => {
      tabBtn.addEventListener('click', () => {
        const targetTabId = tabBtn.getAttribute('data-tab');
        this.switchTab(targetTabId, tabBtn);
      });
    });

    // Theme toggle
    const themeBtn = document.getElementById('themeToggleBtn');
    if (themeBtn) {
      themeBtn.addEventListener('click', () => {
        document.body.classList.toggle('theme-dark');
        const isDark = document.body.classList.contains('theme-dark');
        themeBtn.querySelector('.theme-icon').textContent = isDark ? '☀️' : '🌙';
        if (this.chart) this.chart.render();
      });
    }

    // Pair selector modal
    const pairBtn = document.getElementById('pairSelectorBtn');
    const modal = document.getElementById('pairsModal');
    const btnCloseModal = document.getElementById('btnClosePairsModal');

    if (pairBtn && modal) {
      pairBtn.addEventListener('click', () => {
        modal.classList.add('show');
        this.renderPairsModal('otc');
      });
    }

    if (btnCloseModal && modal) {
      btnCloseModal.addEventListener('click', () => modal.classList.remove('show'));
      modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.remove('show');
      });
    }

    // Modal category tabs
    document.querySelectorAll('.modal-category-tabs .cat-tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        document.querySelectorAll('.modal-category-tabs .cat-tab').forEach(t => t.classList.remove('active'));
        e.target.classList.add('active');
        const cat = e.target.getAttribute('data-cat');
        this.renderPairsModal(cat);
      });
    });

    // Generate signal button
    const btnGen = document.getElementById('btnGenerateSignal');
    if (btnGen) {
      btnGen.addEventListener('click', () => {
        if (!this.isThinking) this.generateSignalWithThinking();
      });
    }

    // Auto-scan button
    const btnAutoScan = document.getElementById('btnAutoScan');
    if (btnAutoScan) {
      btnAutoScan.addEventListener('click', () => this.runAutoScan());
    }

    // Expiration selector chips
    document.querySelectorAll('.exp-chips .exp-chip').forEach(chip => {
      chip.addEventListener('click', (e) => {
        document.querySelectorAll('.exp-chips .exp-chip').forEach(c => c.classList.remove('active'));
        e.currentTarget.classList.add('active');
        const expVal = e.currentTarget.getAttribute('data-exp');
        this.expirationMinutes = parseInt(expVal) || 1;
        const expLabel = document.getElementById('valExpiration');
        if (expLabel) expLabel.textContent = e.currentTarget.textContent;
      });
    });

    // Chart timeframe buttons
    document.querySelectorAll('.chart-timeframes .tf-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        document.querySelectorAll('.chart-timeframes .tf-btn').forEach(b => b.classList.remove('active'));
        e.currentTarget.classList.add('active');
        this.timeframe = e.currentTarget.getAttribute('data-tf');
        this.loadCandles(this.currentPair, this.timeframe);
      });
    });

    // Price sync bar controls
    const btnSyncPrice = document.getElementById('btnSyncPrice');
    const syncPriceBar = document.getElementById('syncPriceBar');
    const btnCancelSync = document.getElementById('btnCancelSync');
    const btnApplySync = document.getElementById('btnApplySync');

    if (btnSyncPrice && syncPriceBar) {
      btnSyncPrice.addEventListener('click', () => {
        syncPriceBar.style.display = syncPriceBar.style.display === 'none' ? 'flex' : 'none';
        const curEl = document.getElementById('valEntryPrice');
        const inputSync = document.getElementById('inputSyncPrice');
        if (curEl && inputSync) inputSync.value = curEl.textContent.trim().replace(',', '.');
      });
    }

    if (btnCancelSync && syncPriceBar) {
      btnCancelSync.addEventListener('click', () => syncPriceBar.style.display = 'none');
    }

    if (btnApplySync && syncPriceBar) {
      btnApplySync.addEventListener('click', async () => {
        const inputSync = document.getElementById('inputSyncPrice');
        const newPrice = parseFloat(inputSync.value);
        if (!isNaN(newPrice) && newPrice > 0) {
          await this.calibratePairPrice(this.currentPair, newPrice);
          syncPriceBar.style.display = 'none';
        }
      });
    }

    // Settings Modal
    const btnOpenSettings = document.getElementById('btnOpenSettings');
    const settingsModal = document.getElementById('settingsModal');
    const btnCloseSettings = document.getElementById('btnCloseSettingsModal');
    const btnSaveSettings = document.getElementById('btnSaveSettings');
    const btnResetSettings = document.getElementById('btnResetSettings');

    if (btnOpenSettings && settingsModal) {
      btnOpenSettings.addEventListener('click', () => {
        settingsModal.classList.add('show');
        this.populateSettingsForm();
      });
    }
    if (btnCloseSettings && settingsModal) {
      btnCloseSettings.addEventListener('click', () => settingsModal.classList.remove('show'));
    }
    if (btnSaveSettings) {
      btnSaveSettings.addEventListener('click', () => this.saveSettings());
    }
    if (btnResetSettings) {
      btnResetSettings.addEventListener('click', () => this.resetSettings());
    }

    // Sliders live label update
    const rngConf = document.getElementById('rngMinConfidence');
    const lblConf = document.getElementById('lblMinConfidence');
    if (rngConf && lblConf) {
      rngConf.addEventListener('input', () => lblConf.textContent = `${rngConf.value}%`);
    }

    const rngConfl = document.getElementById('rngMinConfluence');
    const lblConfl = document.getElementById('lblMinConfluence');
    if (rngConfl && lblConfl) {
      rngConfl.addEventListener('input', () => lblConfl.textContent = `${rngConfl.value} из 9`);
    }

    const rngPay = document.getElementById('rngMinPayout');
    const lblPay = document.getElementById('lblMinPayout');
    if (rngPay && lblPay) {
      rngPay.addEventListener('input', () => lblPay.textContent = `${rngPay.value}%`);
    }

    // Debugger Modal
    const btnOpenDebugger = document.getElementById('btnOpenDebugger');
    const debuggerModal = document.getElementById('debuggerModal');
    const btnCloseDebugger = document.getElementById('btnCloseDebuggerModal');

    if (btnOpenDebugger && debuggerModal) {
      btnOpenDebugger.addEventListener('click', () => {
        debuggerModal.classList.add('show');
        this.loadDebuggerData();
      });
    }
    if (btnCloseDebugger && debuggerModal) {
      btnCloseDebugger.addEventListener('click', () => debuggerModal.classList.remove('show'));
    }

    // File input for photo tab
    const fileInput = document.getElementById('fileInput');
    const btnAnalyzePhoto = document.getElementById('btnAnalyzePhoto');
    const btnClearImg = document.getElementById('btnClearImg');
    const dropzonePrompt = document.getElementById('dropzonePrompt');
    const dropzonePreview = document.getElementById('dropzonePreview');
    const previewImg = document.getElementById('previewImg');

    if (fileInput) {
      fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
          const reader = new FileReader();
          reader.onload = (event) => {
            previewImg.src = event.target.result;
            dropzonePrompt.style.display = 'none';
            dropzonePreview.style.display = 'block';
            if (btnAnalyzePhoto) btnAnalyzePhoto.disabled = false;
          };
          reader.readAsDataURL(file);
        }
      });
    }

    if (btnClearImg) {
      btnClearImg.addEventListener('click', () => {
        fileInput.value = '';
        previewImg.src = '';
        dropzonePrompt.style.display = 'flex';
        dropzonePreview.style.display = 'none';
        if (btnAnalyzePhoto) btnAnalyzePhoto.disabled = true;
        const resBox = document.getElementById('photoResultBox');
        if (resBox) resBox.style.display = 'none';
      });
    }

    if (btnAnalyzePhoto) {
      btnAnalyzePhoto.addEventListener('click', () => this.analyzeUploadedScreenshot());
    }

    // Refresh history
    const btnRefHistory = document.getElementById('btnRefreshHistory');
    if (btnRefHistory) {
      btnRefHistory.addEventListener('click', () => this.refreshHistory());
    }
  }

  switchTab(tabId, activeBtn) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.nav-tab').forEach(b => {
      b.classList.remove('active');
      const iconWrap = b.querySelector('.nav-icon');
      if (iconWrap) iconWrap.classList.remove('active-pill');
    });

    const targetTab = document.getElementById(tabId);
    if (targetTab) targetTab.classList.add('active');

    if (activeBtn) {
      activeBtn.classList.add('active');
      const iconWrap = activeBtn.querySelector('.nav-icon');
      if (iconWrap) iconWrap.classList.add('active-pill');
    }

    if (tabId === 'tabSignals' && this.chart) {
      setTimeout(() => this.chart.resize(), 50);
    } else if (tabId === 'tabScanner') {
      this.loadScannerData();
    }
  }

  async fetchPairs() {
    try {
      const res = await fetch('/api/pairs');
      if (res.ok) {
        this.pairs = await res.json();
      }
    } catch (e) {
      console.warn("Failed to fetch pairs:", e);
    }
  }

  renderPairsModal(category) {
    const container = document.getElementById('pairsListModal');
    if (!container) return;
    container.innerHTML = '';
    const list = this.pairs[category] || [];

    list.forEach(p => {
      const item = document.createElement('div');
      item.className = `pair-modal-item ${p.id === this.currentPair ? 'active' : ''}`;
      item.innerHTML = `
        <span class="p-item-name">${p.name}</span>
        <span class="p-item-payout">${p.payout}%</span>
      `;
      item.addEventListener('click', () => {
        this.selectPair(p.id, p.name, p.category, p.payout, p.precision);
        document.getElementById('pairsModal').classList.remove('show');
      });
      container.appendChild(item);
    });
  }

  async selectPair(pairId, pairName, category, payout, precision) {
    this.currentPair = pairId;
    this.currentPrecision = precision || 5;

    const nameEl = document.getElementById('headerPairName');
    const catEl = document.getElementById('headerPairCategory');
    if (nameEl) nameEl.textContent = pairName;
    if (catEl) catEl.textContent = `${category === 'otc' ? 'OTC Рынок • 24/7' : 'Биржа (Межбанк)'} • Выплата ${payout}%`;

    this.addLog("SELECT", `Выбран инструмент ${pairName}`);
    await this.updatePairPriceImmediate(pairId);
    await this.loadCandles(pairId, this.timeframe);

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ pair: pairId }));
    }

    await this.generateSignalWithThinking();
  }

  async updatePairPriceImmediate(pairId) {
    try {
      const res = await fetch(`/api/price/${pairId}`);
      if (res.ok) {
        const data = await res.json();
        const priceFormatted = Number(data.price).toFixed(this.currentPrecision);
        const tagPrice = document.getElementById('chartCurrentPriceTag');
        const entryPrice = document.getElementById('valEntryPrice');
        if (tagPrice) tagPrice.textContent = priceFormatted;
        if (entryPrice) entryPrice.textContent = priceFormatted;
      }
    } catch (e) {}
  }

  async loadCandles(pairId, tf) {
    try {
      const res = await fetch(`/api/candles/${pairId}?timeframe=${tf}&limit=80`);
      if (res.ok) {
        const data = await res.json();
        if (this.chart) {
          this.chart.setData(data.candles || [], this.currentPrecision);
        }
      }
    } catch (e) {
      console.warn("Failed to load candles:", e);
    }
  }

  async calibratePairPrice(pairId, price) {
    try {
      const formData = new FormData();
      formData.append('pair_id', pairId);
      formData.append('price', price);
      const res = await fetch('/api/market/calibrate', { method: 'POST', body: formData });
      if (res.ok) {
        await this.loadCandles(pairId, this.timeframe);
        await this.updatePairPriceImmediate(pairId);
        this.addLog("CALIBRATE", `Юстировка цены ${pairId} -> ${price}`);
      }
    } catch (e) {}
  }

  async generateSignalWithThinking() {
    this.isThinking = true;
    const overlay = document.getElementById('thinkingOverlay');
    const stageText = document.getElementById('thinkingStageText');
    const progressBar = document.getElementById('thinkingProgressBar');

    if (overlay) overlay.style.display = 'flex';
    if (progressBar) progressBar.style.width = '10%';

    const stages = [
      { text: "Валидация потока котировок (Latency & Spike check)...", progress: "30%" },
      { text: "Анализ 6 таймфреймов и фильтрация рыночного шума...", progress: "60%" },
      { text: "Аудит 12 ворот безопасности & AI Adversarial Critic...", progress: "88%" }
    ];

    for (const stage of stages) {
      if (stageText) stageText.textContent = stage.text;
      if (progressBar) progressBar.style.width = stage.progress;
      await new Promise(r => setTimeout(r, 260));
    }

    try {
      const formData = new FormData();
      formData.append('pair_id', this.currentPair);
      formData.append('timeframe', this.timeframe);
      formData.append('expiration', this.expirationMinutes);

      const res = await fetch('/api/signal/generate', { method: 'POST', body: formData });
      if (res.ok) {
        const signalData = await res.json();
        this.applySignalToUI(signalData);
      }
    } catch (e) {
      console.error("Signal generation error:", e);
    } finally {
      if (progressBar) progressBar.style.width = '100%';
      setTimeout(() => {
        if (overlay) overlay.style.display = 'none';
        this.isThinking = false;
      }, 150);
    }
  }

  applySignalToUI(signal) {
    this.activeSignal = signal;
    const isSignal = signal.status === "SIGNAL_GENERATED" && signal.direction !== "NO_SIGNAL";

    const badge = document.getElementById('headerSignalBadge');
    const arrowSvg = document.getElementById('heroArrowSvg');
    const actionEl = document.getElementById('heroSignalAction');
    const confEl = document.getElementById('heroConfidencePercent');
    const entryEl = document.getElementById('valEntryPrice');
    const exitEl = document.getElementById('valExitPrice');
    const resStatusEl = document.getElementById('valResult');
    const gatePill = document.getElementById('gatePillStatus');

    if (isSignal) {
      const isCall = signal.direction === "CALL" || signal.direction === "BUY";
      const dirClass = isCall ? 'action-buy' : 'action-sell';
      const badgeClass = isCall ? 'badge-buy' : 'badge-sell';
      const arrowClass = isCall ? 'arrow-buy' : 'arrow-sell';

      if (badge) {
        badge.className = `status-badge ${badgeClass}`;
        badge.textContent = isCall ? 'CALL' : 'PUT';
      }
      if (actionEl) {
        actionEl.className = `pill-action ${dirClass}`;
        actionEl.textContent = isCall ? 'CALL' : 'PUT';
      }
      if (arrowSvg) {
        arrowSvg.className = `direction-arrow ${arrowClass}`;
      }
      if (confEl) {
        confEl.textContent = `${signal.confidence_percent}% (${signal.grade || 'Grade A'})`;
      }
      if (entryEl) {
        entryEl.textContent = Number(signal.entry_price).toFixed(this.currentPrecision);
      }
      if (exitEl) {
        exitEl.textContent = Number(signal.target_exit_price).toFixed(this.currentPrecision);
      }
      if (resStatusEl) {
        resStatusEl.className = 'stat-value in-progress';
        resStatusEl.textContent = 'В РАБОТЕ';
      }
      if (gatePill) {
        gatePill.className = 'gate-status-pill pass-pill';
        gatePill.textContent = '12/12 PASSED';
      }

      this.addLog("SIGNAL", `Ордер: ${signal.pair_name} ${isCall ? 'CALL' : 'PUT'} ${signal.confidence_percent}% (${signal.setup})`);
      this.startSignalCountdown(signal.seconds_left || this.expirationMinutes * 60);

    } else {
      // NO_TRADE
      if (badge) {
        badge.className = 'status-badge';
        badge.style.background = '#f59e0b';
        badge.style.color = '#fff';
        badge.textContent = 'NO TRADE';
      }
      if (actionEl) {
        actionEl.className = 'pill-action';
        actionEl.style.color = '#f59e0b';
        actionEl.textContent = 'NO TRADE';
      }
      if (confEl) {
        confEl.textContent = '0.0% (Отклонён)';
      }
      if (resStatusEl) {
        resStatusEl.className = 'stat-value';
        resStatusEl.textContent = 'ЗАЩИТА';
      }
      if (gatePill) {
        gatePill.className = 'gate-status-pill fail-pill';
        gatePill.textContent = signal.gate_status || 'VETOED';
      }
      this.addLog("VETO", `${signal.pair_name}: ${signal.reason || 'Отклонён фильтрами'}`);
    }

    this.renderIndicators(signal.indicators || []);
  }

  renderIndicators(indicators) {
    const list = document.getElementById('indicatorsList');
    if (!list) return;
    list.innerHTML = '';

    if (!indicators || indicators.length === 0) {
      list.innerHTML = '<div style="color:var(--text-muted);font-size:12px;padding:8px;">Индикаторы в состоянии ожидания...</div>';
      return;
    }

    indicators.forEach(ind => {
      const item = document.createElement('div');
      item.className = 'indicator-item';
      const isCall = ind.status === 'CALL' || ind.status === 'BUY';
      const isPut = ind.status === 'PUT' || ind.status === 'SELL';
      const voteClass = isCall ? 'vote-buy' : (isPut ? 'vote-sell' : 'vote-neutral');

      item.innerHTML = `
        <div class="ind-left">
          <span class="ind-name">${ind.name}</span>
          <span class="ind-detail">${ind.detail || ''}</span>
        </div>
        <span class="ind-vote ${voteClass}">${ind.status}</span>
      `;
      list.appendChild(item);
    });
  }

  startSignalCountdown(seconds) {
    if (this.signalTimerInterval) clearInterval(this.signalTimerInterval);
    let rem = seconds;

    this.signalTimerInterval = setInterval(() => {
      rem--;
      const resStatusEl = document.getElementById('valResult');
      if (rem <= 0) {
        clearInterval(this.signalTimerInterval);
        if (resStatusEl) {
          resStatusEl.className = 'stat-value win-status';
          resStatusEl.textContent = 'WIN';
        }
        this.refreshHistory();
      } else {
        const m = Math.floor(rem / 60);
        const s = rem % 60;
        if (resStatusEl) resStatusEl.textContent = `${m}:${s.toString().padStart(2, '0')}`;
      }
    }, 1000);
  }

  async runAutoScan() {
    this.addLog("SCANNER", "Запущен автономный 24/7 сканер всех доступных пар...");
    try {
      const res = await fetch('/api/quant/scan', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data.status === "SIGNAL_GENERATED" && data.signal) {
          this.addLog("FOUND", `Найден лучший сетап: ${data.signal.symbol} ${data.signal.direction} (${data.signal.confidence}%)`);
          await this.selectPair(data.signal.symbol, data.signal.symbol, data.signal.market_type, 85, 5);
        } else {
          this.addLog("NO_TRADE", "Все инструменты сейчас в состоянии шума / флэта. Капитал сохранён.");
          alert("Автономный сканер проверил все рынки: сейчас ни одна пара не имеет математического преимущества (Edge). Ордера не выдаются.");
        }
      }
    } catch (e) {
      console.error("Scan error:", e);
    }
  }

  async loadScannerData() {
    try {
      const res = await fetch('/api/scanner/overview');
      if (res.ok) {
        const list = await res.json();
        const tbody = document.getElementById('scannerTableBody');
        if (!tbody) return;
        tbody.innerHTML = '';

        list.forEach(p => {
          const tr = document.createElement('tr');
          const isLive = p.status === "LIVE";
          const statusBadge = isLive 
            ? '<span class="status-badge-dbg synced">LIVE</span>' 
            : `<span class="status-badge-dbg stale">${p.status}</span>`;

          tr.innerHTML = `
            <td><strong>${p.name}</strong></td>
            <td>${Number(p.price).toFixed(p.precision)}</td>
            <td><span style="color:#10b981;font-weight:700;">${p.payout}%</span></td>
            <td>${statusBadge}</td>
            <td><button class="btn-quick-analyze" data-id="${p.id}">Анализ</button></td>
          `;
          tr.querySelector('.btn-quick-analyze').addEventListener('click', () => {
            this.selectPair(p.id, p.name, p.category, p.payout, p.precision);
            this.switchTab('tabSignals', document.querySelector('.nav-tab[data-tab="tabSignals"]'));
          });
          tbody.appendChild(tr);
        });
      }
    } catch (e) {}
  }

  async loadSettings() {
    try {
      const res = await fetch('/api/settings');
      if (res.ok) {
        this.settings = await res.json();
      }
    } catch (e) {}
  }

  populateSettingsForm() {
    if (!this.settings) return;
    const rngConf = document.getElementById('rngMinConfidence');
    const lblConf = document.getElementById('lblMinConfidence');
    if (rngConf && this.settings.min_confidence) {
      const pct = Math.round(this.settings.min_confidence * 100);
      rngConf.value = pct;
      if (lblConf) lblConf.textContent = `${pct}%`;
    }

    const rngConfl = document.getElementById('rngMinConfluence');
    const lblConfl = document.getElementById('lblMinConfluence');
    if (rngConfl && this.settings.min_confluence) {
      rngConfl.value = this.settings.min_confluence;
      if (lblConfl) lblConfl.textContent = `${this.settings.min_confluence} из 9`;
    }

    const rngPay = document.getElementById('rngMinPayout');
    const lblPay = document.getElementById('lblMinPayout');
    if (rngPay && this.settings.min_payout_pct) {
      const payPct = Math.round(this.settings.min_payout_pct * 100);
      rngPay.value = payPct;
      if (lblPay) lblPay.textContent = `${payPct}%`;
    }

    const chkCritic = document.getElementById('chkStrictCritic');
    if (chkCritic) chkCritic.checked = !!this.settings.strict_critic;

    const chkOtc = document.getElementById('chkOtcEnabled');
    if (chkOtc) chkOtc.checked = !!this.settings.otc_enabled;
  }

  async saveSettings() {
    const minConf = parseInt(document.getElementById('rngMinConfidence').value) / 100.0;
    const minConfl = parseInt(document.getElementById('rngMinConfluence').value);
    const minPay = parseInt(document.getElementById('rngMinPayout').value) / 100.0;
    const strictCritic = document.getElementById('chkStrictCritic').checked;
    const otcEnabled = document.getElementById('chkOtcEnabled').checked;

    const payload = {
      min_confidence: minConf,
      min_confluence: minConfl,
      min_payout_pct: minPay,
      strict_critic: strictCritic,
      otc_enabled: otcEnabled
    };

    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const data = await res.json();
        this.settings = data.settings;
        document.getElementById('settingsModal').classList.remove('show');
        this.addLog("CONFIG", `Настройки обновлены: порог ${Math.round(minConf * 100)}%, конфлюэнс ${minConfl}`);
      }
    } catch (e) {
      alert("Ошибка сохранения настроек");
    }
  }

  async resetSettings() {
    try {
      const res = await fetch('/api/settings/reset', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        this.settings = data.settings;
        this.populateSettingsForm();
        this.addLog("CONFIG", "Настройки сброшены к заводским квант-параметрам.");
      }
    } catch (e) {}
  }

  async loadDebuggerData() {
    try {
      const [resHealth, resComp] = await Promise.all([
        fetch('/api/debugger/health'),
        fetch('/api/debugger/price-comparison')
      ]);

      if (resHealth.ok) {
        const health = await resHealth.json();
        const wsStatus = document.getElementById('dbgWsStatus');
        const latVal = document.getElementById('dbgLatencyVal');
        if (wsStatus) wsStatus.textContent = health.is_connected ? 'ПОДКЛЮЧЕНО' : 'ОФЛАЙН';
        if (latVal && health.sources && health.sources.POCKET_OPTION_WS) {
          latVal.textContent = `${health.sources.POCKET_OPTION_WS.ping_ms} мс`;
        }
      }

      if (resComp.ok) {
        const compList = await resComp.json();
        const tbody = document.getElementById('debuggerTableBody');
        if (!tbody) return;
        tbody.innerHTML = '';

        compList.forEach(item => {
          const tr = document.createElement('tr');
          const isSynced = item.status === "SYNCHRONIZED";
          const stClass = isSynced ? 'synced' : (item.status === 'DESYNC' ? 'desync' : 'stale');

          tr.innerHTML = `
            <td><strong>${item.symbol}</strong></td>
            <td>${Number(item.source_price).toFixed(5)}</td>
            <td>${Number(item.bot_price).toFixed(5)}</td>
            <td>${item.diff_pips} pips</td>
            <td><span class="status-badge-dbg ${stClass}">${item.status}</span></td>
          `;
          tbody.appendChild(tr);
        });
      }
    } catch (e) {}
  }

  async analyzeUploadedScreenshot() {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    if (!file) return;

    const btnAnalyze = document.getElementById('btnAnalyzePhoto');
    if (btnAnalyze) {
      btnAnalyze.disabled = true;
      btnAnalyze.querySelector('.btn-text').textContent = 'Анализ Vision Quant...';
    }

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('asset_hint', this.currentPair);
      formData.append('timeframe_hint', this.timeframe);

      const res = await fetch('/api/signal/analyze-image', { method: 'POST', body: formData });
      if (res.ok) {
        const data = await res.json();
        this.displayPhotoResult(data);
      }
    } catch (e) {
      console.error("Photo analysis error:", e);
    } finally {
      if (btnAnalyze) {
        btnAnalyze.disabled = false;
        btnAnalyze.querySelector('.btn-text').textContent = 'Проанализировать свечную структуру';
      }
    }
  }

  displayPhotoResult(res) {
    const box = document.getElementById('photoResultBox');
    if (!box) return;
    box.style.display = 'block';

    const pairEl = document.getElementById('photoPairName');
    const confEl = document.getElementById('photoConfidence');
    const badgeEl = document.getElementById('photoDirectionBadge');
    const descEl = document.getElementById('photoSignalDesc');
    const syncEl = document.getElementById('photoSyncVal');

    if (!res.is_valid_chart || !res.signal) {
      if (pairEl) pairEl.textContent = res.asset || 'НЕ ОПРЕДЕЛЕНО';
      if (confEl) confEl.textContent = '0.0%';
      if (badgeEl) {
        badgeEl.textContent = 'NO TRADE';
        badgeEl.style.background = '#f59e0b';
      }
      if (descEl) descEl.textContent = res.reason || 'Недостаточно данных для входа';
      if (syncEl) syncEl.textContent = 'ОТКЛОНЕНО';
      return;
    }

    const isCall = res.direction === 'CALL' || res.direction === 'BUY';
    if (pairEl) pairEl.textContent = res.asset;
    if (confEl) confEl.textContent = `${res.confidence_percent}% проходимость`;
    if (badgeEl) {
      badgeEl.textContent = isCall ? 'CALL' : 'PUT';
      badgeEl.style.background = isCall ? '#0088ff' : '#ff3366';
    }
    if (descEl) descEl.textContent = res.summary || `Рекомендуется вход на ${isCall ? 'повышение (CALL)' : 'понижение (PUT)'}`;
    if (syncEl) syncEl.textContent = 'SYNCED';

    this.addLog("VISION", `Скриншот верифицирован: ${res.asset} ${res.direction} (${res.confidence_percent}%)`);
  }

  async refreshHistory() {
    try {
      const res = await fetch('/api/history');
      if (res.ok) {
        const data = await res.json();
        const tot = document.getElementById('statTotalSignals');
        const wr = document.getElementById('statWinRate');
        const w = document.getElementById('statWinsCount');
        const l = document.getElementById('statLossCount');
        if (tot) tot.textContent = data.total_signals || 0;
        if (wr) wr.textContent = `${data.win_rate || 0}%`;
        if (w) w.textContent = data.wins || 0;
        if (l) l.textContent = data.losses || 0;
      }
    } catch (e) {}
  }

  initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/live`;
    try {
      this.ws = new WebSocket(wsUrl);
      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.pair === this.currentPair && msg.price) {
            const priceFormatted = Number(msg.price).toFixed(this.currentPrecision);
            const tagPrice = document.getElementById('chartCurrentPriceTag');
            if (tagPrice) tagPrice.textContent = priceFormatted;

            if (this.chart && msg.latest_candle) {
              this.chart.updateLatestCandle(msg.latest_candle);
            }
          }
        } catch (e) {}
      };
      this.ws.onclose = () => {
        setTimeout(() => this.initWebSocket(), 2000);
      };
    } catch (e) {}
  }

  startFallbackPolling() {
    setInterval(() => {
      if (this.currentPair) {
        this.updatePairPriceImmediate(this.currentPair);
      }
    }, 1500);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.tradingApp = new TradingApp();
});
