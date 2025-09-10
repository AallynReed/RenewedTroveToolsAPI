// ===== Cookie helpers & theme logic =====
function setCookie(name, value, days) {
    const expires = days ? ";expires=" + new Date(Date.now() + days * 864e5).toUTCString() : "";
    document.cookie = name + "=" + encodeURIComponent(value) + expires + ";path=/";
}
function getCookie(name) {
    return decodeURIComponent(document.cookie.replace(new RegExp("(?:(?:^|.*;)\\s*" + name.replace(/[-.]/g, "\\$&") + "\\s*\\=\\s*([^;]*).*$)|^.*$"), "$1")) || null;
}
function setTheme(theme) {
    document.body.setAttribute('data-theme', theme);
    setCookie('theme', theme, 365);
    document.getElementById('theme-switch').checked = (theme === "light");
    document.getElementById('theme-label').textContent = theme === "light" ? "Light Mode" : "Dark Mode";
}
function loadTheme() {
    let theme = getCookie('theme');
    if (!theme) theme = "dark";
    setTheme(theme);
}
document.getElementById('theme-switch').addEventListener('change', function () {
    setTheme(this.checked ? "light" : "dark");
});
loadTheme();

// ===== Lookups =====
const GEM_LOOKUPS = {};
const GEM_LOOKUP_ENDPOINTS = [
    'types', 'elements', 'tiers', 'restrictions', 'stat_types', 'augment_types'
];
async function fetchGemLookups() {
    const fetches = GEM_LOOKUP_ENDPOINTS.map(key =>
        fetch(`https://kiwiapi.aallyn.xyz/v2/gems/${key}`).then(res => res.json())
    );
    const results = await Promise.all(fetches);
    GEM_LOOKUP_ENDPOINTS.forEach((key, i) => {
        GEM_LOOKUPS[key] = results[i];
    });
    render(); // trigger render after lookups loaded
}

function populateGemFormMenus() {
    // Gem Types
    const typeSelect = document.getElementById('gem-type');
    typeSelect.innerHTML = "";
    // Add empty option
    const typeNone = document.createElement('option');
    typeNone.value = "";
    typeNone.textContent = "(None)";
    typeSelect.appendChild(typeNone);
    Object.entries(GEM_LOOKUPS.types || {})
        .sort((a, b) => a[1] - b[1])
        .forEach(([name, id]) => {
            const opt = document.createElement('option');
            opt.value = id;
            opt.textContent = formatGemName(name);
            typeSelect.appendChild(opt);
        });

    // Gem Tiers
    const tierSelect = document.getElementById('gem-tier');
    tierSelect.innerHTML = "";
    const tierNone = document.createElement('option');
    tierNone.value = "";
    tierNone.textContent = "(None)";
    tierSelect.appendChild(tierNone);
    Object.entries(GEM_LOOKUPS.tiers || {})
        .sort((a, b) => a[1] - b[1])
        .forEach(([name, id]) => {
            const opt = document.createElement('option');
            opt.value = id;
            opt.textContent = formatGemName(name);
            tierSelect.appendChild(opt);
        });

    // Gem Elements
    const elemSelect = document.getElementById('gem-element');
    elemSelect.innerHTML = "";
    const elemNone = document.createElement('option');
    elemNone.value = "";
    elemNone.textContent = "(None)";
    elemSelect.appendChild(elemNone);
    Object.entries(GEM_LOOKUPS.elements || {})
        .sort((a, b) => a[1] - b[1])
        .forEach(([name, id]) => {
            const opt = document.createElement('option');
            opt.value = id;
            opt.textContent = formatGemName(name);
            elemSelect.appendChild(opt);
        });

    // restriction input (restrictions, for example)
    const restrictionSelect = document.getElementById('gem-restriction');
    restrictionSelect.innerHTML = "";
    const restrictionNone = document.createElement('option');
    restrictionNone.value = "";
    restrictionNone.textContent = "(None)";
    restrictionSelect.appendChild(restrictionNone);
    Object.entries(GEM_LOOKUPS.restrictions || {})
        .sort((a, b) => a[1] - b[1])
        .forEach(([name, id]) => {
            const opt = document.createElement('option');
            opt.value = id;
            opt.textContent = formatGemName(name);
            restrictionSelect.appendChild(opt);
        });
}

// Show/hide restriction input when type changes
document.addEventListener('change', function (e) {
    if (e.target && e.target.id === 'gem-type') {
        const restrictionSelect = document.getElementById('gem-restriction');
        if (e.target.value === "1") {
            restrictionSelect.disabled = false;
        } else {
            restrictionSelect.disabled = true;
            restrictionSelect.value = "";
        }
    }
});

// On page load, ensure correct state
function setInitialRestrictionState() {
    const typeSelect = document.getElementById('gem-type');
    const restrictionSelect = document.getElementById('gem-restriction');
    if (typeSelect && restrictionSelect) {
        if (typeSelect.value === "1") {
            restrictionSelect.disabled = false;
        } else {
            restrictionSelect.disabled = true;
            restrictionSelect.value = "";
        }
    }
}

// Call after form menus are populated
afterGemLookupsLoaded = function () {
    populateGemFormMenus();
    setInitialRestrictionState();
}

// Call after GEM_LOOKUPS loaded:
fetchGemLookups().then(afterGemLookupsLoaded);

function formatGemName(name) {
    return name.split(' ').map(
        word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
    ).join(' ');
}
function getTypeDisplayName(typeIdOrName) {
    const entry = Object.entries(GEM_LOOKUPS.types || {}).find(([key, val]) =>
        val == typeIdOrName || key == typeIdOrName);
    return entry ? formatGemName(entry[0]) : typeIdOrName;
}
function getElementIds() {
    return Object.values(GEM_LOOKUPS.elements || {});
}
function getElementNameById(id) {
    const found = Object.entries(GEM_LOOKUPS.elements || {}).find(([, val]) => val == id);
    return found ? formatGemName(found[0]) : "Unknown";
}
function getTierDisplayName(tierId) {
    const backendName = Object.keys(GEM_LOOKUPS.tiers || {}).find(
        key => String(GEM_LOOKUPS.tiers[key]) === String(tierId)
    );
    return backendName ? formatGemName(backendName) : tierId;
}

// ===== Inventory and equipped state management with cookies =====
let equipped = [];
let inventory = [];
let selected = null;
let selectedSource = null; // Track where selected came from
function loadInventory() {
    let inventory_data = localStorage.getItem('inventory');
    if (inventory_data) {
        inventory = JSON.parse(inventory_data);
    }
    let equipped_data = localStorage.getItem('equipped');
    if (equipped_data) {
        equipped = JSON.parse(equipped_data);
    }
    render();
}
function saveInventory() {
    localStorage.setItem('inventory', JSON.stringify(inventory));
    localStorage.setItem('equipped', JSON.stringify(equipped));
}

loadInventory();

function gemTierBgUrl(item) {
    return `https://trove.aallyn.xyz/assets/gems/gem_tiers/${item.tier}.png`;
}
function gemImageUrl(item) {
    return `https://trove.aallyn.xyz/assets/gems/gem_types/${item.type}/elements/${item.element}.png`;
}

// ===== Dynamic Equipped Panel Logic (by element, type restriction per slot) =====
function getEquippedRows() {
    // Get array of [elementName, elementId] pairs and sort by elementId
    const sortedElements = Object.entries(GEM_LOOKUPS.elements || {})
        .sort((a, b) => a[1] - b[1]);
    // For each element, 3 slots: slot 0+1 type 1, slot 2 type 2
    return sortedElements.map(([_, elementId], rowIdx) => ({
        elementId,
        slots: [
            { typeRestriction: 1, slotIdx: rowIdx * 3 + 0 },
            { typeRestriction: 1, slotIdx: rowIdx * 3 + 1 },
            { typeRestriction: 2, slotIdx: rowIdx * 3 + 2 }
        ]
    }));
}

function render() {
    renderEquipped();
    renderInventory();
    renderSelected();
    renderTrashSlot();
    saveInventory();
}

// Element color mapping and default
const ELEMENT_COLORS = {
    Fire:   '#a96b64',  // Muted brick red
    Water:  '#628bad',  // Muted slate blue
    Air:    '#a8a77b',  // Muted olive gold
    Cosmic: '#4e7d6c',  // Muted teal green
};
const ELEMENT_DEFAULT_COLOR = '#888888';

function renderEquipped() {
    // --- Primordial Dragon Toggles: keep state across renders ---
    if (!window.primordialDragonToggles) window.primordialDragonToggles = {};
    Object.entries(GEM_LOOKUPS.elements || {}).forEach(([elementName, elementId]) => {
        if (typeof window.primordialDragonToggles[elementId] === "undefined") {
            window.primordialDragonToggles[elementId] = true;
        }
    });

    const equippedEl = document.getElementById('equipped');
    equippedEl.innerHTML = '';
    if (!GEM_LOOKUPS.elements || !GEM_LOOKUPS.types) return;

    const equippedRows = getEquippedRows();
    equippedRows.forEach((row, rowIdx) => {
        // Row label with element color
        const elementName = getElementNameById(row.elementId);
        const color = ELEMENT_COLORS[formatGemName(elementName)] || ELEMENT_DEFAULT_COLOR;
        const rowLabel = document.createElement('div');
        rowLabel.className = 'equipped-row-label';
        rowLabel.textContent = elementName;
        rowLabel.style.color = color;
        equippedEl.appendChild(rowLabel);

        // Row slots
        const rowDiv = document.createElement('div');
        rowDiv.className = 'equipped-row';
        rowDiv.className = 'equipped-row';
        rowDiv.style.border = `2px dashed ${color}`;
        rowDiv.style.borderRadius = '10px';
        rowDiv.style.marginBottom = '16px';
        rowDiv.style.padding = '5px 10px';
        rowDiv.style.width = "fit-content"
        rowDiv.style.marginLeft = 'auto';
        rowDiv.style.marginRight = 'auto';
        row.slots.forEach((slot, slotIdx) => {
            const idx = slot.slotIdx;
            if (!equipped[idx]) equipped[idx] = null;
            const item = equipped[idx];
            const slotDiv = document.createElement('div');
            slotDiv.className = 'slot';
            slotDiv.dataset.row = rowIdx;
            slotDiv.dataset.slot = slotIdx;
            slotDiv.dataset.index = idx;
            slotDiv.dataset.pane = 'equipped';
            slotDiv.setAttribute('data-has-item', !!item);
            slotDiv.ondragover = handleDragOver;
            slotDiv.ondrop = (e) => handleEquippedDrop(e, row.elementId, slot.typeRestriction, idx);
            if (item) {
                const itemEl = createItem(item, 'equipped', idx);
                slotDiv.appendChild(itemEl);
            }

            if (slotIdx === 1) {
                const separator = document.createElement('div');
                separator.className = 'slot-vertical-separator';
                separator.style.borderColor = color;
                rowDiv.appendChild(slotDiv);
                rowDiv.appendChild(separator);
            } else {
                rowDiv.appendChild(slotDiv);
            }
        });
        equippedEl.appendChild(rowDiv);
    });

    // --- Equipped Stat Summary ---
    const equippedStatsSummary = document.createElement('div');
    equippedStatsSummary.style.width = '100%';
    equippedStatsSummary.style.margin = '25px 0 0 0';
    equippedStatsSummary.style.display = 'flex';
    equippedStatsSummary.style.flexDirection = 'column';
    equippedStatsSummary.style.alignItems = 'center';

    // ---- Toggles Row ----
    const togglesRow = document.createElement('div');
    togglesRow.className = 'primordial-toggles-row';
    Object.entries(GEM_LOOKUPS.elements || {}).sort((a, b) => a[1] - b[1]).forEach(([elementName, elementId]) => {
        const color = ELEMENT_COLORS[formatGemName(elementName)] || ELEMENT_DEFAULT_COLOR;

        const toggleDiv = document.createElement('label');
        toggleDiv.className = 'primordial-toggle-label';

        const toggleInput = document.createElement('input');
        toggleInput.type = 'checkbox';
        toggleInput.className = 'primordial-toggle-checkbox';
        toggleInput.checked = !!window.primordialDragonToggles[elementId];
        toggleInput.onchange = () => {
            window.primordialDragonToggles[elementId] = toggleInput.checked;
            renderEquipped();
        };

        const customSlider = document.createElement('span');
        customSlider.className = 'primordial-toggle-slider';
        customSlider.style.background = toggleInput.checked
        ? `${color}`
        : '#ccc';

        const labelText = document.createElement('span');
        labelText.className = 'primordial-toggle-text';
        labelText.textContent = `${formatGemName(elementName)} Primordial Dragon`;
        labelText.style.color = color;

        toggleDiv.appendChild(toggleInput);
        toggleDiv.appendChild(customSlider);
        toggleDiv.appendChild(labelText);
        togglesRow.appendChild(toggleDiv);
    });
    equippedStatsSummary.appendChild(togglesRow);

    // 1. Calculate totals for all equipped gems (raw, no buffs)
    const equippedGems = equipped.filter(Boolean);
    const perElementStats = {};
    const perElementPR = {};
    const allStatNames = new Set();

    equippedGems.forEach(gem => {
        const elementId = gem.element;
        if (!perElementStats[elementId]) perElementStats[elementId] = {};
        if (!perElementPR[elementId]) perElementPR[elementId] = 0;
        perElementPR[elementId] += gem.power_rank || 0;
        (gem.stats || []).forEach((stat, i) => {
            const statName = Object.keys(gem.stat_values[i])[0];
            const value = gem.stat_values[i][statName];
            perElementStats[elementId][statName] = (perElementStats[elementId][statName] || 0) + value;
            allStatNames.add(statName);
        });
    });

    // 2. Apply +10% buff if toggle enabled, prepare per-element and total stats (with buffs)
    const perElementBuffed = {};
    const perElementBuffedPR = {};
    const statTotalsBuffed = {};
    let totalPRBuffed = 0;

    Object.entries(GEM_LOOKUPS.elements || {}).forEach(([elementName, elementId]) => {
        const stats = perElementStats[elementId] || {};
        const buffedStats = {};
        const buffActive = !!window.primordialDragonToggles[elementId];
        const origPR = perElementPR[elementId] || 0;
        let buffedPR = origPR;
        if (buffActive) buffedPR = origPR * 1.10;
        perElementBuffedPR[elementId] = buffedPR;
        totalPRBuffed += buffedPR;

        Object.entries(stats).forEach(([statName, val]) => {
            let finalVal = val;
            if (buffActive) finalVal = val * 1.10;
            buffedStats[statName] = finalVal;
            statTotalsBuffed[statName] = (statTotalsBuffed[statName] || 0) + finalVal;
        });
        perElementBuffed[elementId] = { ...buffedStats, _buffed: buffActive };
    });

    allStatNames.forEach(statName => {
        if (!(statName in statTotalsBuffed)) statTotalsBuffed[statName] = 0;
    });

    // --- Top total card ---
    const totalsCard = document.createElement('div');
    totalsCard.className = 'selected-stats-square';
    totalsCard.style.margin = '0 auto 20px auto';
    totalsCard.style.maxWidth = 'fit-content';

    totalsCard.innerHTML = `
    <div style="text-align:center;font-weight:bold;font-size:1.22em;margin-bottom:7px;color:#34d058">
        Equipped Totals
    </div>
    <div style="text-align:center;font-weight:bold;margin-bottom:10px;">
        Total Power Rank: ${Math.round(totalPRBuffed * 100) / 100}
    </div>
    <hr style="width:60%;border:0;border-top:1.5px solid #3b4252;margin:10px auto 10px auto;">
    `;

    const totalsStatGrid = document.createElement('div');
    totalsStatGrid.style.display = 'grid';
    totalsStatGrid.style.gridTemplateColumns = '1fr 1fr';
    totalsStatGrid.style.gap = '2px 20px';
    totalsStatGrid.style.justifyContent = 'center';

    Array.from(allStatNames).sort().forEach(statName => {
        const statVal = statTotalsBuffed[statName] ?? 0;
        if (statVal > 0) {
            const statLabel = document.createElement('div');
            statLabel.style.fontWeight = 'bold';
            statLabel.textContent = statName;
            const statValue = document.createElement('div');
            statValue.textContent = Math.round(statVal * 100) / 100;
            totalsStatGrid.appendChild(statLabel);
            totalsStatGrid.appendChild(statValue);
        }
    });
    totalsCard.appendChild(totalsStatGrid);
    equippedStatsSummary.appendChild(totalsCard);

    // --- Per-element cards (with buff badge if enabled) ---
    const elementCardsContainer = document.createElement('div');
    elementCardsContainer.style.display = 'flex';
    elementCardsContainer.style.flexWrap = 'wrap';
    elementCardsContainer.style.gap = '17px';
    elementCardsContainer.style.justifyContent = 'center';

    Object.entries(GEM_LOOKUPS.elements || {}).sort((a, b) => a[1] - b[1]).forEach(([elementName, elementId]) => {
        const stats = perElementBuffed[elementId] || {};
        const nonzeroStats = Object.entries(stats).filter(([key, val]) => key !== '_buffed' && val > 0);
        const color = ELEMENT_COLORS[formatGemName(elementName)] || ELEMENT_DEFAULT_COLOR;

        const card = document.createElement('div');
        card.className = 'selected-stats-square';
        card.style.minWidth = '160px';
        card.style.maxWidth = '270px';
        card.style.flex = '1 1 220px';
        card.style.margin = '0';
        card.style.border = `2px solid ${color}`;

        // Name row with badge if buff enabled
        const nameRow = document.createElement('div');
        nameRow.style.display = 'flex';
        nameRow.style.justifyContent = 'center';
        nameRow.style.alignItems = 'center';
        nameRow.style.gap = '9px';
        nameRow.style.marginBottom = '6px';

        const nameDiv = document.createElement('div');
        nameDiv.textContent = formatGemName(elementName);
        nameDiv.style.fontWeight = 'bold';
        nameDiv.style.fontSize = '1.08em';
        nameDiv.style.color = color;
        nameRow.appendChild(nameDiv);

        // Buff badge
        if (stats._buffed && nonzeroStats.length > 0) {
            const buffBadge = document.createElement('span');
            buffBadge.textContent = '+10%';
            buffBadge.style.background = 'linear-gradient(90deg,#34d058 50%,#43a047 100%)';
            buffBadge.style.color = '#fff';
            buffBadge.style.borderRadius = '6px';
            buffBadge.style.fontSize = '0.97em';
            buffBadge.style.fontWeight = 'bold';
            buffBadge.style.padding = '1px 9px';
            buffBadge.style.marginLeft = '5px';
            buffBadge.title = 'Primordial Dragon buff enabled';
            nameRow.appendChild(buffBadge);
        }
        card.appendChild(nameRow);

        // Power Rank row
        const prDiv = document.createElement('div');
        prDiv.style.textAlign = 'center';
        prDiv.style.fontWeight = 'bold';
        // prDiv.style.color = '#34d058';
        prDiv.style.marginBottom = '5px';
        prDiv.textContent = `Power Rank: ${Math.round((perElementBuffedPR[elementId] || 0) * 100) / 100}`;
        card.appendChild(prDiv);

        // Horizontal separator
        const hr = document.createElement('hr');
        hr.style.width = '60%';
        hr.style.border = '0';
        hr.style.borderTop = '1.5px solid #3b4252';
        hr.style.margin = '8px auto 8px auto';
        hr.style.borderColor = `${color}`;
        card.appendChild(hr);

        // If no gems OR no nonzero stats for this element
        const hasGems = equipped.some(gem => gem && String(gem.element) === String(elementId));
        if (!hasGems || nonzeroStats.length === 0) {
            const noneDiv = document.createElement('div');
            noneDiv.style.textAlign = 'center';
            noneDiv.style.color = '#a3adc2';
            noneDiv.style.fontStyle = 'italic';
            noneDiv.textContent = 'No gems socketed';
            card.appendChild(noneDiv);
        } else {
            const statGrid = document.createElement('div');
            statGrid.style.display = 'grid';
            statGrid.style.gridTemplateColumns = '1fr 1fr';
            statGrid.style.gap = '2px 12px';
            statGrid.style.justifyContent = 'center';
            nonzeroStats.forEach(([statName, statValue]) => {
                const statLabel = document.createElement('div');
                statLabel.style.fontWeight = 'bold';
                statLabel.textContent = statName;
                const statVal = document.createElement('div');
                statVal.textContent = Math.round(statValue * 100) / 100;
                statGrid.appendChild(statLabel);
                statGrid.appendChild(statVal);
            });
            card.appendChild(statGrid);
        }
        elementCardsContainer.appendChild(card);
    });

    equippedStatsSummary.appendChild(elementCardsContainer);

    // Append the summary after all rows
    equippedEl.appendChild(equippedStatsSummary);
}

document.addEventListener('DOMContentLoaded', function () {
    const levelSlider = document.getElementById('gem-level-slider');
    const augmentSlider = document.getElementById('gem-augment-slider');
    const levelValue = document.getElementById('gem-level-value');
    const augmentValue = document.getElementById('gem-augment-value');
    if (levelSlider && levelValue) {
        levelSlider.addEventListener('input', () => { levelValue.textContent = levelSlider.value; });
    }
    if (augmentSlider && augmentValue) {
        augmentSlider.addEventListener('input', () => { augmentValue.textContent = augmentSlider.value; });
    }
});

function handleEquippedDrop(e, elementId, typeRestriction, equippedIdx) {
    e.preventDefault();
    const { fromPane, fromIdx } = JSON.parse(e.dataTransfer.getData('text/plain'));
    let draggedGem = null;

    if (fromPane === 'selected') {
        // Block if selectedSource is not null (i.e. gem is from inv/equipped)
        if (selectedSource !== null) {
            alert('Cannot duplicate a gem from inventory or equipped. Use drag-and-drop to move instead.');
            return;
        }
        draggedGem = selected;
        // Check element and type restriction
        if (String(draggedGem.element) !== String(elementId) || String(draggedGem.type) !== String(typeRestriction)) {
            alert(
                String(draggedGem.element) !== String(elementId)
                    ? `This slot only accepts gems of element ${getElementNameById(elementId)}.`
                    : `This slot only accepts Type ${getTypeDisplayName(typeRestriction)} gems.`
            );
            render();
            return;
        }
        // If slot filled, move old gem to inventory
        if (equipped[equippedIdx]) {
            const oldGem = equipped[equippedIdx];
            const free = inventory.findIndex(i => !i);
            if (free !== -1) {
                inventory[free] = oldGem;
            }
            // If no free slot, old gem is simply replaced (deleted)
        }
        equipped[equippedIdx] = draggedGem;
        render();
        return;
    }

    if (fromPane === 'inventory') {
        draggedGem = inventory[fromIdx];
        // Check element and type restriction
        if (String(draggedGem.element) !== String(elementId) || String(draggedGem.type) !== String(typeRestriction)) {
            inventory[fromIdx] = draggedGem; // Place back in inventory
            alert(
                String(draggedGem.element) !== String(elementId)
                    ? `This slot only accepts gems of element ${getElementNameById(elementId)}.`
                    : `This slot only accepts Type ${getTypeDisplayName(typeRestriction)} gems.`
            );
            render();
            return;
        }
        // If slot filled, move old gem to inventory[fromIdx]
        if (equipped[equippedIdx]) {
            const oldGem = equipped[equippedIdx];
            inventory[fromIdx] = oldGem;
        } else {
            inventory[fromIdx] = null;
        }
        equipped[equippedIdx] = draggedGem;
        // Unselect if just moved
        if (selected && draggedGem && selected.id === draggedGem.id) {
            selected = null;
            selectedSource = null;
        }
        render();
        return;
    }
}

async function massUpdateGemsRemote(gemArray) {
    try {
        const resp = await fetch('https://kiwiapi.aallyn.xyz/v2/gems/mass_update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ gems: gemArray })
        });
        if (!resp.ok) throw new Error('Failed to update gems');
        const data = await resp.json();
        // Only trust a response if it's a non-empty array matching your input length
        if (Array.isArray(data.gems) && data.gems.length === gemArray.length) {
            return data.gems;
        }
        return gemArray;
    } catch (e) {
        return gemArray;
    }
}


function renderInventory() {
    const inventoryEl = document.getElementById('inventory');
    inventoryEl.innerHTML = '';
    for (let idx = 0; idx < 150; idx++) {
        if (!inventory[idx]) inventory[idx] = null;
        const item = inventory[idx];
        const slot = document.createElement('div');
        slot.className = 'slot';
        slot.dataset.index = idx;
        slot.dataset.pane = 'inventory';
        slot.setAttribute('data-has-item', !!item);
        slot.ondragover = handleDragOver;
        slot.ondrop = handleDrop;
        if (item) {
            const itemEl = createItem(item, 'inventory', idx);
            slot.appendChild(itemEl);
        }
        inventoryEl.appendChild(slot);
    }

    // Remove existing update button to prevent duplicates
    let updateBtn = document.getElementById('update-gems-btn');
    if (updateBtn) updateBtn.remove();

    // Add "Update Gems" button below inventory
    updateBtn = document.createElement('button');
    updateBtn.id = 'update-gems-btn';
    updateBtn.innerText = 'Sync Gem Bases';

    // Styles
    updateBtn.style.display = 'block';
    updateBtn.style.margin = '24px auto 0 auto';
    updateBtn.style.padding = '12px 32px';
    updateBtn.style.fontSize = '1.2rem';
    updateBtn.style.background = 'linear-gradient(90deg, #6bffcb 0%, #3698f3 100%)';
    updateBtn.style.color = '#222';
    updateBtn.style.border = 'none';
    updateBtn.style.borderRadius = '8px';
    updateBtn.style.boxShadow = '0 2px 8px rgba(54,152,243,0.2)';
    updateBtn.style.cursor = 'pointer';
    updateBtn.style.fontWeight = 'bold';
    updateBtn.style.transition = 'background 0.3s, box-shadow 0.3s';
    updateBtn.onmouseover = function() {
        updateBtn.style.background = 'linear-gradient(90deg, #3698f3 0%, #6bffcb 100%)';
        updateBtn.style.boxShadow = '0 4px 16px rgba(54,152,243,0.3)';
    };
    updateBtn.onmouseout = function() {
        updateBtn.style.background = 'linear-gradient(90deg, #6bffcb 0%, #3698f3 100%)';
        updateBtn.style.boxShadow = '0 2px 8px rgba(54,152,243,0.2)';
    };

    updateBtn.onclick = async function() {
        // Store selection info
        let prevSelection = null;
        if (
            selected &&
            typeof selectedSource === "object" &&
            selectedSource !== null &&
            (
                (selectedSource.pane === "inventory" && typeof selectedSource.idx === "number" && inventory[selectedSource.idx] && inventory[selectedSource.idx].id === selected.id) ||
                (selectedSource.pane === "equipped" && typeof selectedSource.idx === "number" && equipped[selectedSource.idx] && equipped[selectedSource.idx].id === selected.id)
            )
        ) {
            prevSelection = { pane: selectedSource.pane, idx: selectedSource.idx, id: selected.id };
        }

        // Mass update inventory
        if (Array.isArray(inventory) && inventory.length > 0) {
            const updatedInventory = await massUpdateGemsRemote(inventory);
            inventory = updatedInventory;
            localStorage.setItem('inventory', JSON.stringify(inventory));
        }
        // Mass update equipped
        if (Array.isArray(equipped) && equipped.length > 0) {
            const updatedEquipped = await massUpdateGemsRemote(equipped);
            equipped = updatedEquipped;
            localStorage.setItem('equipped', JSON.stringify(equipped));
        }

        // Reselect gem if it is from inventory or equipped, otherwise clear selection
        if (prevSelection) {
            if (
                prevSelection.pane === "inventory" &&
                inventory[prevSelection.idx] &&
                inventory[prevSelection.idx].id === prevSelection.id
            ) {
                selected = inventory[prevSelection.idx];
                selectedSource = { pane: "inventory", idx: prevSelection.idx };
            } else if (
                prevSelection.pane === "equipped" &&
                equipped[prevSelection.idx] &&
                equipped[prevSelection.idx].id === prevSelection.id
            ) {
                selected = equipped[prevSelection.idx];
                selectedSource = { pane: "equipped", idx: prevSelection.idx };
            } else {
                selected = null;
                selectedSource = null;
            }
        } else {
            selected = null;
            selectedSource = null;
        }

        render();
    };
    inventoryEl.parentNode.insertBefore(updateBtn, inventoryEl.nextSibling);
}

// At top level, preserve selectedActionKey for the same gem
if (!window._selectedGemId) window._selectedGemId = null;
if (!window._selectedActionKey) window._selectedActionKey = null;

function renderSelected() {
    const selectedEl = document.getElementById('selected');
    selectedEl.innerHTML = '';
    if (!selected) return;

    // If gem changed, reset action
    if (window._selectedGemId !== selected.id) {
        window._selectedActionKey = null;
        window._selectedGemId = selected.id;
    }

    // Gem Name at top
    const nameDiv = document.createElement('div');
    nameDiv.style.textAlign = 'center';
    nameDiv.style.fontWeight = 'bold';
    nameDiv.style.fontSize = '1.3em';
    nameDiv.style.marginBottom = '10px';
    nameDiv.textContent = selected.gem_name || '(Unnamed Gem)';
    selectedEl.appendChild(nameDiv);

    // Side-by-side container (circle and details)
    const container = document.createElement('div');
    container.className = 'selected-container';

    // Left: Big gem circle
    const circle = document.createElement('div');
    circle.className = 'big-slot';
    circle.draggable = true;
    circle.ondragstart = function (e) {
        e.dataTransfer.setData('text/plain', JSON.stringify({
            fromPane: 'selected',
            fromIdx: 0,
        }));
    };
    const holder = document.createElement('div');
    holder.className = 'big-slot-inner-holder';
    const tierBg = document.createElement('img');
    tierBg.className = 'big-slot-tier-bg';
    tierBg.src = gemTierBgUrl(selected);
    tierBg.alt = '';
    holder.appendChild(tierBg);
    const gemImg = document.createElement('img');
    gemImg.className = 'big-slot-gem-img';
    gemImg.src = gemImageUrl(selected);
    gemImg.alt = '';
    holder.appendChild(gemImg);
    // if (selected.is_max_level) {
    //     const maxDiv = document.createElement('div');
    //     maxDiv.className = 'big-slot-max';
    //     maxDiv.textContent = '★';
    //     holder.appendChild(maxDiv);
    // }
    const lvDiv = document.createElement('div');
    lvDiv.className = 'big-slot-lv';
    lvDiv.textContent = `Lv.${selected.level}`;
    holder.appendChild(lvDiv);
    const powerDiv = document.createElement('div');
    powerDiv.className = 'big-slot-power';
    powerDiv.textContent = selected.power_rank;
    holder.appendChild(powerDiv);
    circle.appendChild(holder);
    container.appendChild(circle);

    // Right: Gem details (NO stats)
    const detailsPanel = document.createElement('div');
    detailsPanel.className = 'selected-panel-details selected-stats-square';
    detailsPanel.innerHTML = `
        <div class="gem-general">
            <div><b>Power:</b> ${selected.power_rank}</div>
            <div><b>Level:</b> ${selected.level}</div>
            <div><b>Type:</b> ${getTypeDisplayName(selected.type)}</div>
            <div><b>Tier:</b> ${getTierDisplayName(selected.tier)}</div>
            <div><b>Quality:</b> ${(selected.quality * 100).toFixed(1)}%</div>
        </div>
    `;
    // ${selected.is_max_level ? ' <span class="item-max">(MAX)</span>' : ''}
    container.appendChild(detailsPanel);
    selectedEl.appendChild(container);

    // --- Stat Column: Each Stat is a Column, Containers are Row Inside ---
    if (!window._selectedStatIdx) window._selectedStatIdx = 0;
    let selectedStatIdx = window._selectedStatIdx;

    const statCol = document.createElement('div');
    statCol.className = 'stat-list-column';

    (selected.stats || []).forEach((stat, statIdx) => {
        const statBox = document.createElement('div');
        statBox.className = 'stat-vert-square';
        statBox.tabIndex = 0;
        statBox.style.cursor = "pointer";
        statBox.style.transition = "box-shadow 0.15s, border-color 0.15s, opacity 0.15s";
        statBox.setAttribute("stat_type", stat.type);
        if (statIdx === selectedStatIdx) {
            statBox.classList.add('stat-vert-square-selected');
            statBox.style.boxShadow = "0 0 0 3px #b0ebff";
            statBox.style.borderColor = "#4fc3f7";
            statBox.style.opacity = 1;
        } else {
            statBox.style.boxShadow = "0 0 0 2px #bdf6c5";
            statBox.style.borderColor = "#bdf6c5";
            statBox.style.opacity = 0.5;
        }
        statBox.onclick = () => {
            window._selectedStatIdx = statIdx;
            renderSelected();
        };

        // Lock icon per stat
        if (stat.locked) {
            const lockIcon = document.createElement('span');
            lockIcon.className = 'stat-lock-icon';
            lockIcon.title = 'Locked';
            lockIcon.innerHTML = '🔒';
            statBox.appendChild(lockIcon);
        }

        // Stat label and augmentation % row (flex)
        const statLabelRow = document.createElement('div');
        statLabelRow.style.display = "flex";
        statLabelRow.style.justifyContent = "space-between";
        statLabelRow.style.alignItems = "center";

        // Stat label (left)
        const statTypeName = Object.keys(selected.stat_values[statIdx])[0] || `Stat ${statIdx + 1}`;
        const statValue = selected.stat_values[statIdx][statTypeName];
        const statLabel = document.createElement('div');
        statLabel.className = 'stat-label';
        statLabel.textContent = `${statValue !== undefined ? statValue.toFixed(2) : '0.00'} ${statTypeName}`;
        statLabelRow.appendChild(statLabel);

        // Augmentation progress (right)
        const augPct = document.createElement('div');
        augPct.className = 'stat-augment-pct';
        augPct.style.fontWeight = 'bold';
        augPct.style.color = '#4fc3f7';
        augPct.style.marginBottom = '10px';
        augPct.style.marginLeft = '10px';
        augPct.style.position = 'absolute';
        augPct.style.right = '40px';
        augPct.textContent = `${((stat.augmentation_progress || 0) * 100).toFixed(2)}%`;
        statLabelRow.appendChild(augPct);

        statBox.appendChild(statLabelRow);

        // Containers row (inside stat square)
        const containerRow = document.createElement('div');
        containerRow.className = 'container-chip-row';

        (stat.containers || []).forEach((container) => {
            const chip = document.createElement('div');
            chip.className = 'container-chip-vert';

            // Percentage value
            const pct = document.createElement('div');
            pct.className = 'container-chip-val';
            pct.textContent = `${(container.real_value * 100).toFixed(2)}%`;
            chip.appendChild(pct);

            // Progress bar (color per container value)
            const barWrap = document.createElement('div');
            barWrap.className = 'container-chip-bar-wrap';
            const bar = document.createElement('div');
            bar.className = 'container-chip-bar';

            let v = container.value;
            if (v < 0.33) {
                bar.style.background = 'linear-gradient(90deg, #f44336, #ff8a65)';
            } else if (v < 0.66) {
                bar.style.background = 'linear-gradient(90deg, #ffeb3b, #fbc02d)';
            } else {
                bar.style.background = 'linear-gradient(90deg, #4fc3f7, #43a047 70%)';
            }
            bar.style.width = `${(v * 100).toFixed(1)}%`;
            barWrap.appendChild(bar);
            chip.appendChild(barWrap);

            containerRow.appendChild(chip);
        });

        statBox.appendChild(containerRow);
        statCol.appendChild(statBox);
    });

    selectedEl.appendChild(statCol);

    // --- Action Selection Row ---
    const buttonRow = document.createElement('div');
    buttonRow.className = "button-row";
    buttonRow.style.display = "flex";
    buttonRow.style.alignItems = "center";
    buttonRow.style.marginTop = "10px";
    buttonRow.style.gap = "10px";
    buttonRow.style.justifyContent = "center";
    const actionGroup = document.createElement('div');
    actionGroup.className = 'action-group';
    actionGroup.style.display = 'flex';
    actionGroup.style.gap = '8px';
    const allSquares = [];

    // Use persistent selectedActionKey
    let selectedActionKey = window._selectedActionKey;

    // Augments
    const augmentTypes = Object.entries(GEM_LOOKUPS.augment_types || {}).sort((a, b) => a[1] - b[1]);
    augmentTypes.forEach(([name, id]) => {
        const square = document.createElement('div');
        square.className = 'action-square';
        square.tabIndex = 0;
        square.title = name;
        square.dataset.actionKey = `augment-${id}`;
        const img = document.createElement('img');
        img.src = `https://trove.aallyn.xyz/assets/gems/augments/${id}.png`;
        img.alt = name;
        img.style.width = '40px';
        img.style.height = '40px';
        img.style.display = 'block';
        square.appendChild(img);

        if (selectedActionKey === `augment-${id}`) {
            square.classList.add('selected');
        }

        square.onclick = () => {
            window._selectedActionKey = square.dataset.actionKey;
            renderSelected();
        };
        allSquares.push(square);
        actionGroup.appendChild(square);
    });
    // Separator
    const sep = document.createElement('div');
    sep.className = 'action-separator';
    sep.style.width = "2px";
    sep.style.height = "44px";
    sep.style.margin = "0 12px";
    sep.style.background = "rgba(0,180,255,0.25)";
    sep.style.borderRadius = "2px";
    actionGroup.appendChild(sep);
    // Modifiers
    [
        { key: 'spark', url: 'https://trove.aallyn.xyz/assets/gems/modifiers/spark.png', label: 'Spark' },
        { key: 'flare', url: 'https://trove.aallyn.xyz/assets/gems/modifiers/flare.png', label: 'Flare' }
    ].forEach(mod => {
        const square = document.createElement('div');
        square.className = 'action-square';
        square.tabIndex = 0;
        square.title = mod.label;
        square.dataset.actionKey = mod.key;
        const img = document.createElement('img');
        img.src = mod.url;
        img.alt = mod.label;
        img.style.width = '40px';
        img.style.height = '40px';
        img.style.display = 'block';
        square.appendChild(img);

        if (selectedActionKey === mod.key) {
            square.classList.add('selected');
        }

        square.onclick = () => {
            window._selectedActionKey = square.dataset.actionKey;
            renderSelected();
        };
        allSquares.push(square);
        actionGroup.appendChild(square);
    });
    buttonRow.appendChild(actionGroup);

    // Add action selection menu row first (before buttons)
    selectedEl.appendChild(buttonRow);

    // --- Action + Level Up Buttons Row ---
    const actionsRow = document.createElement('div');
    actionsRow.className = 'gem-actions-row';

    // Level Up Button
    let levelUpBtn = null;
    if (!selected.is_max_level) {
        levelUpBtn = document.createElement('button');
        levelUpBtn.textContent = 'Level Up';
        levelUpBtn.className = 'gem-action-btn';
        levelUpBtn.onclick = async () => {
            levelUpBtn.disabled = true;
            levelUpBtn.textContent = 'Leveling...';
            try {
                const resp = await fetch('https://kiwiapi.aallyn.xyz/v2/gems/level_up', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ gem: selected })
                });
                if (!resp.ok) throw new Error('Network error');
                const upgraded = await resp.json();
                selected = upgraded;
                if (selectedSource && selectedSource.pane === 'inventory' && selectedSource.idx != null) {
                    inventory[selectedSource.idx] = upgraded;
                }
                if (selectedSource && selectedSource.pane === 'equipped' && selectedSource.idx != null) {
                    equipped[selectedSource.idx] = upgraded;
                }
                render();
            } catch (err) {
                alert('Could not level up gem.');
            } finally {
                levelUpBtn.disabled = false;
                levelUpBtn.textContent = 'Level Up';
            }
        };
        actionsRow.appendChild(levelUpBtn);
    }

    // Action Button
    const actionBtn = document.createElement('button');
    actionBtn.className = 'gem-action-btn';
    actionBtn.disabled = !selectedActionKey; // Disabled if no action selected

    function updateActionButton() {
        actionBtn.disabled = !window._selectedActionKey;
        // Use selectedActionKey to determine label
        if (!window._selectedActionKey) {
            actionBtn.textContent = 'Augment Stat';
        } else if (window._selectedActionKey === 'spark') {
            actionBtn.textContent = 'Change Stat';
        } else if (window._selectedActionKey === 'flare') {
            actionBtn.textContent = 'Move Boost';
        } else {
            actionBtn.textContent = 'Augment Stat';
        }
    }
    updateActionButton();

    actionBtn.onclick = async () => {
        if (!window._selectedActionKey) return;

        // Get selected stat info from DOM attribute
        const statCol = document.querySelector('.stat-list-column');
        const statBoxes = statCol.querySelectorAll('.stat-vert-square');
        const selectedStatBox = statBoxes[window._selectedStatIdx];
        const statTypeId = selectedStatBox.getAttribute('stat_type');

        let url = '';
        let payload = {
            gem: selected,
            stat: parseInt(statTypeId)
        };

        if (window._selectedActionKey.startsWith('augment-')) {
            url = 'https://kiwiapi.aallyn.xyz/v2/gems/augment';
            const augmentId = window._selectedActionKey.split('-')[1];
            payload.augment = parseInt(augmentId);
        } else if (window._selectedActionKey === 'spark') {
            url = 'https://kiwiapi.aallyn.xyz/v2/gems/spark';
        } else if (window._selectedActionKey === 'flare') {
            url = 'https://kiwiapi.aallyn.xyz/v2/gems/flare';
        }

        actionBtn.disabled = true;
        actionBtn.textContent = 'Working...';

        try {
            const resp = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (!resp.ok) throw new Error('Network error');
            const result = await resp.json();
            selected = result;
            if (selectedSource && selectedSource.pane === 'inventory' && selectedSource.idx != null) {
                inventory[selectedSource.idx] = result;
            }
            if (selectedSource && selectedSource.pane === 'equipped' && selectedSource.idx != null) {
                equipped[selectedSource.idx] = result;
            }
            // Do not reset action key on rerender!
            render();
        } catch (err) {
            alert('Action failed.');
        } finally {
            updateActionButton();
        }
    };

    actionsRow.appendChild(actionBtn);

    // Insert the buttons row after the action selection row
    selectedEl.appendChild(actionsRow);

    // Save gem to inventory button (if not present)
    const inInventory = selected.id !== undefined && inventory.some(item => item && item.id === selected.id);
    const inEquipped = selected.id !== undefined && equipped.some(item => item && item.id === selected.id);
    if (
        selected.id !== undefined &&
        !inInventory &&
        !inEquipped
    ) {
        const saveBtn = document.createElement('button');
        saveBtn.className = 'save-gem-btn';
        saveBtn.type = 'button';
        saveBtn.textContent = 'Add to Inventory';
        saveBtn.onclick = () => {
            const emptyIdx = inventory.findIndex(i => !i);
            if (emptyIdx === -1) {
                alert('Inventory is full.');
                return;
            }
            inventory[emptyIdx] = JSON.parse(JSON.stringify(selected));
            render();
        };
        selectedEl.appendChild(saveBtn);
    }
}

function renderTrashSlot() {
    const trashContainer = document.getElementById('trash-slot-container');
    trashContainer.innerHTML = '';
    const trashSlot = document.createElement('div');
    trashSlot.className = 'trash-slot';
    trashSlot.title = "Drag a gem here to delete";
    trashSlot.ondragover = (e) => { e.preventDefault(); };
    trashSlot.ondrop = function (e) {
        e.preventDefault();
        const { fromPane, fromIdx } = JSON.parse(e.dataTransfer.getData('text/plain'));
        let item = null;
        if (fromPane === 'equipped') {
            item = equipped[fromIdx];
        } else if (fromPane === 'inventory') {
            item = inventory[fromIdx];
        }
        if (!item) return;
        if (confirm('Are you sure you want to delete this gem?')) {
            if (fromPane === 'equipped') {
                equipped[fromIdx] = null;
            } else if (fromPane === 'inventory') {
                inventory[fromIdx] = null;
            }
            if (selected && selected.id === item.id) selected = null;
            render();
        }
    };
    const trashIcon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    trashIcon.setAttribute("viewBox", "0 0 24 24");
    trashIcon.setAttribute("class", "trash-icon");
    trashIcon.innerHTML = `
                <path fill="#c62828" d="M9,3V4H4V6H5V19A2,2 0 0,0 7,21H17A2,2 0 0,0 19,19V6H20V4H15V3H9M7,6H17V19H7V6Z"/>
            `;
    trashSlot.appendChild(trashIcon);
    const label = document.createElement('div');
    label.className = 'trash-label';
    label.textContent = "Trash";
    trashContainer.appendChild(trashSlot);
    trashContainer.appendChild(label);
}

function createItem(item, fromPane, fromIdx) {
    const itemEl = document.createElement('div');
    itemEl.className = 'item';
    itemEl.draggable = true;

    // MOUSE WHEEL (MIDDLE CLICK) DELETION
    itemEl.addEventListener('mousedown', function (e) {
        if (e.button === 1) { // Middle mouse button
            e.preventDefault(); // Prevent scroll
            // Delete without confirmation
            if (fromPane === 'inventory') {
                inventory[fromIdx] = null;
            } else if (fromPane === 'equipped') {
                equipped[fromIdx] = null;
            }
            if (selected && selected.id === item.id) selected = null;
            render();
            return false;
        }
    });

    const imgHolder = document.createElement('div');
    imgHolder.className = 'item-img-holder';
    const tierBg = document.createElement('img');
    tierBg.className = 'item-tier-bg';
    tierBg.src = gemTierBgUrl(item);
    tierBg.alt = '';
    imgHolder.appendChild(tierBg);
    const gemImg = document.createElement('img');
    gemImg.className = 'item-gem-img';
    gemImg.src = gemImageUrl(item);
    gemImg.alt = '';
    imgHolder.appendChild(gemImg);
    // if (item.is_max_level) {
    //     const maxDiv = document.createElement('div');
    //     maxDiv.className = 'item-max';
    //     maxDiv.textContent = '★';
    //     imgHolder.appendChild(maxDiv);
    // }
    const lvDiv = document.createElement('div');
    lvDiv.className = 'item-lv';
    lvDiv.textContent = `Lv.${item.level}`;
    imgHolder.appendChild(lvDiv);
    const powerDiv = document.createElement('div');
    powerDiv.className = 'item-power';
    powerDiv.textContent = item.power_rank;
    imgHolder.appendChild(powerDiv);
    itemEl.appendChild(imgHolder);
    itemEl.dataset.fromPane = fromPane;
    itemEl.dataset.fromIdx = fromIdx;
    itemEl.ondragstart = handleDragStart;
    itemEl.onclick = () => {
        selected = item;
        selectedSource = { pane: fromPane, idx: fromIdx }; // Add this line
        render();
    };
    return itemEl;
}

function handleDragStart(e) {
    let target = e.target;
    while (target && !target.classList.contains('item')) target = target.parentElement;
    if (!target) return;
    e.dataTransfer.setData('text/plain', JSON.stringify({
        fromPane: target.dataset.fromPane,
        fromIdx: target.dataset.fromIdx
    }));
}
function handleDragOver(e) { e.preventDefault(); }
function handleDrop(e) {
    e.preventDefault();
    const { fromPane, fromIdx } = JSON.parse(e.dataTransfer.getData('text/plain'));
    const toPane = this.dataset.pane;
    const toIdx = this.dataset.index;

    // Prevent dropping into same slot
    if (fromPane === toPane && fromIdx === toIdx) return;

    let draggedGem = null;

    if (fromPane === 'equipped') {
        draggedGem = equipped[fromIdx];
        // Move to empty inventory slot
        if (toPane === 'inventory' && !inventory[toIdx]) {
            equipped[fromIdx] = null;
            inventory[toIdx] = draggedGem;
            // Unselect if just moved
            if (selected && draggedGem && selected.id === draggedGem.id) {
                selected = null;
                selectedSource = null;
            }
            render();
            return;
        }
        // Swap with inventory gem
        if (toPane === 'inventory' && inventory[toIdx]) {
            // Find equipped slot restriction
            const equippedRows = getEquippedRows();
            let found = false, restrictType = null, restrictElement = null;
            for (const row of equippedRows) {
                for (const slot of row.slots) {
                    if (slot.slotIdx == fromIdx) {
                        restrictType = slot.typeRestriction;
                        restrictElement = row.elementId;
                        found = true;
                        break;
                    }
                }
                if (found) break;
            }
            const inventoryGem = inventory[toIdx];
            if (
                String(inventoryGem.element) === String(restrictElement) &&
                String(inventoryGem.type) === String(restrictType)
            ) {
                // Swap
                equipped[fromIdx] = inventoryGem;
                inventory[toIdx] = draggedGem;
                // Unselect if just moved
                if (selected && draggedGem && selected.id === draggedGem.id) {
                    selected = null;
                    selectedSource = null;
                }
                if (selected && inventoryGem && selected.id === inventoryGem.id) {
                    selected = null;
                    selectedSource = null;
                }
                render();
                return;
            } else {
                alert("Gem is incompatible with this equipped slot.");
                render();
                return;
            }
        }
    }

    // Existing logic for inventory→inventory swap
    if (fromPane === 'inventory') {
        draggedGem = inventory[fromIdx];
        if (toPane === 'inventory' && inventory[toIdx]) {
            const temp = inventory[toIdx];
            inventory[toIdx] = draggedGem;
            inventory[fromIdx] = temp;
            // Unselect if just moved
            if (selected && draggedGem && selected.id === draggedGem.id) {
                selected = null;
                selectedSource = null;
            }
            if (selected && temp && selected.id === temp.id) {
                selected = null;
                selectedSource = null;
            }
            render();
            return;
        }
        if (toPane === 'inventory' && !inventory[toIdx]) {
            inventory[fromIdx] = null;
            inventory[toIdx] = draggedGem;
            // Unselect if just moved
            if (selected && draggedGem && selected.id === draggedGem.id) {
                selected = null;
                selectedSource = null;
            }
            render();
            return;
        }
    }

    // Selected→inventory
    if (fromPane === 'selected') {
        // Block if selectedSource is not null (i.e. gem is from inv/equipped)
        if (selectedSource !== null) {
            alert('Cannot duplicate a gem from inventory or equipped. Use drag-and-drop to move instead.');
            return;
        }
        if (toPane === 'inventory' && !inventory[toIdx]) {
            inventory[toIdx] = JSON.parse(JSON.stringify(selected));
            render();
            return;
        }
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const augmentSlider = document.getElementById('gem-augment-slider');
    const augmentValue = document.getElementById('gem-augment-value');
    const augmentNull = document.getElementById('gem-augment-null');
    if (augmentNull && augmentSlider && augmentValue) {
        // Start disabled if checked
        if (augmentNull.checked) {
            augmentSlider.disabled = true;
            augmentValue.textContent = '—';
        }
        augmentNull.addEventListener('change', function () {
            if (this.checked) {
                augmentSlider.disabled = true;
                augmentValue.textContent = '—';
            } else {
                augmentSlider.disabled = false;
                augmentValue.textContent = augmentSlider.value;
            }
        });
        augmentSlider.addEventListener('input', function () {
            if (!augmentNull.checked) {
                augmentValue.textContent = augmentSlider.value;
            }
        });
    }
});

document.getElementById('gem-form').addEventListener('submit', async function (e) {
    e.preventDefault();
    const button = this.querySelector('button');
    button.disabled = true;
    button.textContent = 'Generating...';

    // Read form values and convert to integers if present
    const typeVal = document.getElementById('gem-type').value;
    const tierVal = document.getElementById('gem-tier').value;
    const elementVal = document.getElementById('gem-element').value;
    const restrictionVal = document.getElementById('gem-restriction').value;

    // --- Read sliders ---
    const levelVal = document.getElementById('gem-level-slider').value;

    let body = {};
    if (typeVal) body.type = parseInt(typeVal, 10);
    if (tierVal) body.tier = parseInt(tierVal, 10);
    if (elementVal) body.element = parseInt(elementVal, 10);
    const restrictionSelect = document.getElementById('gem-restriction');
    if (!restrictionSelect.disabled && restrictionVal) {
        body.restriction = parseInt(restrictionVal, 10);
    }
    // --- Add sliders to body ---
    const augmentNull = document.getElementById('gem-augment-null');
    const augmentVal = document.getElementById('gem-augment-slider').value;
    if (levelVal) body.level = parseInt(levelVal, 10);
    if (augmentNull && augmentNull.checked) {
        body.augmentation = null;
    } else if (augmentVal) {
        body.augmentation = parseInt(augmentVal, 10) / 100;
    }

    try {
        const resp = await fetch('https://kiwiapi.aallyn.xyz/v2/gems/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!resp.ok) throw new Error('Network error');
        const gem = await resp.json();
        selected = gem;
        selectedSource = null; // Clear any old source
        render();
    } catch (err) {
        alert('Could not generate gem.');
    } finally {
        button.disabled = false;
        button.textContent = 'Generate Random Gem';
    }
});

render();
console.log("Loaded gem engine");