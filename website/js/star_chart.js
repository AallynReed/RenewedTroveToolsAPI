/* =========================================================
   Star Chart – Hierarchical Layout Implementation
   ---------------------------------------------------------
   Adds full recursive (sector + concentric rings) layout
   so ALL nodes in star_chart_data are positioned & selectable.
   ========================================================= */

/* ---------- Configurable Constants ---------- */
const SC_MAX_ACTIVATED = 40;
const SC_NODE_RADII = { Root: 34, Major: 22, Minor: 14 };
const SC_ANIMATION_ENABLED = true;
const SPACING_MULT = 18;

/* Sector layout params */
const SECTOR_GAP_RADIANS = 0.10;          // gap between root sectors
const MARGIN_CANVAS = 48;                 // min free space to border
const ROOT_RING_EXTRA = 1.2;              // root ring = levelGap * this
const LABEL_OFFSET = 4;                   // px below node
const EDGE_WIDTH = 2.2;

/* Zoom / Pan */
const ZOOM_DEFAULT = 1;
const ZOOM_MIN = 0.35;
const ZOOM_MAX = 2.75;
const ZOOM_STEP = 0.10;

/* ---------- Internal State ---------- */
let scCanvas, scCtx;
let scCenter = { x: 0, y: 0 };
let scActivated = new Set();
let scHoverPath = null;
let scPan = { x: 0, y: 0 };
let scIsPanning = false;
let scPanDragOrigin = { x: 0, y: 0 };
let scPanPointerStart = { x: 0, y: 0 };
let scZoom = ZOOM_DEFAULT;
let scRafId = 0;

/* Panels / tooltip */
let panelLeft, panelRight, tooltipEl;

/* Data + indices */
let scData = null;            // reference to star_chart_data
let scAllNodes = [];          // flat list of every node object
let scIndex = new Map();      // path -> node
let scParent = new Map();     // path -> parent path (null if root)
let scDepth = new Map();      // path -> integer depth (root=0)
let scRoots = [];             // array of root node objects (data objects themselves)

/* Hit test refs */
let scNodeRefs = [];          // current frame screen-space info

/* =========================================================
   Initialization
   ========================================================= */
document.addEventListener('DOMContentLoaded', () => {
  if (typeof star_chart_data === 'undefined') {
    console.warn('[StarChart] star_chart_data not defined.');
    return;
  }
  scData = star_chart_data;
  scCanvas = document.getElementById('star-chart-canvas');
  if (!scCanvas) return;
  scCtx = scCanvas.getContext('2d');

  ensurePanels();
  ensureTooltip();
  bindOverlayButtons();
  bindCanvasEvents();
  bindWindowEvents();

  buildIndices();     // build index of all nodes (structure)
  resizeCanvas();
  computeLayout();     // position every node
  draw();
});

/* =========================================================
   Panel / Tooltip Provisioning
   ========================================================= */
function ensurePanels() {
  const modal = document.getElementById('star-chart-modal');
  if (!modal) return;
  panelLeft = document.getElementById('star-chart-left-panel');
  if (!panelLeft) {
    panelLeft = document.createElement('div');
    panelLeft.id = 'star-chart-left-panel';
    panelLeft.className = 'star-chart-panel';
    modal.insertBefore(panelLeft, scCanvas);
  }
  panelRight = document.getElementById('star-chart-right-panel');
  if (!panelRight) {
    panelRight = document.createElement('div');
    panelRight.id = 'star-chart-right-panel';
    panelRight.className = 'star-chart-panel';
    modal.appendChild(panelRight);
  }
  renderLeftPanel();
  renderRightPanel(null);
}
function ensureTooltip() {
  tooltipEl = document.getElementById('star-chart-tooltip');
  if (!tooltipEl) {
    tooltipEl = document.createElement('div');
    tooltipEl.id = 'star-chart-tooltip';
    document.body.appendChild(tooltipEl);
  }
}

/* =========================================================
   Data Indexing
   ========================================================= */
function buildIndices() {
  scAllNodes = [];
  scIndex.clear();
  scParent.clear();
  scDepth.clear();
  scRoots = [];

  if (!scData) return;
  const roots = Object.values(scData);

  function traverse(node, parentPath, depth) {
    scAllNodes.push(node);
    scIndex.set(node.Path, node);
    scParent.set(node.Path, parentPath);
    scDepth.set(node.Path, depth);
    if (!node.Type) node.Type = parentPath == null ? 'Root' : 'Minor';
    if (depth === 0) scRoots.push(node);
    (node.Stars || []).forEach(child => traverse(child, node.Path, depth + 1));
  }

  roots.forEach(root => traverse(root, null, 0));
}

/* =========================================================
   Layout Algorithm (Sector + Concentric Rings)
   ---------------------------------------------------------
   1. Divide full circle into sectors for each root (with small gaps).
   2. For each root sector, distribute nodes at each depth evenly
      over that sector on their depth ring.
   3. Depth ring spacing auto-scales to fit canvas.
   ========================================================= */
function resizeCanvas() {
  const modal = document.getElementById('star-chart-modal');
  if (!modal) return;
  const rect = modal.getBoundingClientRect();
  const leftW = panelLeft ? panelLeft.offsetWidth : 0;
  const rightW = panelRight ? panelRight.offsetWidth : 0;

  const cssW = rect.width - leftW - rightW;
  const cssH = rect.height;
  const dpr = window.devicePixelRatio || 1;

  scCanvas.style.width = cssW + 'px';
  scCanvas.style.height = cssH + 'px';
  scCanvas.width = Math.round(cssW * dpr);
  scCanvas.height = Math.round(cssH * dpr);

  scCtx.scale(dpr, dpr); // Apply once here
  // NOTE: After doing this, remove the scale(dpr,dpr) interplay in draw().
  // You’d also need to reset transform at start of draw(): scCtx.setTransform(dpr,0,0,dpr,0,0);

  scCenter = { x: cssW / 2, y: cssH / 2 };
}

function computeLayout() {
  if (!scAllNodes.length) return;

  // Max depth present
  let maxDepth = 0;
  scAllNodes.forEach(n => {
    const d = scDepth.get(n.Path);
    if (d > maxDepth) maxDepth = d;
  });

  const minDim = Math.min(scCanvas.width, scCanvas.height);
  const maxRadiusAvail = minDim / 2 - MARGIN_CANVAS;

  // Base (unscaled) spacing
  const baseLevelGap = maxRadiusAvail / (maxDepth + 2);           // original formula
  const baseRootRingRadius = baseLevelGap * ROOT_RING_EXTRA;
  const baseMaxRingRadius = baseRootRingRadius + maxDepth * baseLevelGap;

  // Desired scaled spacing
  const desiredRootRingRadius = baseRootRingRadius * SPACING_MULT;
  const desiredMaxRingRadius = desiredRootRingRadius + maxDepth * baseLevelGap * SPACING_MULT;

  // Clamp scale so deepest ring fits
  let appliedScale;
  if (desiredMaxRingRadius <= maxRadiusAvail) {
    appliedScale = SPACING_MULT;
  } else {
    // Scale down proportionally to fit
    appliedScale = maxRadiusAvail / baseMaxRingRadius;
  }

  const rootRingRadius = baseRootRingRadius * appliedScale;
  const levelGap = baseLevelGap * appliedScale;

  // Sector calculations (unchanged logic)
  const rootCount = scRoots.length;
  if (!rootCount) return;
  const totalGap = rootCount * SECTOR_GAP_RADIANS;
  const usableAngle = Math.PI * 2 - totalGap;
  const sectorSpan = usableAngle / rootCount;

  // Group nodes per root by depth
  const perRootBuckets = new Map();
  scRoots.forEach(root => perRootBuckets.set(root.Path, new Map()));

  scAllNodes.forEach(n => {
    const depth = scDepth.get(n.Path);
    if (depth === 0) return; // root itself handled separately
    // Ascend to root
    let rootPath = n.Path;
    while (scParent.get(rootPath)) rootPath = scParent.get(rootPath);
    const depthMap = perRootBuckets.get(rootPath);
    if (!depthMap.has(depth)) depthMap.set(depth, []);
    depthMap.get(depth).push(n);
  });

  let currentStartAngle = -Math.PI / 2;
  scRoots.forEach(root => {
    const startAngle = currentStartAngle;
    const endAngle = startAngle + sectorSpan;
    const midAngle = (startAngle + endAngle) / 2;

    // Position root on its ring
    root._x = scCenter.x + rootRingRadius * Math.cos(midAngle);
    root._y = scCenter.y + rootRingRadius * Math.sin(midAngle);
    root._sector = { start: startAngle, end: endAngle };

    // Descendants
    const bucketMap = perRootBuckets.get(root.Path);
    if (bucketMap) {
      for (const [depthStr, nodesAtDepth] of [...bucketMap.entries()].sort((a,b)=>a[0]-b[0])) {
        const depth = Number(depthStr);
        const ringRadius = rootRingRadius + depth * levelGap;
        const count = nodesAtDepth.length;
        const pad = (endAngle - startAngle) * 0.08;
        const usable = (endAngle - startAngle) - pad * 2;
        nodesAtDepth.forEach((node, idx) => {
          const angle = startAngle + pad + usable * (idx + 1) / (count + 1);
          node._angle = angle;
          node._x = scCenter.x + ringRadius * Math.cos(angle);
          node._y = scCenter.y + ringRadius * Math.sin(angle);
        });
      }
    }

    currentStartAngle = endAngle + SECTOR_GAP_RADIANS;
  });
}

/* =========================================================
   Drawing
   ========================================================= */
function scheduleDraw() {
  if (SC_ANIMATION_ENABLED) {
    if (scRafId) cancelAnimationFrame(scRafId);
    scRafId = requestAnimationFrame(draw);
  } else draw();
}

function draw() {
  scNodeRefs = [];
  scCtx.clearRect(0, 0, scCanvas.width, scCanvas.height);
  scCtx.save();

  // Correct order: translate then scale
  scCtx.translate(scPan.x, scPan.y);
  scCtx.scale(scZoom, scZoom);

  drawCenterNode();
  drawEdges();
  drawAllNodes();

  scCtx.restore();
}


function drawCenterNode() {
  // Visual central anchor (not a data node)
  scCtx.beginPath();
  scCtx.arc(scCenter.x, scCenter.y, SC_NODE_RADII.Root, 0, Math.PI * 2);
  scCtx.fillStyle = '#34d058';
  scCtx.fill();
  scCtx.lineWidth = 2;
  scCtx.strokeStyle = '#ffffff';
  scCtx.stroke();

  scCtx.fillStyle = '#ffffff';
  scCtx.font = 'bold 16px sans-serif';
  scCtx.textAlign = 'center';
  scCtx.textBaseline = 'middle';
  scCtx.fillText('Star Chart', scCenter.x, scCenter.y);
}

function drawEdges() {
  scCtx.lineWidth = EDGE_WIDTH;
  scCtx.strokeStyle = '#6d7785';
  scCtx.lineCap = 'round';

  scAllNodes.forEach(node => {
    const parentPath = scParent.get(node.Path);
    if (parentPath == null) return; // root
    const parent = scIndex.get(parentPath);
    if (!parent || parent._x == null || node._x == null) return;

    const r1 = SC_NODE_RADII[parent.Type] || 12;
    const r2 = SC_NODE_RADII[node.Type] || 12;
    const dx = node._x - parent._x;
    const dy = node._y - parent._y;
    const dist = Math.hypot(dx, dy) || 1;
    const sx = parent._x + dx * (r1 / dist);
    const sy = parent._y + dy * (r1 / dist);
    const ex = node._x - dx * (r2 / dist);
    const ey = node._y - dy * (r2 / dist);

    scCtx.beginPath();
    scCtx.moveTo(sx, sy);
    scCtx.lineTo(ex, ey);
    scCtx.stroke();
  });
}

function drawAllNodes() {
  scAllNodes.forEach(node => {
    if (node._x == null) return;
    drawNode(node);
  });
}

function drawNode(node) {
  const type = node.Type || 'Minor';
  const r = SC_NODE_RADII[type] || 12;
  const isActive = scActivated.has(node.Path);
  const isHover = scHoverPath === node.Path;
  let fill;
  if (type === 'Root') fill = '#1f8b4c';
  else if (type === 'Major') fill = '#283593';
  else fill = '#0097a7';
  if (isActive) fill = '#43a047';
  if (isHover) fill = '#fbc02d';

  scCtx.beginPath();
  scCtx.arc(node._x, node._y, r, 0, Math.PI * 2);
  scCtx.fillStyle = fill;
  scCtx.fill();
  scCtx.lineWidth = 2;
  scCtx.strokeStyle = '#ffffff';
  scCtx.stroke();

  scCtx.font = 'bold 11px sans-serif';
  scCtx.fillStyle = '#ffffff';
  scCtx.textAlign = 'center';
  scCtx.textBaseline = 'top';
  scCtx.fillText(node.Name || node.Constellation || '', node._x, node._y + r + LABEL_OFFSET);

  scNodeRefs.push({ path: node.Path, node, x: node._x, y: node._y, r });
}

/* =========================================================
   Interaction
   ========================================================= */
function bindOverlayButtons() {
  const openBtn = document.getElementById('open-star-chart-btn');
  const closeBtn = document.getElementById('close-star-chart-btn');
  const overlay = document.getElementById('star-chart-overlay');

  if (openBtn) openBtn.addEventListener('click', () => {
    overlay.style.display = 'flex';
    resizeCanvas();
    computeLayout();
    draw();
  });

  if (closeBtn) closeBtn.addEventListener('click', () => {
    overlay.style.display = 'none';
    hideTooltip();
  });

  window.addEventListener('keydown', e => {
    if (e.key === 'Escape' && overlay.style.display !== 'none') {
      overlay.style.display = 'none';
      hideTooltip();
    }
  });
}

function bindCanvasEvents() {
  scCanvas.addEventListener('mousedown', onPointerDown);
  window.addEventListener('mousemove', onPointerMove);
  window.addEventListener('mouseup', onPointerUp);
  scCanvas.addEventListener('wheel', onWheelZoom, { passive: false });
  scCanvas.addEventListener('mousemove', onHover);
  scCanvas.addEventListener('mouseleave', () => {
    scHoverPath = null;
    hideTooltip();
    scheduleDraw();
  });
  scCanvas.addEventListener('click', onClickActivate);
  scCanvas.addEventListener('touchstart', onTouchStart, { passive: false });
  scCanvas.addEventListener('touchmove', onTouchMove, { passive: false });
  scCanvas.addEventListener('touchend', onTouchEnd, { passive: false });
}

function bindWindowEvents() {
  window.addEventListener('resize', () => {
    const overlay = document.getElementById('star-chart-overlay');
    if (overlay && overlay.style.display !== 'none') {
      resizeCanvas();
      computeLayout();
      draw();
    }
  });
}

/* Hover */
function onHover(e) {
  const ref = findNodeAt(e.clientX, e.clientY);
  const newHover = ref ? ref.path : null;
  if (newHover !== scHoverPath) {
    scHoverPath = newHover;
    scheduleDraw();
    if (ref) {
      showTooltipForNode(ref, e.clientX, e.clientY);
      renderRightPanel(ref.node);
    } else {
      hideTooltip();
      renderRightPanel(null);
    }
  } else if (ref) {
    positionTooltip(e.clientX, e.clientY);
  }
}

/* Activation logic */
function onClickActivate(e) {
  const ref = findNodeAt(e.clientX, e.clientY);
  if (!ref) return;
  const node = ref.node;
  if (node.Type === 'Root') return; // do not activate roots

  if (scActivated.has(node.Path)) {
    deactivateNodeCascade(node.Path);
  } else {
    // parent must be active or root
    const parentPath = scParent.get(node.Path);
    if (parentPath) {
      const parentNode = scIndex.get(parentPath);
      if (parentNode.Type !== 'Root' && !scActivated.has(parentPath)) return;
    }
    if (scActivated.size >= SC_MAX_ACTIVATED) return;
    activateNode(node);
  }
  renderLeftPanel();
  scheduleDraw();
}

function activateNode(node) {
  scActivated.add(node.Path);
  // Handle Overwrites: deactivate listed paths and their descendants
  if (Array.isArray(node.Overwrites)) {
    node.Overwrites.forEach(path => {
      if (scIndex.has(path)) deactivateNodeCascade(path);
    });
  }
}

function deactivateNodeCascade(path) {
  // Remove path and ALL descendants
  function dfs(p) {
    scActivated.delete(p);
    scAllNodes.forEach(n => {
      if (scParent.get(n.Path) === p) dfs(n.Path);
    });
  }
  dfs(path);
}

/* Pan */
function onPointerDown(e) {
  if (e.button !== 0) return;
  scIsPanning = true;
  scCanvas.classList.add('grabbing');
  scPanDragOrigin = { x: scPan.x, y: scPan.y };
  scPanPointerStart = { x: e.clientX, y: e.clientY };
}
function onPointerMove(e) {
  if (!scIsPanning) return;
  scPan.x = scPanDragOrigin.x + (e.clientX - scPanPointerStart.x);
  scPan.y = scPanDragOrigin.y + (e.clientY - scPanPointerStart.y);
  scheduleDraw();
}
function onPointerUp() {
  scIsPanning = false;
  scCanvas.classList.remove('grabbing');
}

/* Zoom (wheel) */
function onWheelZoom(e) {
  if (!e.ctrlKey) e.preventDefault();
  const delta = e.deltaY;
  let target = scZoom * (delta > 0 ? (1 - ZOOM_STEP) : (1 + ZOOM_STEP));
  target = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, target));

  const rect = scCanvas.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;
  const wxBefore = (mx - scPan.x) / scZoom;
  const wyBefore = (my - scPan.y) / scZoom;

  scZoom = target;

  const wxAfter = (mx - scPan.x) / scZoom;
  const wyAfter = (my - scPan.y) / scZoom;
  scPan.x += (wxAfter - wxBefore) * scZoom;
  scPan.y += (wyAfter - wyBefore) * scZoom;

  scheduleDraw();
}

/* Touch (single-finger pan) */
function onTouchStart(e) {
  if (e.touches.length === 1) {
    const t = e.touches[0];
    scIsPanning = true;
    scPanDragOrigin = { x: scPan.x, y: scPan.y };
    scPanPointerStart = { x: t.clientX, y: t.clientY };
  }
}
function onTouchMove(e) {
  if (e.touches.length === 1 && scIsPanning) {
    const t = e.touches[0];
    scPan.x = scPanDragOrigin.x + (t.clientX - scPanPointerStart.x);
    scPan.y = scPanDragOrigin.y + (t.clientY - scPanPointerStart.y);
    scheduleDraw();
  }
}
function onTouchEnd() {
  scIsPanning = false;
}

/* Hit Testing */
function screenToWorld(sx, sy) {
  const rect = scCanvas.getBoundingClientRect();
  const screenX = sx - rect.left;
  const screenY = sy - rect.top;
  return {
    x: screenX / scZoom - scPan.x,
    y: screenY / scZoom - scPan.y
  };
}
function findNodeAt(sx, sy) {
  const { x, y } = screenToWorld(sx, sy + 10); // shift hitbox 4px upward
  for (let i = scNodeRefs.length - 1; i >= 0; i--) {
    const ref = scNodeRefs[i];
    const dx = x - ref.x;
    const dy = y - ref.y;
    if (dx*dx + dy*dy <= (ref.r + 4) * (ref.r + 4)) return ref;
  }
  return null;
}

/* =========================================================
   Tooltip
   ========================================================= */
function showTooltipForNode(ref, clientX, clientY) {
  if (!tooltipEl) return;
  tooltipEl.innerHTML = buildTooltipHTML(ref.node);
  tooltipEl.style.display = 'block';
  positionTooltip(clientX, clientY);
}
function positionTooltip(cx, cy) {
  if (!tooltipEl) return;
  const pad = 14;
  const rect = tooltipEl.getBoundingClientRect();
  let left = cx + 16;
  let top = cy + 16;
  if (left + rect.width + pad > window.innerWidth) left = cx - rect.width - 20;
  if (top + rect.height + pad > window.innerHeight) top = cy - rect.height - 20;
  tooltipEl.style.left = left + 'px';
  tooltipEl.style.top = top + 'px';
}
function hideTooltip() {
  if (tooltipEl) tooltipEl.style.display = 'none';
}
function buildTooltipHTML(node) {
  const stats = (node.Stats || []).map(s => {
    const val = (s.value !== null && s.value !== undefined) ? s.value : '';
    return `<li>${s.name}: ${val}${s.percentage ? '%' : ''}</li>`;
  }).join('');
  const abilities = (node.Abilities || []).map(a => `<li>${a}</li>`).join('');
  return `
    <div class="tt-name">${node.Name || node.Constellation || 'Node'}</div>
    <div class="tt-desc" style="white-space:pre-line;">${node.Description || ''}</div>
    <div><strong>Stats</strong></div>
    <ul>${stats || '<li class="muted">None</li>'}</ul>
    <div style="margin-top:4px;"><strong>Abilities</strong></div>
    <ul>${abilities || '<li class="muted">None</li>'}</ul>
    <div class="muted" style="margin-top:4px;font-size:.65rem;">${node.Path}</div>
  `;
}

/* =========================================================
   Panels
   ========================================================= */
function renderLeftPanel() {
  if (!panelLeft) return;
  const activated = Array.from(scActivated)
    .map(p => scIndex.get(p))
    .filter(Boolean);
  panelLeft.innerHTML = `
    <h3>Activated</h3>
    <div class="activation-count">${activated.length}/${SC_MAX_ACTIVATED} slots</div>
    ${
      activated.length
        ? '<ul style="margin:0;padding-left:18px;">' +
          activated.map(n => `<li>${n.Name}</li>`).join('') +
          '</ul>'
        : '<div class="empty-note">None selected</div>'
    }
  `;
}

function renderRightPanel(node) {
  if (!panelRight) return;
  if (!node) {
    panelRight.innerHTML = `<h3>Details</h3><div class="empty-note">Hover a node</div>`;
    return;
  }
  const stats = (node.Stats || []).map(s => {
    const val = (s.value !== null && s.value !== undefined) ? s.value : '';
    return `<li>${s.name}: ${val}${s.percentage ? '%' : ''}</li>`;
  }).join('');
  const abilities = (node.Abilities || []).map(a => `<li>${a}</li>`).join('');
  panelRight.innerHTML = `
    <h3>${node.Name}</h3>
    <div style="margin-bottom:8px;white-space:pre-line;">${node.Description || ''}</div>
    <div><strong>Stats</strong></div>
    <ul style="margin:4px 0 10px;padding-left:18px;">${stats || '<li class="muted">None</li>'}</ul>
    <div><strong>Abilities</strong></div>
    <ul style="margin:4px 0 10px;padding-left:18px;">${abilities || '<li class="muted">None</li>'}</ul>
    <div class="muted" style="font-size:.7rem;">Path: ${node.Path}</div>
  `;
}

/* =========================================================
   Utilities & API
   ========================================================= */
function findNodeByPath(path) { return scIndex.get(path) || null; }

window.StarChartAPI = {
  activate(path) {
    const node = scIndex.get(path);
    if (!node || node.Type === 'Root') return;
    if (scActivated.has(path)) return;
    const parentPath = scParent.get(path);
    if (parentPath) {
      const parentNode = scIndex.get(parentPath);
      if (parentNode.Type !== 'Root' && !scActivated.has(parentPath)) return;
    }
    if (scActivated.size >= SC_MAX_ACTIVATED) return;
    activateNode(node);
    renderLeftPanel();
    scheduleDraw();
  },
  deactivate(path) {
    if (!scIndex.has(path)) return;
    if (scActivated.has(path)) {
      deactivateNodeCascade(path);
      renderLeftPanel();
      scheduleDraw();
    }
  },
  getActivated() { return Array.from(scActivated); },
  setActivated(paths) {
    scActivated.clear();
    paths.forEach(p => {
      const node = scIndex.get(p);
      if (!node || node.Type === 'Root') return;
      const parentPath = scParent.get(p);
      if (parentPath) {
        const parentNode = scIndex.get(parentPath);
        if (parentNode.Type !== 'Root' && !scActivated.has(parentPath)) return;
      }
      if (scActivated.size < SC_MAX_ACTIVATED) scActivated.add(p);
    });
    renderLeftPanel();
    scheduleDraw();
  },
  centerChart() {
    scPan = { x: 0, y: 0 };
    scZoom = ZOOM_DEFAULT;
    scheduleDraw();
  },
  reloadData(newData) {
    scData = newData;
    scActivated.clear();
    scHoverPath = null;
    buildIndices();
    computeLayout();
    renderLeftPanel();
    renderRightPanel(null);
    scheduleDraw();
  }
};