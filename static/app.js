// Werkudoro Macroeconomic Intelligence Terminal - Client Engine v2.1
let state = {
  authenticated: false,
  currentUser: null,
  activeMainTab: 'nexus', // 'nexus', 'indonesia', 'advanced', 'commodities', 'news'
  indicators: { all: [], indonesia: [], advanced_economies: {}, commodities: [], nexus: {} },
  news: [],
  newsTotal: 0,
  newsLimit: 30,
  newsOffset: 0,
  filterRegion: 'Semua',
  filterCategory: 'Semua',
  filterSentiment: 'Semua',
  searchQuery: '',
  calendar: [],
  briefing: null,
  chartInstance: null,
  pollingInterval: null,
  isMobile: false
};

// Theme Management (Dark / Light)
function initTheme() {
  const savedTheme = localStorage.getItem('werkudoro_theme') || 'dark';
  applyTheme(savedTheme);
}

function applyTheme(theme) {
  const html = document.documentElement;
  const sun = document.getElementById('themeIconSun');
  const moon = document.getElementById('themeIconMoon');

  if (theme === 'light') {
    html.setAttribute('data-theme', 'light');
    html.classList.remove('dark');
    if (sun) sun.classList.remove('hidden');
    if (moon) moon.classList.add('hidden');
  } else {
    html.setAttribute('data-theme', 'dark');
    html.classList.add('dark');
    if (sun) sun.classList.add('hidden');
    if (moon) moon.classList.remove('hidden');
  }

  localStorage.setItem('werkudoro_theme', theme);
  
  // Re-render chart with appropriate theme palette
  if (state.chartInstance) {
    updateChart();
  }
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  const target = current === 'dark' ? 'light' : 'dark';
  applyTheme(target);
}

// Detect User-Agent & Screen Fit Dynamically
function initUserAgentEnvironment() {
  const ua = navigator.userAgent || '';
  const isMobileUA = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua);
  const isSmallScreen = window.innerWidth <= 768;
  state.isMobile = isMobileUA || isSmallScreen;

  const deviceBadge = document.getElementById('uaDeviceBadge');
  const footerUADetect = document.getElementById('footerUADetect');

  let deviceName = 'Desktop Workstation';
  if (/iPhone/i.test(ua)) deviceName = 'Apple iPhone';
  else if (/iPad/i.test(ua)) deviceName = 'Apple iPad';
  else if (/Android/i.test(ua)) deviceName = 'Android Device';
  else if (isSmallScreen) deviceName = 'Mobile Browser';

  if (deviceBadge) deviceBadge.innerText = `${deviceName.toUpperCase()} • ACTIVE`;
  if (footerUADetect) footerUADetect.innerText = `UA: ${deviceName}`;

  if (state.isMobile) {
    document.body.classList.add('is-mobile-ua');
  } else {
    document.body.classList.remove('is-mobile-ua');
  }
}

// Clock WIB (Asia/Jakarta)
function updateClock() {
  const now = new Date();
  const timeOptions = { timeZone: 'Asia/Jakarta', hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' };
  const timeStr = now.toLocaleTimeString('id-ID', timeOptions) + ' WIB';
  const clockEl = document.getElementById('clockWIB');
  if (clockEl) clockEl.innerText = timeStr;
}
setInterval(updateClock, 1000);
updateClock();

// Tab Nav: Switch between Nexus, Indonesia, Advanced, Commodities, News
function switchMacroTab(tabId) {
  state.activeMainTab = tabId;
  const tabs = ['nexus', 'indonesia', 'advanced', 'commodities', 'news'];

  tabs.forEach(t => {
    // Desktop Tab buttons
    const deskBtn = document.getElementById(`tabNav${capitalize(t)}`);
    if (deskBtn) {
      if (t === tabId) {
        deskBtn.classList.add('active');
      } else {
        deskBtn.classList.remove('active');
      }
    }

    // Mobile Bottom items
    const mobBtn = document.getElementById(`mobNav${capitalize(t)}`);
    if (mobBtn) {
      if (t === tabId) {
        mobBtn.classList.add('active');
      } else {
        mobBtn.classList.remove('active');
      }
    }

    // View panels
    const viewEl = document.getElementById(`view${capitalize(t)}`);
    if (viewEl) {
      if (t === tabId) {
        viewEl.classList.remove('hidden');
      } else {
        viewEl.classList.add('hidden');
      }
    }
  });

  // Re-render or resize chart if switching to nexus
  if (tabId === 'nexus' && state.chartInstance) {
    setTimeout(() => {
      state.chartInstance.resize();
    }, 50);
  }

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function capitalize(s) {
  if (s === 'nexus') return 'Nexus';
  if (s === 'indonesia') return 'Indonesia';
  if (s === 'advanced') return 'Advanced';
  if (s === 'commodities') return 'Commodities';
  if (s === 'news') return 'News';
  return s.charAt(0).toUpperCase() + s.slice(1);
}

// Auth Tab in Login Modal (Username/Email vs Google SSO)
function switchAuthTab(type) {
  const form = document.getElementById('loginForm');
  const googlePanel = document.getElementById('googleAuthPanel');
  const tabUser = document.getElementById('tabAuthUser');
  const tabGoogle = document.getElementById('tabAuthGoogle');

  if (type === 'user') {
    if (form) form.classList.remove('hidden');
    if (googlePanel) googlePanel.classList.add('hidden');
    if (tabUser) {
      tabUser.className = 'py-1.5 px-2 rounded text-center transition-colors bg-[#232938] text-white font-medium';
    }
    if (tabGoogle) {
      tabGoogle.className = 'py-1.5 px-2 rounded text-center transition-colors text-[#717a8c] hover:text-white font-medium';
    }
  } else {
    if (form) form.classList.add('hidden');
    if (googlePanel) googlePanel.classList.remove('hidden');
    if (tabGoogle) {
      tabGoogle.className = 'py-1.5 px-2 rounded text-center transition-colors bg-[#232938] text-white font-medium';
    }
    if (tabUser) {
      tabUser.className = 'py-1.5 px-2 rounded text-center transition-colors text-[#717a8c] hover:text-white font-medium';
    }
  }
}

// Check Authentication Session
async function checkAuth() {
  try {
    const res = await fetch('/api/auth/check', { credentials: 'include' });
    const data = await res.json();
    if (data.authenticated) {
      state.authenticated = true;
      state.currentUser = data.username;
      showAuthenticatedUI();
      bootDashboardData();
    } else {
      state.authenticated = false;
      state.currentUser = null;
      showLoginModal();
    }
  } catch (err) {
    console.error('Auth check error:', err);
    showLoginModal();
  }
}

function showLoginModal() {
  const modal = document.getElementById('loginModal');
  const badge = document.getElementById('userBadge');
  if (modal) modal.classList.remove('hidden');
  if (badge) badge.classList.add('hidden');
  if (state.pollingInterval) {
    clearInterval(state.pollingInterval);
    state.pollingInterval = null;
  }
}

function showAuthenticatedUI() {
  const modal = document.getElementById('loginModal');
  const badge = document.getElementById('userBadge');
  const userSpan = document.getElementById('headerUsername');
  
  if (modal) modal.classList.add('hidden');
  if (badge) badge.classList.remove('hidden');
  if (userSpan) userSpan.innerText = state.currentUser || 'syant';
  
  if (window.lucide) lucide.createIcons();
}

async function handleLoginSubmit(event) {
  event.preventDefault();
  const userInput = document.getElementById('inputUsername');
  const passInput = document.getElementById('inputPassword');
  const errorAlert = document.getElementById('loginErrorAlert');
  const errorMsg = document.getElementById('loginErrorMessage');
  const btn = document.getElementById('btnLoginSubmit');
  const btnText = document.getElementById('loginBtnText');

  const identifier = userInput.value.trim();
  const password = passInput.value;

  if (errorAlert) errorAlert.classList.add('hidden');
  if (btnText) btnText.innerText = 'Mengautentikasi...';
  if (btn) btn.disabled = true;

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ identifier, password })
    });

    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      state.authenticated = true;
      state.currentUser = data.username;
      showAuthenticatedUI();
      userInput.value = '';
      passInput.value = '';
      await bootDashboardData();
    } else {
      if (errorAlert) {
        errorAlert.classList.remove('hidden');
        if (errorMsg) errorMsg.innerText = data.detail || 'Kredensial tidak sesuai.';
      }
    }
  } catch (err) {
    if (errorAlert) {
      errorAlert.classList.remove('hidden');
      if (errorMsg) errorMsg.innerText = 'Gagal terhubung ke gateway.';
    }
  } finally {
    if (btnText) btnText.innerText = 'Masuk ke Sesi';
    if (btn) btn.disabled = false;
  }
}

async function handleGoogleSSOLogin() {
  const btn = document.getElementById('btnGoogleSSO');
  if (btn) btn.disabled = true;

  try {
    const res = await fetch('/api/auth/google-sso', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email: "hermansyantoso@gmail.com" })
    });

    const data = await res.json();
    if (res.ok && data.status === 'ok') {
      state.authenticated = true;
      state.currentUser = data.username;
      showAuthenticatedUI();
      await bootDashboardData();
    }
  } catch (err) {
    console.error('Google SSO error:', err);
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function handleLogout() {
  try {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
  } catch (e) {
    console.error('Logout error:', e);
  }
  state.authenticated = false;
  state.currentUser = null;
  showLoginModal();
}

// Indicators Engine (Fetch & Multi-View Rendering)
async function fetchIndicators() {
  if (!state.authenticated) return;
  try {
    const res = await fetch('/api/indicators', { credentials: 'include' });
    if (res.status === 401) return showLoginModal();
    if (!res.ok) throw new Error('Network error');
    const data = await res.json();
    state.indicators = data;

    renderNexusView();
    renderIndonesiaView();
    renderAdvancedEconomiesView();
    renderCommoditiesView();
    renderTicker();
    updateChart();
  } catch (err) {
    console.error('Failed to load indicators:', err);
  }
}

function renderTicker() {
  const track = document.getElementById('tickerTrack');
  if (!track) return;
  const items = state.indicators.all || [];
  if (items.length === 0) return;

  const tickerHtml = items.map(ind => {
    const isUp = ind.trend === 'up';
    const isDown = ind.trend === 'down';
    const color = isUp ? 'text-emerald-400' : (isDown ? 'text-rose-400' : 'text-[#848d9f]');
    const arrow = isUp ? '▲' : (isDown ? '▼' : '■');
    const sign = ind.change_pct > 0 ? '+' : '';
    
    let valStr = ind.value.toLocaleString('id-ID');
    if (ind.unit === 'IDR') valStr = `Rp ${valStr}`;
    else if (ind.unit.startsWith('USD')) valStr = `$${valStr}`;
    else valStr = `${valStr} ${ind.unit}`;

    return `
      <span class="inline-flex items-center space-x-1.5 px-3 border-r border-[#1c2028]">
        <span class="text-[#717a8c]">${ind.name.split('(')[0].trim()}:</span>
        <span class="text-white font-semibold">${valStr}</span>
        <span class="${color} font-medium text-[10px]">
          ${arrow}${sign}${ind.change_pct}%
        </span>
      </span>
    `;
  }).join('');

  track.innerHTML = tickerHtml + tickerHtml;
}

// 1. Render Global Nexus View
function renderNexusView() {
  const nexus = state.indicators.nexus || {};
  const rateEl = document.getElementById('nexusRateSpread');
  const yieldEl = document.getElementById('nexusYieldSpread');
  const realEl = document.getElementById('nexusRealSpread');
  const fxEl = document.getElementById('nexusFxLevel');
  const vixEl = document.getElementById('nexusVixLevel');
  const stressEl = document.getElementById('nexusStressScore');
  const stressStatEl = document.getElementById('nexusStressStatus');
  const notesEl = document.getElementById('nexusNotes');

  if (rateEl && nexus.rate_spread_pct !== undefined) {
    rateEl.innerText = `+${nexus.rate_spread_pct}%`;
  }
  if (yieldEl && nexus.yield_spread_bps !== undefined) {
    yieldEl.innerText = `+${nexus.yield_spread_bps} bps`;
  }
  if (realEl && nexus.real_spread_premium !== undefined) {
    realEl.innerText = `+${nexus.real_spread_premium}%`;
  }
  if (fxEl && nexus.dxy_level && nexus.usd_idr_level) {
    fxEl.innerText = `${nexus.dxy_level.toFixed(1)} / ${nexus.usd_idr_level.toLocaleString('id-ID')}`;
  }
  if (vixEl && nexus.vix_level !== undefined) {
    vixEl.innerText = `${nexus.vix_level.toFixed(2)} pts`;
  }
  if (stressEl && nexus.macro_stress_score !== undefined) {
    stressEl.innerText = `${nexus.macro_stress_score} / 100`;
  }
  if (stressStatEl && nexus.stress_status) {
    stressStatEl.innerText = nexus.stress_status;
    if (nexus.macro_stress_score > 60) {
      stressEl.className = 'text-sm sm:text-base font-bold font-mono-numbers text-rose-500';
    } else if (nexus.macro_stress_score > 35) {
      stressEl.className = 'text-sm sm:text-base font-bold font-mono-numbers text-amber-500';
    } else {
      stressEl.className = 'text-sm sm:text-base font-bold font-mono-numbers text-emerald-500';
    }
  }

  if (notesEl && nexus.transmission_notes) {
    notesEl.innerHTML = nexus.transmission_notes.map((note, idx) => `
      <div class="flex items-start space-x-2">
        <span class="text-blue-500 font-mono-numbers font-bold text-xs">${idx + 1}.</span>
        <span class="leading-relaxed">${note}</span>
      </div>
    `).join('');
  }
}

// Component to render indicator card
function createIndicatorCardHTML(item) {
  const isUp = item.trend === 'up';
  const isDown = item.trend === 'down';
  const badgeCls = isUp ? 'badge-gain' : (isDown ? 'badge-loss' : 'badge-neutral');
  const arrow = isUp ? '▲' : (isDown ? '▼' : '■');
  const sign = item.change_pct > 0 ? '+' : '';

  let valFormatted = item.value.toLocaleString('id-ID');
  if (item.unit === 'IDR') valFormatted = `Rp ${valFormatted}`;
  else if (item.unit.startsWith('USD')) valFormatted = `$${valFormatted}`;
  else if (item.unit === 'JPY') valFormatted = `¥ ${valFormatted}`;

  return `
    <div class="fin-card p-2.5 sm:p-3 flex flex-col justify-between">
      <div>
        <div class="flex items-center justify-between text-[10px] font-mono-numbers text-[#64748b] mb-1">
          <span class="truncate max-w-[120px]">${item.category}</span>
          <span class="font-medium">${item.region.slice(0, 3).toUpperCase()}</span>
        </div>
        <div class="text-xs font-semibold line-clamp-1" title="${item.name}">${item.name}</div>
      </div>
      
      <div class="my-2">
        <div class="text-sm sm:text-base font-bold font-mono-numbers tracking-tight">${valFormatted}</div>
        <div class="text-[10px] text-[#64748b] font-mono-numbers">${item.unit}</div>
      </div>

      <div class="flex items-center justify-between pt-1.5 border-t border-[#1a1e27] text-[10px] font-mono-numbers">
        <span class="px-1.5 py-0.5 rounded ${badgeCls}">
          ${arrow} ${sign}${item.change_pct}%
        </span>
        <span class="text-[#64748b] truncate max-w-[90px]" title="${item.source}">${item.source.split('(')[0]}</span>
      </div>
    </div>
  `;
}

// 2. Render Indonesia Deep View
function renderIndonesiaView() {
  const container = document.getElementById('gridIndoIndicators');
  if (!container) return;
  const list = state.indicators.indonesia || [];

  if (list.length === 0) {
    container.innerHTML = '<div class="col-span-full text-center text-[#555d6e] text-xs py-4 font-mono-numbers">Memuat data indikator Indonesia...</div>';
    return;
  }
  container.innerHTML = list.map(createIndicatorCardHTML).join('');
}

// 3. Render Advanced Economies View (US, Euro, Japan, UK, China)
function renderAdvancedEconomiesView() {
  const adv = state.indicators.advanced_economies || {};

  const gridUS = document.getElementById('gridUSIndicators');
  const gridEuro = document.getElementById('gridEuroIndicators');
  const gridJapan = document.getElementById('gridJapanIndicators');
  const gridUK = document.getElementById('gridUKIndicators');
  const gridChina = document.getElementById('gridChinaIndicators');

  if (gridUS && adv.us) gridUS.innerHTML = adv.us.map(createIndicatorCardHTML).join('');
  if (gridEuro && adv.eurozone) gridEuro.innerHTML = adv.eurozone.map(createIndicatorCardHTML).join('');
  if (gridJapan && adv.japan) gridJapan.innerHTML = adv.japan.map(createIndicatorCardHTML).join('');
  if (gridUK && adv.uk) gridUK.innerHTML = adv.uk.map(createIndicatorCardHTML).join('');
  if (gridChina && adv.china) gridChina.innerHTML = adv.china.map(createIndicatorCardHTML).join('');
}

// 4. Render Commodities View
function renderCommoditiesView() {
  const container = document.getElementById('gridCommodityIndicators');
  if (!container) return;
  const list = state.indicators.commodities || [];

  if (list.length === 0) {
    container.innerHTML = '<div class="col-span-full text-center text-[#555d6e] text-xs py-4 font-mono-numbers">Memuat data komoditas global...</div>';
    return;
  }
  container.innerHTML = list.map(createIndicatorCardHTML).join('');
}

// Chart.js Comparison Chart
function updateChart() {
  const ctx = document.getElementById('macroComparisonChart');
  if (!ctx) return;

  const items = state.indicators.all || [];
  const biRate = items.find(i => i.key === 'BI_RATE')?.value || 6.00;
  const fedRate = items.find(i => i.key === 'FED_FUNDS_RATE')?.value || 4.50;
  const ecbRate = items.find(i => i.key === 'ECB_RATE')?.value || 3.25;
  const bojRate = items.find(i => i.key === 'BOJ_RATE')?.value || 0.25;
  const sbn10y = items.find(i => i.key === 'SBN_10Y')?.value || 6.85;
  const us10y = items.find(i => i.key === 'US_10Y')?.value || 5.18;

  if (state.chartInstance) {
    state.chartInstance.destroy();
  }

  const isLight = document.documentElement.getAttribute('data-theme') === 'light';
  const gridColor = isLight ? 'rgba(0, 0, 0, 0.05)' : 'rgba(255, 255, 255, 0.04)';
  const textColor = isLight ? '#64748b' : '#717a8c';

  state.chartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['BI-Rate (ID)', 'Fed Rate (US)', 'ECB Rate (EU)', 'BoJ Rate (JP)', 'SBN 10Y Yield', 'US 10Y Yield'],
      datasets: [{
        label: 'Nilai Acuan (%)',
        data: [biRate, fedRate, ecbRate, bojRate, sbn10y, us10y],
        backgroundColor: [
          '#2563eb', // Blue - BI Rate
          '#4f46e5', // Indigo - Fed Rate
          '#0891b2', // Cyan - ECB Rate
          '#7c3aed', // Purple - BoJ Rate
          '#059669', // Emerald - SBN 10Y
          '#d97706'  // Amber - US 10Y
        ],
        borderRadius: 3,
        borderWidth: 0,
        barPercentage: 0.65
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: isLight ? '#ffffff' : '#161920',
          titleColor: isLight ? '#0f172a' : '#e5e7eb',
          bodyColor: isLight ? '#475569' : '#9ca3af',
          borderColor: isLight ? '#cbd5e1' : '#262c38',
          borderWidth: 1,
          padding: 8,
          bodyFont: { family: 'JetBrains Mono', size: 11 },
          titleFont: { family: 'Inter', size: 11 },
          callbacks: {
            label: context => ` ${context.parsed.y.toFixed(2)} %`
          }
        }
      },
      scales: {
        x: {
          grid: { color: gridColor },
          ticks: { color: textColor, font: { size: 10, family: 'JetBrains Mono' } }
        },
        y: {
          grid: { color: gridColor },
          ticks: {
            color: textColor,
            font: { size: 10, family: 'JetBrains Mono' },
            callback: value => value + ' %'
          }
        }
      }
    }
  });
}

// Executive Briefing
async function fetchBriefing() {
  if (!state.authenticated) return;
  try {
    const res = await fetch('/api/briefing', { credentials: 'include' });
    if (res.status === 401) return showLoginModal();
    if (!res.ok) return;
    const data = await res.json();
    if (data.briefing) {
      state.briefing = data.briefing;
      renderBriefing();
    }
  } catch (err) {
    console.error('Failed to load briefing:', err);
  }
}

function renderBriefing() {
  const b = state.briefing;
  if (!b) return;

  const hl = document.getElementById('briefingHeadline');
  const bi = document.getElementById('briefingIndo');
  const bg = document.getElementById('briefingGlobal');
  const br = document.getElementById('briefingRisks');
  const bt = document.getElementById('briefingTime');
  const ms = document.getElementById('marketSentimentBadge');

  if (hl) hl.innerText = b.headline;
  if (bi) bi.innerHTML = b.summary_indo.replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>').replace(/\n/g, '<br/>');
  if (bg) bg.innerHTML = b.summary_global.replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>').replace(/\n/g, '<br/>');
  if (br) br.innerText = b.key_risks;
  if (ms) ms.innerText = b.market_sentiment;

  if (bt && b.updated_at) {
    const d = new Date(b.updated_at);
    bt.innerText = 'Diperbarui: ' + d.toLocaleTimeString('id-ID') + ' WIB';
  }
}

// Calendar
async function fetchCalendar() {
  if (!state.authenticated) return;
  try {
    const res = await fetch('/api/calendar', { credentials: 'include' });
    if (res.status === 401) return showLoginModal();
    if (!res.ok) return;
    const data = await res.json();
    state.calendar = data.events || [];
    renderCalendar();
  } catch (err) {
    console.error('Failed to load calendar:', err);
  }
}

function renderCalendar() {
  const list = document.getElementById('calendarList');
  if (!list) return;

  if (state.calendar.length === 0) {
    list.innerHTML = '<div class="text-[#555d6e] text-xs py-4 text-center font-mono-numbers">Tidak ada event ekonomi mendatang.</div>';
    return;
  }

  list.innerHTML = state.calendar.map(ev => {
    const isIndo = ev.region === 'Indonesia';
    const tag = isIndo ? 'ID' : 'GLB';

    return `
      <div class="p-2 rounded fin-subcard space-y-1 transition-colors">
        <div class="flex items-center justify-between text-[11px] gap-1">
          <span class="font-medium line-clamp-1">${ev.event_name}</span>
          <span class="text-[9px] font-mono-numbers px-1 rounded badge-neutral">${tag}</span>
        </div>
        <div class="flex items-center justify-between text-[10px] text-[var(--text-muted)] font-mono-numbers">
          <span>${ev.event_date} | ${ev.time_wib}</span>
          <span class="font-semibold text-[var(--text-primary)]">Fcst: ${ev.forecast}</span>
        </div>
      </div>
    `;
  }).join('');
}

// News Wire Stream
async function fetchNews(append = false) {
  if (!state.authenticated) return;
  try {
    const params = new URLSearchParams();
    if (state.filterRegion !== 'Semua') params.append('region', state.filterRegion);
    if (state.filterCategory !== 'Semua') params.append('category', state.filterCategory);
    if (state.filterSentiment !== 'Semua') params.append('sentiment', state.filterSentiment);
    if (state.searchQuery.trim()) params.append('q', state.searchQuery.trim());
    params.append('limit', state.newsLimit);
    params.append('offset', state.newsOffset);

    const res = await fetch(`/api/news?${params.toString()}`, { credentials: 'include' });
    if (res.status === 401) return showLoginModal();
    if (!res.ok) throw new Error('Failed to fetch news');
    const data = await res.json();

    state.newsTotal = data.total;
    if (append) {
      state.news = state.news.concat(data.items);
    } else {
      state.news = data.items;
    }

    renderNews();
  } catch (err) {
    console.error('Failed to load news:', err);
  }
}

function renderNews() {
  const grid = document.getElementById('newsGrid');
  const totalBadge = document.getElementById('newsTotalBadge');
  const btnMore = document.getElementById('btnLoadMore');

  if (totalBadge) totalBadge.innerText = `${state.newsTotal} Berita`;
  if (!grid) return;

  if (state.news.length === 0) {
    grid.innerHTML = `
      <div class="py-8 text-center text-[#555d6e] text-xs font-mono-numbers">
        Tidak ada berita makroekonomi untuk filter ini.
      </div>
    `;
    if (btnMore) btnMore.classList.add('hidden');
    return;
  }

  grid.innerHTML = state.news.map(item => {
    const isIndo = item.region === 'Indonesia';
    const tag = isIndo ? 'ID' : 'GLB';

    let sentColor = 'text-[#717a8c]';
    if (item.sentiment === 'Hawkish') sentColor = 'text-red-400';
    else if (item.sentiment === 'Dovish') sentColor = 'text-emerald-400';
    else if (item.sentiment === 'Bullish') sentColor = 'text-emerald-400';
    else if (item.sentiment === 'Bearish') sentColor = 'text-red-400';

    const tagsArr = item.tags ? item.tags.split(',').filter(Boolean) : [];
    const tagsHtml = tagsArr.map(t => `<span class="text-[10px] text-[#555d6e] font-mono-numbers mr-1.5">#${t}</span>`).join('');

    return `
      <article class="py-2.5 flex flex-col md:flex-row md:items-baseline justify-between gap-2 group hover:bg-[var(--bg-hover)] px-2 rounded transition-colors border-b border-[var(--border-subtle)] last:border-0">
        <div class="space-y-1 flex-1">
          <div class="flex items-center space-x-2 text-[10px] font-mono-numbers">
            <span class="px-1.5 py-0.2 rounded badge-neutral font-medium">${tag}</span>
            <span class="font-medium">${item.source}</span>
            <span class="text-[var(--text-dim)]">•</span>
            <span>${item.category}</span>
            <span class="text-[var(--text-dim)]">•</span>
            <span class="${sentColor} font-semibold">${item.sentiment}</span>
          </div>

          <h5 class="text-xs font-semibold group-hover:text-blue-500 transition-colors leading-snug">
            <a href="${item.link}" target="_blank" rel="noopener noreferrer" class="hover:underline inline-flex items-center">
              <span>${item.title}</span>
              <i data-lucide="external-link" class="w-3 h-3 ml-1 text-[var(--text-dim)] group-hover:text-blue-500"></i>
            </a>
          </h5>

          <p class="text-[11px] text-[var(--text-secondary)] leading-relaxed line-clamp-2">
            ${item.summary || 'Klik tautan untuk membaca analisis makroekonomi lengkap.'}
          </p>

          <div class="pt-0.5">
            ${tagsHtml}
          </div>
        </div>

        <div class="flex-shrink-0 text-right text-[10px] font-mono-numbers text-[var(--text-muted)] whitespace-nowrap pl-2">
          ${item.published_at.slice(0, 16).replace('T', ' ')}
        </div>
      </article>
    `;
  }).join('');

  if (window.lucide) lucide.createIcons();

  if (btnMore) {
    if (state.news.length < state.newsTotal) {
      btnMore.classList.remove('hidden');
    } else {
      btnMore.classList.add('hidden');
    }
  }
}

function filterNewsRegion(reg) {
  state.filterRegion = reg;
  state.newsOffset = 0;
  
  ['Semua', 'Indonesia', 'Negara Maju'].forEach(r => {
    const id = r === 'Semua' ? 'pillRegAll' : (r === 'Indonesia' ? 'pillRegID' : 'pillRegAdv');
    const btn = document.getElementById(id);
    if (btn) {
      if (r === reg) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    }
  });

  fetchNews();
}

function toggleMobileSearch() {
  const row = document.getElementById('mobileSearchRow');
  if (row) {
    row.classList.toggle('hidden');
    if (!row.classList.contains('hidden')) {
      const input = document.getElementById('searchInputMobile');
      if (input) input.focus();
    }
  }
}

function handleSearchInput(e) {
  clearTimeout(searchDebounce);
  const val = e.target.value;
  
  // Sync both inputs
  const d = document.getElementById('searchInputDesktop');
  const m = document.getElementById('searchInputMobile');
  if (d && d !== e.target) d.value = val;
  if (m && m !== e.target) m.value = val;

  searchDebounce = setTimeout(() => {
    state.searchQuery = val;
    state.newsOffset = 0;
    fetchNews();
  }, 300);
}

function applyFilters() {
  const cat = document.getElementById('selectCategory');
  const sent = document.getElementById('selectSentiment');
  if (cat) state.filterCategory = cat.value;
  if (sent) state.filterSentiment = sent.value;
  state.newsOffset = 0;
  fetchNews();
}

function loadMoreNews() {
  state.newsOffset += state.newsLimit;
  fetchNews(true);
}

// Search
let searchDebounce;
const searchInput = document.getElementById('searchInput');
if (searchInput) {
  searchInput.addEventListener('input', (e) => {
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(() => {
      state.searchQuery = e.target.value;
      state.newsOffset = 0;
      fetchNews();
    }, 300);
  });
}

// Manual Refresh
async function manualRefresh() {
  if (!state.authenticated) return;
  const icon = document.getElementById('refreshIcon');
  if (icon) icon.classList.add('animate-spin');

  try {
    await fetch('/api/refresh', { method: 'POST', credentials: 'include' });
    setTimeout(async () => {
      await Promise.all([
        fetchIndicators(),
        fetchBriefing(),
        fetchCalendar(),
        fetchNews()
      ]);
      if (icon) icon.classList.remove('animate-spin');
    }, 1500);
  } catch (err) {
    console.error('Refresh trigger error:', err);
    if (icon) icon.classList.remove('animate-spin');
  }
}

// Initial Boot Data
async function bootDashboardData() {
  await Promise.all([
    fetchIndicators(),
    fetchBriefing(),
    fetchCalendar(),
    fetchNews()
  ]);

  if (!state.pollingInterval) {
    state.pollingInterval = setInterval(async () => {
      if (state.authenticated) {
        await Promise.all([
          fetchIndicators(),
          fetchBriefing(),
          fetchCalendar()
        ]);
      }
    }, 45000);
  }
}

// Startup
window.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initUserAgentEnvironment();
  checkAuth();
});

window.addEventListener('resize', () => {
  initUserAgentEnvironment();
});
