class CandlestickChart {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.candles = [];
    this.sarPoints = [];
    this.zigzagPoints = [];
    this.currentPrice = 0;
    this.precision = 5;

    this.resize();
    window.addEventListener('resize', () => this.resize());
  }

  resize() {
    if (!this.canvas) return;
    const rect = this.canvas.parentElement.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    this.width = rect.width;
    this.height = rect.height;

    this.canvas.width = this.width * dpr;
    this.canvas.height = this.height * dpr;
    this.ctx.scale(dpr, dpr);
    this.render();
  }

  setData(candles, precision = 5) {
    this.candles = candles || [];
    this.precision = precision;
    if (this.candles.length > 0) {
      this.currentPrice = this.candles[this.candles.length - 1].close;
      this._calculateLocalIndicators();
    }
    this.render();
  }

  updateLatestCandle(candle, price) {
    if (!candle) return;
    this.currentPrice = price;
    if (this.candles.length === 0) {
      this.candles.push(candle);
    } else {
      const last = this.candles[this.candles.length - 1];
      if (last.time === candle.time) {
        this.candles[this.candles.length - 1] = candle;
      } else if (candle.time > last.time) {
        this.candles.push(candle);
        if (this.candles.length > 80) this.candles.shift();
      }
    }
    this._calculateLocalIndicators();
    this.render();
  }

  _calculateLocalIndicators() {
    if (this.candles.length < 5) return;
    // Simple fast visual SAR calculation
    this.sarPoints = [];
    let uptrend = true;
    let ep = this.candles[0].high;
    let curSar = this.candles[0].low;
    let af = 0.02;

    for (let i = 1; i < this.candles.length; i++) {
      const c = this.candles[i];
      if (uptrend) {
        curSar = curSar + af * (ep - curSar);
        if (c.low < curSar) {
          uptrend = false;
          curSar = ep;
          ep = c.low;
          af = 0.02;
        } else if (c.high > ep) {
          ep = c.high;
          af = Math.min(af + 0.02, 0.2);
        }
      } else {
        curSar = curSar + af * (ep - curSar);
        if (c.high > curSar) {
          uptrend = true;
          curSar = ep;
          ep = c.high;
          af = 0.02;
        } else if (c.low < ep) {
          ep = c.low;
          af = Math.min(af + 0.02, 0.2);
        }
      }
      this.sarPoints.push({ index: i, sar: curSar, uptrend });
    }

    // ZigZag pivots calculation
    this.zigzagPoints = [];
    const depth = 6;
    for (let i = depth; i < this.candles.length - 2; i++) {
      const curH = this.candles[i].high;
      const curL = this.candles[i].low;
      let isH = true;
      let isL = true;
      for (let j = i - depth; j <= i + 2; j++) {
        if (j >= 0 && j < this.candles.length && j !== i) {
          if (this.candles[j].high > curH) isH = false;
          if (this.candles[j].low < curL) isL = false;
        }
      }
      if (isH) this.zigzagPoints.push({ index: i, price: curH, type: 'high' });
      else if (isL) this.zigzagPoints.push({ index: i, price: curL, type: 'low' });
    }
  }

  render() {
    if (!this.ctx || this.candles.length === 0) return;
    const ctx = this.ctx;
    const w = this.width;
    const h = this.height;

    ctx.clearRect(0, 0, w, h);

    const paddingRight = 65;
    const paddingTop = 20;
    const paddingBottom = 25;
    const chartWidth = w - paddingRight;
    const chartHeight = h - paddingTop - paddingBottom;

    // Determine min/max price
    let minPrice = Infinity;
    let maxPrice = -Infinity;
    const visibleCount = Math.min(this.candles.length, 36);
    const visibleCandles = this.candles.slice(-visibleCount);
    const startIndex = this.candles.length - visibleCount;

    visibleCandles.forEach(c => {
      if (c.low < minPrice) minPrice = c.low;
      if (c.high > maxPrice) maxPrice = c.high;
    });

    const priceBuffer = (maxPrice - minPrice) * 0.15 || 0.0001;
    minPrice -= priceBuffer;
    maxPrice += priceBuffer;
    const priceRange = maxPrice - minPrice;

    const getY = (price) => {
      return paddingTop + (1 - (price - minPrice) / priceRange) * chartHeight;
    };

    const candleWidth = chartWidth / visibleCount;
    const barWidth = Math.max(3, candleWidth * 0.65);

    // 1. Draw Grid Lines
    ctx.strokeStyle = document.body.classList.contains('theme-dark') ? '#222c44' : '#edf2f7';
    ctx.lineWidth = 1;

    const gridLines = 4;
    for (let i = 0; i <= gridLines; i++) {
      const y = paddingTop + (chartHeight / gridLines) * i;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(chartWidth, y);
      ctx.stroke();

      const priceVal = maxPrice - (priceRange / gridLines) * i;
      ctx.fillStyle = document.body.classList.contains('theme-dark') ? '#64748b' : '#94a3b8';
      ctx.font = '10px sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText(priceVal.toFixed(this.precision), chartWidth + 6, y + 3);
    }

    // 2. Draw ZigZag Lines
    if (this.zigzagPoints.length > 1) {
      ctx.strokeStyle = '#f59e0b';
      ctx.lineWidth = 2;
      ctx.beginPath();
      let started = false;

      this.zigzagPoints.forEach(p => {
        if (p.index >= startIndex) {
          const visIdx = p.index - startIndex;
          const x = visIdx * candleWidth + candleWidth / 2;
          const y = getY(p.price);
          if (!started) {
            ctx.moveTo(x, y);
            started = true;
          } else {
            ctx.lineTo(x, y);
          }
        }
      });
      ctx.stroke();
    }

    // 3. Draw Candlesticks
    visibleCandles.forEach((c, idx) => {
      const x = idx * candleWidth + candleWidth / 2;
      const isBullish = c.close >= c.open;
      const bodyColor = isBullish ? '#10b981' : '#ef4444';

      const openY = getY(c.open);
      const closeY = getY(c.close);
      const highY = getY(c.high);
      const lowY = getY(c.low);

      // Wick
      ctx.strokeStyle = bodyColor;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(x, highY);
      ctx.lineTo(x, lowY);
      ctx.stroke();

      // Body
      const bodyY = Math.min(openY, closeY);
      const bodyHeight = Math.max(2, Math.abs(closeY - openY));
      ctx.fillStyle = bodyColor;
      ctx.fillRect(x - barWidth / 2, bodyY, barWidth, bodyHeight);

      // Draw Time labels every 6 candles on bottom axis
      if (idx % 6 === 0 || idx === visibleCandles.length - 1) {
        const d = new Date(c.time * 1000);
        const timeStr = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        ctx.fillStyle = document.body.classList.contains('theme-dark') ? '#64748b' : '#94a3b8';
        ctx.font = '9px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(timeStr, x, h - 8);
      }
    });

    // 4. Draw Parabolic SAR Dots
    this.sarPoints.forEach(p => {
      if (p.index >= startIndex) {
        const visIdx = p.index - startIndex;
        const x = visIdx * candleWidth + candleWidth / 2;
        const y = getY(p.sar);

        ctx.fillStyle = '#0088ff';
        ctx.beginPath();
        ctx.arc(x, y, 2.5, 0, Math.PI * 2);
        ctx.fill();
      }
    });

    // 5. Draw Current Price Horizontal Line & Tag
    if (this.currentPrice > 0) {
      const curY = getY(this.currentPrice);
      ctx.strokeStyle = '#0088ff';
      ctx.setLineDash([4, 4]);
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(0, curY);
      ctx.lineTo(chartWidth, curY);
      ctx.stroke();
      ctx.setLineDash([]);

      // Right price badge
      ctx.fillStyle = '#0088ff';
      const badgeH = 18;
      const badgeW = paddingRight - 8;
      ctx.fillRect(chartWidth + 4, curY - badgeH / 2, badgeW, badgeH);

      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 10px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(this.currentPrice.toFixed(this.precision), chartWidth + 4 + badgeW / 2, curY + 3.5);

      // Live pulse dot
      const lastX = (visibleCandles.length - 1) * candleWidth + candleWidth / 2;
      ctx.fillStyle = '#0088ff';
      ctx.beginPath();
      ctx.arc(lastX, curY, 4, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  calibratePrice(newPrice) {
    if (!newPrice || this.candles.length === 0) return;
    const diff = newPrice - this.currentPrice;
    this.currentPrice = newPrice;
    this.candles.forEach(c => {
      c.open += diff;
      c.close += diff;
      c.high += diff;
      c.low += diff;
    });
    this._calculateLocalIndicators();
    this.render();
  }
}
