// Kroniclez Digital TV Menu Board Client Engine
let currentScreenId = 1;
let currentStoreId = 1;
let autoCycleEnabled = false;
let autoCycleTimer = null;
let autoCycleIntervalSeconds = 30;
let pollTimer = null;

// Parse URL Parameters
function getUrlParams() {
    const params = new URLSearchParams(window.location.search);
    const screen = parseInt(params.get('screen') || (window.__INITIAL_SCREEN_ID__ || 1));
    const store = parseInt(params.get('store') || 1);
    const auto = params.get('auto') === '1' || params.get('auto') === 'true';
    return { screen, store, auto };
}

// Format Canadian Dollars
function formatCAD(val) {
    const num = parseFloat(val) || 0.0;
    return `$${num.toFixed(2)}`;
}

// Standard Row Renderer (Screens 1 & 2)
function renderRowHtml(it, showStrainBadge = false) {
    let badge = '';
    if (showStrainBadge) {
        const s = (it.species || 'HYBRID').toUpperCase();
        if (s.includes('INDICA')) badge = '<span class="badge-strain b-indica">IND</span>';
        else if (s.includes('SATIVA')) badge = '<span class="badge-strain b-sativa">SAT</span>';
        else badge = '<span class="badge-strain b-hybrid">HYB</span>';
    }

    const pName = it.product_name || '';
    const thc = it.thc || '28%';

    let priceHtml = '';
    if (it.is_sale && it.old_price) {
        priceHtml = `
            <span class="sale">${formatCAD(it.price)}</span>
            <span class="old">${formatCAD(it.old_price)}</span>
        `;
    } else {
        priceHtml = `<span class="regular">${formatCAD(it.price)}</span>`;
    }

    return `
        <div class="p-row">
            <div class="p-name" title="${pName}">${badge}${pName}</div>
            <div class="p-thc">${thc}</div>
            <div class="p-price">${priceHtml}</div>
        </div>
    `;
}

// Soft Chews 5-Column Row Renderer (Screen 3)
function renderSoftRow(it) {
    const spec = (it.species || 'HYBRID').toUpperCase();
    let metaClass = 'meta-hybrid';
    let metaText = 'Hybrid';
    if (spec.includes('INDICA')) { metaClass = 'meta-indica'; metaText = 'Indica'; }
    else if (spec.includes('SATIVA')) { metaClass = 'meta-sativa'; metaText = 'Sativa'; }

    let priceHtml = '';
    if (it.is_sale && it.old_price) {
        priceHtml = `
            <span class="sale">${formatCAD(it.price)}</span>
            <span class="old">${formatCAD(it.old_price)}</span>
        `;
    } else {
        priceHtml = `<span class="regular">${formatCAD(it.price)}</span>`;
    }

    return `
        <div class="soft-row">
            <div class="soft-name" title="${it.product_name}">${it.product_name}</div>
            <div class="soft-meta ${metaClass}">${metaText}</div>
            <div class="soft-thc">${it.thc || '10mg'}</div>
            <div class="soft-cbd">${it.cbd || '—'}</div>
            <div class="p-price">${priceHtml}</div>
        </div>
    `;
}

// Soft Card Panel Renderer (Screen 3)
function renderSoftCard(cardKey, dataObj) {
    const sec = dataObj[cardKey];
    if (!sec || !sec.items || sec.items.length === 0) return '';

    const subHtml = sec.subtitle ? `<div class="card-head-sub">${sec.subtitle}</div>` : '';
    return `
        <div class="soft-card card-${sec.color || 'gold'}">
            <div class="card-head-title">${sec.title}</div>
            ${subHtml}
            <div class="table-header-soft">
                <div>PRODUCT</div>
                <div style="text-align:center;">STRAIN</div>
                <div style="text-align:center;">THC</div>
                <div style="text-align:center;">CBD</div>
                <div style="text-align:right;">PRICE</div>
            </div>
            ${sec.items.map(it => renderSoftRow(it)).join('')}
        </div>
    `;
}

// Main Render Dispatcher
function renderMenuData(res) {
    if (!res || !res.structured) return;
    const mount = document.getElementById('menuMount');
    if (!mount) return;

    const screen = res.screen || currentScreenId;

    if (screen === 1) {
        // SCREEN 1: PRE-ROLLS (Indica, Hybrid, Sativa, Infused)
        const d = res.structured;
        
        let infusedHtml = '';
        const infIndica = d.infused.indica_items || [];
        const infHybrid = d.infused.hybrid_items || [];
        const infSativa = d.infused.sativa_items || [];

        if (infIndica.length) {
            infusedHtml += `<div class="subhead indica"><span style="color:#4CAF50;">Indica Infused</span> <span style="font-size:11px; color:#888;">${infIndica.length} SKUs</span></div>`;
            infusedHtml += infIndica.map(it => renderRowHtml(it, false)).join('');
        }
        if (infHybrid.length) {
            infusedHtml += `<div class="subhead hybrid"><span style="color:#FFC107;">Hybrid Infused</span> <span style="font-size:11px; color:#888;">${infHybrid.length} SKUs</span></div>`;
            infusedHtml += infHybrid.map(it => renderRowHtml(it, false)).join('');
        }
        if (infSativa.length) {
            infusedHtml += `<div class="subhead sativa"><span style="color:#FF6666;">Sativa Infused</span> <span style="font-size:11px; color:#888;">${infSativa.length} SKUs</span></div>`;
            infusedHtml += infSativa.map(it => renderRowHtml(it, false)).join('');
        }

        mount.innerHTML = `
            <div class="container-prerolls">
                <!-- INDICA PRE-ROLLS -->
                <div class="panel">
                    <div class="title indica">INDICA</div>
                    <div class="table-header"><div class="h-name">Strain / Product</div><div class="h-thc">THC</div><div class="h-price">Price</div></div>
                    ${(d.indica.items || []).map(it => renderRowHtml(it, false)).join('') || '<div style="color:#666; font-size:12px; padding:15px; text-align:center;">No Indica Pre-Rolls</div>'}
                </div>

                <!-- HYBRID PRE-ROLLS -->
                <div class="panel">
                    <div class="title hybrid">HYBRID</div>
                    <div class="table-header"><div class="h-name">Strain / Product</div><div class="h-thc">THC</div><div class="h-price">Price</div></div>
                    ${(d.hybrid.items || []).map(it => renderRowHtml(it, false)).join('') || '<div style="color:#666; font-size:12px; padding:15px; text-align:center;">No Hybrid Pre-Rolls</div>'}
                </div>

                <!-- SATIVA PRE-ROLLS -->
                <div class="panel">
                    <div class="title sativa">SATIVA</div>
                    <div class="table-header"><div class="h-name">Strain / Product</div><div class="h-thc">THC</div><div class="h-price">Price</div></div>
                    ${(d.sativa.items || []).map(it => renderRowHtml(it, false)).join('') || '<div style="color:#666; font-size:12px; padding:15px; text-align:center;">No Sativa Pre-Rolls</div>'}
                </div>

                <!-- INFUSED PRE-ROLLS -->
                <div class="panel">
                    <div class="title infused">INFUSED PRE-ROLLS</div>
                    <div class="table-header"><div class="h-name">Strain / Product</div><div class="h-thc">THC</div><div class="h-price">Price</div></div>
                    ${infusedHtml || '<div style="color:#666; font-size:12px; padding:15px; text-align:center;">No Infused Pre-Rolls</div>'}
                </div>
            </div>
        `;

    } else if (screen === 2) {
        // SCREEN 2: FLOWER & VAPES (Dried on top -> Milled below)
        const f = res.structured.flower;
        const v = res.structured.vapes;

        // Column 1: Indica Dried + Milled & Hybrid Dried + Milled
        let col1Html = '';
        const indTotal = (f.indica_dried.items.length + f.indica_milled.items.length);
        if (indTotal > 0) {
            col1Html += `<div class="subhead indica"><span style="color:#4CAF50;">Indica Dried Flower</span> <span style="font-size:11px; color:#888;">${f.indica_dried.items.length} SKUs</span></div>`;
            col1Html += f.indica_dried.items.map(it => renderRowHtml(it, false)).join('');
            if (f.indica_milled.items.length) {
                col1Html += `<div style="font-size:10.5px; font-weight:800; color:#a3e635; margin:6px 0 2px 2px; text-transform:uppercase; letter-spacing:0.5px;"><i class="bi bi-scissors"></i> Indica Milled (${f.indica_milled.items.length} SKUs)</div>`;
                col1Html += f.indica_milled.items.map(it => renderRowHtml(it, false)).join('');
            }
        }

        const hybTotal = (f.hybrid_dried.items.length + f.hybrid_milled.items.length);
        if (hybTotal > 0) {
            col1Html += `<div class="subhead hybrid" style="margin-top:10px;"><span style="color:#FFC107;">Hybrid Dried Flower</span> <span style="font-size:11px; color:#888;">${f.hybrid_dried.items.length} SKUs</span></div>`;
            col1Html += f.hybrid_dried.items.map(it => renderRowHtml(it, false)).join('');
            if (f.hybrid_milled.items.length) {
                col1Html += `<div style="font-size:10.5px; font-weight:800; color:#a3e635; margin:6px 0 2px 2px; text-transform:uppercase; letter-spacing:0.5px;"><i class="bi bi-scissors"></i> Hybrid Milled (${f.hybrid_milled.items.length} SKUs)</div>`;
                col1Html += f.hybrid_milled.items.map(it => renderRowHtml(it, false)).join('');
            }
        }

        // Column 2: Sativa Dried + Milled
        let col2Html = '';
        const satTotal = (f.sativa_dried.items.length + f.sativa_milled.items.length);
        if (satTotal > 0) {
            col2Html += `<div class="subhead sativa"><span style="color:#FF6666;">Sativa Dried Flower</span> <span style="font-size:11px; color:#888;">${f.sativa_dried.items.length} SKUs</span></div>`;
            col2Html += f.sativa_dried.items.map(it => renderRowHtml(it, false)).join('');
            if (f.sativa_milled.items.length) {
                col2Html += `<div style="font-size:10.5px; font-weight:800; color:#a3e635; margin:6px 0 2px 2px; text-transform:uppercase; letter-spacing:0.5px;"><i class="bi bi-scissors"></i> Sativa Milled (${f.sativa_milled.items.length} SKUs)</div>`;
                col2Html += f.sativa_milled.items.map(it => renderRowHtml(it, false)).join('');
            }
        }

        // Column 3: 510 Carts (Indica on top -> Hybrid below)
        let col3Html = '';
        if (v.vapes_510_indica.items.length) {
            col3Html += `<div class="subhead indica"><span style="color:#4CAF50;">510 Indica</span> <span style="font-size:11px; color:#888;">${v.vapes_510_indica.items.length} SKUs</span></div>`;
            col3Html += v.vapes_510_indica.items.map(it => renderRowHtml(it, true)).join('');
        }
        if (v.vapes_510_hybrid.items.length) {
            col3Html += `<div class="subhead hybrid" style="margin-top:10px;"><span style="color:#FFC107;">510 Hybrid</span> <span style="font-size:11px; color:#888;">${v.vapes_510_hybrid.items.length} SKUs</span></div>`;
            col3Html += v.vapes_510_hybrid.items.map(it => renderRowHtml(it, true)).join('');
        }

        // Column 4: 510 Sativa & All-in-One Disposables
        let col4Html = '';
        if (v.vapes_510_sativa.items.length) {
            col4Html += `<div class="subhead sativa"><span style="color:#FF6666;">510 Sativa</span> <span style="font-size:11px; color:#888;">${v.vapes_510_sativa.items.length} SKUs</span></div>`;
            col4Html += v.vapes_510_sativa.items.map(it => renderRowHtml(it, true)).join('');
        }
        const dispTotal = (v.disp_indica.items.length + v.disp_hybrid.items.length + v.disp_sativa.items.length);
        if (dispTotal > 0) {
            col4Html += `<div class="subhead disposable" style="margin-top:10px;"><span style="color:#f472b6;">All-in-One Disposables</span> <span style="font-size:11px; color:#888;">${dispTotal} SKUs</span></div>`;
            col4Html += v.disp_indica.items.map(it => renderRowHtml(it, true)).join('');
            col4Html += v.disp_hybrid.items.map(it => renderRowHtml(it, true)).join('');
            col4Html += v.disp_sativa.items.map(it => renderRowHtml(it, true)).join('');
        }

        mount.innerHTML = `
            <div class="container-vapes-flower">
                <!-- COL 1: INDICA & HYBRID FLOWER -->
                <div class="panel">
                    <div class="title indica">INDICA & HYBRID FLOWER</div>
                    <div class="table-header"><div class="h-name">Strain / Product</div><div class="h-thc">THC/CBD</div><div class="h-price">Price</div></div>
                    ${col1Html || '<div style="color:#666; font-size:12px; padding:15px; text-align:center;">No Flower</div>'}
                </div>

                <!-- COL 2: SATIVA FLOWER -->
                <div class="panel">
                    <div class="title sativa">SATIVA FLOWER</div>
                    <div class="table-header"><div class="h-name">Strain / Product</div><div class="h-thc">THC/CBD</div><div class="h-price">Price</div></div>
                    ${col2Html || '<div style="color:#666; font-size:12px; padding:15px; text-align:center;">No Flower</div>'}
                </div>

                <!-- COL 3: 510 CARTS -->
                <div class="panel">
                    <div class="title vapes510">510 CARTRIDGES</div>
                    <div class="table-header"><div class="h-name">Product</div><div class="h-thc">THC/CBD</div><div class="h-price">Price</div></div>
                    ${col3Html || '<div style="color:#666; font-size:12px; padding:15px; text-align:center;">No 510 Carts</div>'}
                </div>

                <!-- COL 4: 510 SATIVA & DISPOSABLES -->
                <div class="panel">
                    <div class="title disposable">VAPES & DISPOSABLES</div>
                    <div class="table-header"><div class="h-name">Product</div><div class="h-thc">THC/CBD</div><div class="h-price">Price</div></div>
                    ${col4Html || '<div style="color:#666; font-size:12px; padding:15px; text-align:center;">No Disposables</div>'}
                </div>
            </div>
        `;

    } else {
        // SCREEN 3: SOFT CHEWS, DRINKS, CONCENTRATES & WELLNESS
        const d = res.structured;
        
        mount.innerHTML = `
            <div class="container-softchews">
                <!-- LEFT COLUMN: CONCENTRATES & BEVERAGES -->
                <div class="column-deck">
                    ${renderSoftCard('concentrates', d)}
                    ${renderSoftCard('beverages', d)}
                </div>

                <!-- CENTER COLUMN: INDICA & HYBRID GUMMIES + CHOCOLATES -->
                <div class="column-deck">
                    ${renderSoftCard('gummies_ind_hyb', d)}
                    ${renderSoftCard('chocolates', d)}
                </div>

                <!-- RIGHT COLUMN: SATIVA GUMMIES + WELLNESS -->
                <div class="column-deck">
                    ${renderSoftCard('gummies_sativa', d)}
                    ${renderSoftCard('wellness', d)}
                </div>
            </div>
        `;
    }

    updateNavPills(screen);
    updateSyncStatus(res.updated_at);
}

// Fetch live menu from API
function fetchLiveMenu(screenId, storeId) {
    const sId = screenId || currentScreenId;
    const stId = storeId || currentStoreId;

    fetch(`/api/tv-menu?screen=${sId}&store=${stId}`)
        .then(r => r.json())
        .then(res => {
            if (res.success) {
                renderMenuData(res);
            }
        })
        .catch(err => {
            console.error("TV Menu fetch error:", err);
        });
}

// Switch Screen with Animation
function switchScreen(screenNum) {
    currentScreenId = screenNum;
    const newUrl = `?screen=${currentScreenId}&store=${currentStoreId}${autoCycleEnabled ? '&auto=1' : ''}`;
    window.history.replaceState({}, '', newUrl);
    fetchLiveMenu(currentScreenId, currentStoreId);
}

// Update Active Button in Floating Nav
function updateNavPills(screen) {
    const btn1 = document.getElementById('nav-btn-screen1');
    const btn2 = document.getElementById('nav-btn-screen2');
    const btn3 = document.getElementById('nav-btn-screen3');
    const btnAuto = document.getElementById('nav-btn-auto');

    if (btn1) btn1.className = `nav-link-btn ${screen === 1 ? 'active' : ''}`;
    if (btn2) btn2.className = `nav-link-btn ${screen === 2 ? 'active' : ''}`;
    if (btn3) btn3.className = `nav-link-btn ${screen === 3 ? 'active' : ''}`;
    if (btnAuto) {
        btnAuto.className = `nav-link-btn ${autoCycleEnabled ? 'auto-active' : ''}`;
        btnAuto.title = autoCycleEnabled ? 'Auto-Cycle ON (Cycling every 30s)' : 'Auto-Cycle OFF (Press A)';
    }
}

function updateSyncStatus(timestamp) {
    const el = document.getElementById('tv-sync-time');
    if (el && timestamp) {
        el.textContent = `TENDY LIVE • ${timestamp}`;
    }
}

// Toggle Fullscreen
function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(err => console.log(err));
    } else {
        if (document.exitFullscreen) document.exitFullscreen();
    }
}

// Toggle Auto-Cycle Rotation Mode
function toggleAutoCycle() {
    autoCycleEnabled = !autoCycleEnabled;
    if (autoCycleEnabled) {
        startAutoCycle();
    } else {
        clearInterval(autoCycleTimer);
    }
    updateNavPills(currentScreenId);
}

function startAutoCycle() {
    clearInterval(autoCycleTimer);
    autoCycleTimer = setInterval(() => {
        let nextScreen = currentScreenId + 1;
        if (nextScreen > 3) nextScreen = 1;
        switchScreen(nextScreen);
    }, autoCycleIntervalSeconds * 1000);
}

// Auto-hide navigation pill on idle
let idleTimer;
function showNav() {
    const el = document.getElementById('floatingNav');
    if (el) el.classList.remove('hidden');
    clearTimeout(idleTimer);
    idleTimer = setTimeout(() => {
        if (el) el.classList.add('hidden');
    }, 3500);
}

// Keyboard shortcuts for TV Remotes & Dispensary Staff
window.addEventListener('keydown', (e) => {
    if (e.key === '1') switchScreen(1);
    if (e.key === '2') switchScreen(2);
    if (e.key === '3') switchScreen(3);
    if (e.key.toLowerCase() === 'f') toggleFullscreen();
    if (e.key.toLowerCase() === 'a') toggleAutoCycle();
    if (e.key.toLowerCase() === 'r') fetchLiveMenu(currentScreenId, currentStoreId);
});

window.addEventListener('mousemove', showNav);
window.addEventListener('touchstart', showNav);

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
    const params = getUrlParams();
    currentScreenId = params.screen;
    currentStoreId = params.store;
    autoCycleEnabled = params.auto;

    showNav();

    // 1. If preloaded state exists and has products, render immediately
    if (window.__INITIAL_MENU_DATA__ && window.__INITIAL_MENU_DATA__.success && window.__INITIAL_MENU_DATA__.total_in_stock > 0) {
        renderMenuData(window.__INITIAL_MENU_DATA__);
    } else {
        fetchLiveMenu(currentScreenId, currentStoreId);
    }

    if (autoCycleEnabled) {
        startAutoCycle();
    }

    // Auto-poll Tendy inventory every 25 seconds in background
    pollTimer = setInterval(() => {
        fetchLiveMenu(currentScreenId, currentStoreId);
    }, 25000);
});
