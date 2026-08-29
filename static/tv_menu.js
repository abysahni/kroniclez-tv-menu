// Kroniclez Dedicated Single-Screen Digital TV Menu Board Client Engine
let currentScreenId = 1;
let currentStoreId = 1;
let pollTimer = null;

// Parse URL Parameters / Dedicated Screen Routes
function getUrlParams() {
    const params = new URLSearchParams(window.location.search);
    const path = window.location.pathname;
    
    let screen = parseInt(window.__INITIAL_SCREEN_ID__ || 1);
    if (path === '/tv1' || path === '/screen1') screen = 1;
    else if (path === '/tv2' || path === '/screen2') screen = 2;
    else if (path === '/tv3' || path === '/screen3') screen = 3;
    else if (params.has('screen')) screen = parseInt(params.get('screen') || 1);

    const store = parseInt(params.get('store') || 1);
    return { screen, store };
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
    
    let tagBadge = '';
    if (it.tag === 'STAFF PICK') {
        tagBadge = '<span class="badge-staff-pick">👑 STAFF PICK</span>';
    } else if (it.tag === 'FEATURED' || (it.is_sale && it.old_price)) {
        tagBadge = '<span class="badge-featured">⭐ FEATURED</span>';
    }

    let stockBadge = '';
    const stockNum = parseInt(it.stock, 10);
    if (stockNum > 0 && stockNum <= 3) {
        stockBadge = `<span class="badge-low-stock">⚠️ ${stockNum === 1 ? 'Last 1 Left!' : `Only ${stockNum} Left!`}</span>`;
    }

    let priceHtml = '';
    if (it.is_sale && it.old_price) {
        priceHtml = `
            <span class="sale">${formatCAD(it.price)}</span>
            <span class="old">${formatCAD(it.old_price)}</span>
        `;
    } else {
        priceHtml = `<span class="regular">${formatCAD(it.price)}</span>`;
    }

    const isFeatured = (it.tag === 'FEATURED' || (it.is_sale && it.old_price));
    const isLowStock = (!isFeatured && stockNum > 0 && stockNum <= 3);

    let rowClass = '';
    if (isFeatured) rowClass = 'row-featured';
    else if (isLowStock) rowClass = 'row-low-stock';

    return `
        <div class="p-row ${rowClass}">
            <div class="p-name">${badge}${pName}${tagBadge}${stockBadge}</div>
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

    let tagBadge = '';
    if (it.tag === 'STAFF PICK') {
        tagBadge = '<span class="badge-staff-pick">👑 STAFF PICK</span>';
    } else if (it.tag === 'FEATURED' || (it.is_sale && it.old_price)) {
        tagBadge = '<span class="badge-featured">⭐ FEATURED</span>';
    }

    let stockBadge = '';
    const stockNum = parseInt(it.stock, 10);
    if (stockNum > 0 && stockNum <= 3) {
        stockBadge = `<span class="badge-low-stock">⚠️ ${stockNum === 1 ? 'Last 1 Left!' : `Only ${stockNum} Left!`}</span>`;
    }

    // Functional Cannabinoid Badge (Option 2)
    let funcBadge = '';
    const pNameLow = (it.product_name || '').toLowerCase();
    if (pNameLow.includes('cbn')) {
        funcBadge = '<span class="badge-cbn">🌙 CBN • SLEEP</span>';
    } else if (pNameLow.includes('cbg')) {
        funcBadge = '<span class="badge-cbg">⚡ CBG • FOCUS</span>';
    } else if (pNameLow.includes('4:1') || pNameLow.includes('cbd bomb')) {
        funcBadge = '<span class="badge-cbd">🌿 CBD • CALM</span>';
    } else if (pNameLow.includes('1:1') && !pNameLow.includes('cbn')) {
        funcBadge = '<span class="badge-balance">⚖️ 1:1 • BALANCED</span>';
    }

    let priceHtml = '';
    if (it.is_sale && it.old_price) {
        priceHtml = `
            <span class="sale">${formatCAD(it.price)}</span>
            <span class="old">${formatCAD(it.old_price)}</span>
        `;
    } else {
        priceHtml = `<span class="regular">${formatCAD(it.price)}</span>`;
    }

    const isFeatured = (it.tag === 'FEATURED' || (it.is_sale && it.old_price));
    const isLowStock = (!isFeatured && stockNum > 0 && stockNum <= 3);

    let rowClass = '';
    if (isFeatured) rowClass = 'row-featured';
    else if (isLowStock) rowClass = 'row-low-stock';

    return `
        <div class="soft-row ${rowClass}">
            <div class="soft-name">${it.product_name}${funcBadge}${tagBadge}${stockBadge}</div>
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

    const count = sec.items.length;
    const subHtml = sec.subtitle ? `<div class="card-head-sub">${sec.subtitle}</div>` : '';

    // Option 4: Sub-Categorize Infused Beverages into Sodas & Seltzers
    if (cardKey === 'beverages') {
        const sodas = [];
        const seltzers = [];
        sec.items.forEach(it => {
            const nl = (it.product_name || '').toLowerCase();
            if (nl.includes('soda') || nl.includes('cola') || nl.includes('root beer') || nl.includes('cream soda')) {
                sodas.push(it);
            } else {
                seltzers.push(it);
            }
        });

        return `
            <div class="soft-card card-cyan">
                <div class="card-head-title">${sec.title} <span class="title-count">(${count})</span></div>
                <div class="card-head-sub">${sec.subtitle || 'CRAFT SODAS • SPARKLING SELTZERS'}</div>
                <div class="table-header-soft">
                    <div>BEVERAGE</div>
                    <div style="text-align:center;">TYPE</div>
                    <div style="text-align:center;">THC</div>
                    <div style="text-align:center;">CBD</div>
                    <div style="text-align:right;">PRICE</div>
                </div>
                ${sodas.length > 0 ? `
                    <div class="subhead" style="color:#38bdf8; margin: 3px 0 1px; font-size:11.5px; font-weight:800;"><span>🥤 Craft Sodas & Colas</span> <span style="font-size:10px; color:#888;">${sodas.length} SKUs</span></div>
                    ${sodas.map(it => renderSoftRow(it)).join('')}
                ` : ''}
                ${seltzers.length > 0 ? `
                    <div class="subhead" style="color:#2dd4bf; margin: 5px 0 1px; font-size:11.5px; font-weight:800;"><span>🍋 Seltzers, Teas & Lemonades</span> <span style="font-size:10px; color:#888;">${seltzers.length} SKUs</span></div>
                    ${seltzers.map(it => renderSoftRow(it)).join('')}
                ` : ''}
            </div>
        `;
    }

    return `
        <div class="soft-card card-${sec.color || 'gold'}">
            <div class="card-head-title">${sec.title} <span class="title-count">(${count})</span></div>
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
        
        const indItems = d.indica.items || [];
        const hybItems = d.hybrid.items || [];
        const satItems = d.sativa.items || [];

        let infusedHtml = '';
        const infIndica = (d.infused && d.infused.indica_items) || [];
        const infHybrid = (d.infused && d.infused.hybrid_items) || [];
        const infSativa = (d.infused && d.infused.sativa_items) || [];
        const infTotal = (d.infused && d.infused.items) ? d.infused.items.length : (infIndica.length + infHybrid.length + infSativa.length);

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
                    <div class="title indica">INDICA PRE-ROLLS <span class="title-count">(${indItems.length})</span></div>
                    <div class="table-header"><div class="h-name">Strain / Product</div><div class="h-thc">THC</div><div class="h-price">Price</div></div>
                    ${indItems.map(it => renderRowHtml(it, false)).join('') || '<div style="color:#666; font-size:12px; padding:15px; text-align:center;">No Indica Pre-Rolls</div>'}
                </div>

                <!-- HYBRID PRE-ROLLS -->
                <div class="panel">
                    <div class="title hybrid">HYBRID & BLENDS PRE-ROLLS <span class="title-count">(${hybItems.length})</span></div>
                    <div class="table-header"><div class="h-name">Strain / Product</div><div class="h-thc">THC</div><div class="h-price">Price</div></div>
                    ${hybItems.map(it => renderRowHtml(it, false)).join('') || '<div style="color:#666; font-size:12px; padding:15px; text-align:center;">No Hybrid Pre-Rolls</div>'}
                </div>

                <!-- SATIVA PRE-ROLLS -->
                <div class="panel">
                    <div class="title sativa">SATIVA PRE-ROLLS <span class="title-count">(${satItems.length})</span></div>
                    <div class="table-header"><div class="h-name">Strain / Product</div><div class="h-thc">THC</div><div class="h-price">Price</div></div>
                    ${satItems.map(it => renderRowHtml(it, false)).join('') || '<div style="color:#666; font-size:12px; padding:15px; text-align:center;">No Sativa Pre-Rolls</div>'}
                </div>

                <!-- INFUSED PRE-ROLLS -->
                <div class="panel">
                    <div class="title infused">INFUSED PRE-ROLLS <span class="title-count">(${infTotal})</span></div>
                    <div class="table-header"><div class="h-name">Strain / Product</div><div class="h-thc">THC</div><div class="h-price">Price</div></div>
                    ${infusedHtml || '<div style="color:#666; font-size:12px; padding:15px; text-align:center;">No Infused Pre-Rolls</div>'}
                </div>
            </div>
        `;

    } else if (screen === 2) {
        // SCREEN 2: FLOWER & VAPES (Indica, Hybrid, Sativa, 510 & Disposables)
        const f = res.structured.flower;
        const v = res.structured.vapes;

        const indTotal = (f.indica_dried.items.length + f.indica_milled.items.length);
        const hybTotal = (f.hybrid_dried.items.length + f.hybrid_milled.items.length);
        const col1Total = indTotal + hybTotal;

        // Column 1: Indica & Hybrid Flower
        let col1Html = '';
        if (indTotal > 0) {
            col1Html += `<div class="subhead indica"><span style="color:#4CAF50;">Indica Dried Flower</span> <span style="font-size:11px; color:#888;">${f.indica_dried.items.length} SKUs</span></div>`;
            col1Html += f.indica_dried.items.map(it => renderRowHtml(it, false)).join('');
            if (f.indica_milled.items.length) {
                col1Html += `<div style="font-size:10.5px; font-weight:800; color:#a3e635; margin:6px 0 2px 2px; text-transform:uppercase; letter-spacing:0.5px; display:flex; justify-content:space-between;"><span><i class="bi bi-scissors"></i> Indica Milled</span> <span style="font-size:11px; color:#888;">${f.indica_milled.items.length} SKUs</span></div>`;
                col1Html += f.indica_milled.items.map(it => renderRowHtml(it, false)).join('');
            }
        }

        if (hybTotal > 0) {
            col1Html += `<div class="subhead hybrid" style="margin-top:10px;"><span style="color:#FFC107;">Hybrid Dried Flower</span> <span style="font-size:11px; color:#888;">${f.hybrid_dried.items.length} SKUs</span></div>`;
            col1Html += f.hybrid_dried.items.map(it => renderRowHtml(it, false)).join('');
            if (f.hybrid_milled.items.length) {
                col1Html += `<div style="font-size:10.5px; font-weight:800; color:#a3e635; margin:6px 0 2px 2px; text-transform:uppercase; letter-spacing:0.5px; display:flex; justify-content:space-between;"><span><i class="bi bi-scissors"></i> Hybrid Milled</span> <span style="font-size:11px; color:#888;">${f.hybrid_milled.items.length} SKUs</span></div>`;
                col1Html += f.hybrid_milled.items.map(it => renderRowHtml(it, false)).join('');
            }
        }

        // Column 2: Sativa Flower
        const satTotal = (f.sativa_dried.items.length + f.sativa_milled.items.length);
        let col2Html = '';
        if (satTotal > 0) {
            col2Html += `<div class="subhead sativa"><span style="color:#FF6666;">Sativa Dried Flower</span> <span style="font-size:11px; color:#888;">${f.sativa_dried.items.length} SKUs</span></div>`;
            col2Html += f.sativa_dried.items.map(it => renderRowHtml(it, false)).join('');
            if (f.sativa_milled.items.length) {
                col2Html += `<div style="font-size:10.5px; font-weight:800; color:#a3e635; margin:6px 0 2px 2px; text-transform:uppercase; letter-spacing:0.5px; display:flex; justify-content:space-between;"><span><i class="bi bi-scissors"></i> Sativa Milled</span> <span style="font-size:11px; color:#888;">${f.sativa_milled.items.length} SKUs</span></div>`;
                col2Html += f.sativa_milled.items.map(it => renderRowHtml(it, false)).join('');
            }
        }

        // Column 3: 510 Carts (Indica & Hybrid)
        const v510Total = (v.vapes_510_indica.items.length + v.vapes_510_hybrid.items.length);
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
        const dispTotal = (v.disp_indica.items.length + v.disp_hybrid.items.length + v.disp_sativa.items.length);
        const col4Total = v.vapes_510_sativa.items.length + dispTotal;
        let col4Html = '';
        if (v.vapes_510_sativa.items.length) {
            col4Html += `<div class="subhead sativa"><span style="color:#FF6666;">510 Sativa</span> <span style="font-size:11px; color:#888;">${v.vapes_510_sativa.items.length} SKUs</span></div>`;
            col4Html += v.vapes_510_sativa.items.map(it => renderRowHtml(it, true)).join('');
        }
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
                    <div class="title indica">INDICA & HYBRID FLOWER <span class="title-count">(${col1Total})</span></div>
                    <div class="table-header"><div class="h-name">Strain / Product</div><div class="h-thc">THC/CBD</div><div class="h-price">Price</div></div>
                    ${col1Html || '<div style="color:#666; font-size:12px; padding:15px; text-align:center;">No Flower</div>'}
                </div>

                <!-- COL 2: SATIVA FLOWER -->
                <div class="panel">
                    <div class="title sativa">SATIVA FLOWER <span class="title-count">(${satTotal})</span></div>
                    <div class="table-header"><div class="h-name">Strain / Product</div><div class="h-thc">THC/CBD</div><div class="h-price">Price</div></div>
                    ${col2Html || '<div style="color:#666; font-size:12px; padding:15px; text-align:center;">No Flower</div>'}
                </div>

                <!-- COL 3: 510 CARTS -->
                <div class="panel">
                    <div class="title vapes510">510 CARTRIDGES <span class="title-count">(${v510Total})</span></div>
                    <div class="table-header"><div class="h-name">Product</div><div class="h-thc">THC/CBD</div><div class="h-price">Price</div></div>
                    ${col3Html || '<div style="color:#666; font-size:12px; padding:15px; text-align:center;">No 510 Carts</div>'}
                </div>

                <!-- COL 4: 510 SATIVA & DISPOSABLES -->
                <div class="panel">
                    <div class="title disposable">VAPES & DISPOSABLES <span class="title-count">(${col4Total})</span></div>
                    <div class="table-header"><div class="h-name">Product</div><div class="h-thc">THC/CBD</div><div class="h-price">Price</div></div>
                    ${col4Html || '<div style="color:#666; font-size:12px; padding:15px; text-align:center;">No Disposables</div>'}
                </div>
            </div>
        `;

    } else {
        // SCREEN 3: SOFT CHEWS, DRINKS, CONCENTRATES, TOPICALS & OILS/CAPSULES
        const d = res.structured;
        
        const gSat = (d.gummies_sativa && d.gummies_sativa.items) || [];
        const chocolates = (d.chocolates && d.chocolates.items) || [];
        const wellness = (d.wellness && d.wellness.items) || [];
        const col3Total = gSat.length + chocolates.length + wellness.length;

        const col3UnifiedHtml = `
            <div class="soft-card card-pink">
                <div class="card-head-title">SATIVA CHEWS, CHOCOLATE & WELLNESS <span class="title-count">(${col3Total})</span></div>
                <div class="card-head-sub">SATIVA GUMMIES • ARTISAN CHOCOLATES • DROPS & CAPSULES</div>
                <div class="table-header-soft">
                    <div>PRODUCT</div>
                    <div style="text-align:center;">STRAIN</div>
                    <div style="text-align:center;">THC</div>
                    <div style="text-align:center;">CBD</div>
                    <div style="text-align:right;">PRICE</div>
                </div>
                ${gSat.length > 0 ? `
                    <div class="subhead" style="color:#f472b6; margin: 3px 0 1px; font-size:11px;"><span><i class="bi bi-circle-fill" style="font-size:7px;"></i> Sativa Soft Chews</span> <span style="font-size:10px; color:#888;">${gSat.length} SKUs</span></div>
                    ${gSat.map(it => renderSoftRow(it)).join('')}
                ` : ''}
                ${chocolates.length > 0 ? `
                    <div class="subhead" style="color:#fb923c; margin: 4px 0 1px; font-size:11px;"><span><i class="bi bi-box2-heart" style="font-size:10px;"></i> Artisan Chocolates</span> <span style="font-size:10px; color:#888;">${chocolates.length} SKUs</span></div>
                    ${chocolates.map(it => renderSoftRow(it)).join('')}
                ` : ''}
                ${wellness.length > 0 ? `
                    <div class="subhead" style="color:#c084fc; margin: 4px 0 1px; font-size:11px;"><span><i class="bi bi-capsule" style="font-size:10px;"></i> Oils, Drops & Wellness</span> <span style="font-size:10px; color:#888;">${wellness.length} SKU</span></div>
                    ${wellness.map(it => renderSoftRow(it)).join('')}
                ` : ''}
            </div>
        `;

        mount.innerHTML = `
            <div class="container-softchews">
                <!-- COLUMN 1: CONCENTRATES & BEVERAGES -->
                <div class="column-deck">
                    ${renderSoftCard('concentrates', d)}
                    ${renderSoftCard('beverages', d)}
                </div>

                <!-- COLUMN 2: SOFT CHEWS & GUMMIES (INDICA & HYBRID) -->
                <div class="column-deck">
                    ${renderSoftCard('gummies_ind_hyb', d)}
                </div>

                <!-- COLUMN 3: SATIVA SOFT CHEWS + ARTISAN CHOCOLATES + WELLNESS -->
                <div class="column-deck">
                    ${col3UnifiedHtml}
                </div>
            </div>
        `;
    }

    updateNavPills(screen);
    updateSyncStatus(res.updated_at);
}

// Fetch live menu from API strictly for current TV's dedicated screen
function fetchLiveMenu(screenId, storeId) {
    const sId = screenId || currentScreenId;
    const stId = storeId || currentStoreId;

    fetch(`/api/tv-menu?screen=${sId}&store=${stId}`)
        .then(r => {
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            return r.json();
        })
        .then(res => {
            if (res.success) {
                renderMenuData(res);
                try {
                    localStorage.setItem(`kroniclez_tv_cache_${sId}`, JSON.stringify(res));
                } catch (e) {}
            }
        })
        .catch(err => {
            console.warn("TV Menu live fetch hiccup, falling back to cache:", err);
            try {
                const cached = localStorage.getItem(`kroniclez_tv_cache_${sId}`);
                if (cached) {
                    renderMenuData(JSON.parse(cached));
                }
            } catch (e) {}
            // Retry in 4 seconds if disconnected
            setTimeout(() => fetchLiveMenu(sId, stId), 4000);
        });
}

// Switch Screen manually if selected
function switchScreen(screenNum) {
    currentScreenId = screenNum;
    const newUrl = `/tv${currentScreenId}`;
    window.history.replaceState({}, '', newUrl);
    fetchLiveMenu(currentScreenId, currentStoreId);
}

// Update Active Button in Floating Nav
function updateNavPills(screen) {
    const btn1 = document.getElementById('nav-btn-screen1');
    const btn2 = document.getElementById('nav-btn-screen2');
    const btn3 = document.getElementById('nav-btn-screen3');

    if (btn1) btn1.className = `nav-link-btn ${screen === 1 ? 'active' : ''}`;
    if (btn2) btn2.className = `nav-link-btn ${screen === 2 ? 'active' : ''}`;
    if (btn3) btn3.className = `nav-link-btn ${screen === 3 ? 'active' : ''}`;
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

// Keyboard shortcuts for TV Remotes & Staff
window.addEventListener('keydown', (e) => {
    if (e.key === '1') switchScreen(1);
    if (e.key === '2') switchScreen(2);
    if (e.key === '3') switchScreen(3);
    if (e.key.toLowerCase() === 'f') toggleFullscreen();
    if (e.key.toLowerCase() === 'r') fetchLiveMenu(currentScreenId, currentStoreId);
});

window.addEventListener('mousemove', showNav);
window.addEventListener('touchstart', showNav);

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
    const params = getUrlParams();
    currentScreenId = params.screen;
    currentStoreId = params.store;

    showNav();

    // 1. Render immediately if pre-injected data exists
    if (window.__INITIAL_MENU_DATA__ && window.__INITIAL_MENU_DATA__.success && window.__INITIAL_MENU_DATA__.screen === currentScreenId && window.__INITIAL_MENU_DATA__.total_in_stock > 0) {
        renderMenuData(window.__INITIAL_MENU_DATA__);
        try {
            localStorage.setItem(`kroniclez_tv_cache_${currentScreenId}`, JSON.stringify(window.__INITIAL_MENU_DATA__));
        } catch (e) {}
    } else {
        // 2. Instant cache recovery from localStorage
        try {
            const cached = localStorage.getItem(`kroniclez_tv_cache_${currentScreenId}`);
            if (cached) {
                renderMenuData(JSON.parse(cached));
            }
        } catch (e) {}
        fetchLiveMenu(currentScreenId, currentStoreId);
    }

    // Auto-poll Tendy inventory every 25 seconds strictly for this TV's dedicated screen
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(() => {
        fetchLiveMenu(currentScreenId, currentStoreId);
    }, 25000);
});
