// Batch Watermark Studio Client Application

let currentMode = 'text'; // 'text' | 'image'
let currentPosition = 'diagonal-grid'; // Default to the requested Edu360 diagonal pattern
let currentStagger = false; // Parallel alignment for Edu360
let currentDensity = 1.0;
let currentSamples = [];
let currentSampleIndex = 0;
let currentLogoPath = '';
let isScanning = false;
let isProcessing = false;
let previewDebounceTimer = null;

// Canvas Frame & Image Zoom State (1570x1002 default)
let canvasEnabled = true;
let canvasW = 1570;
let canvasH = 1002;
let canvasZoom = 1.0;
let canvasMode = 'fit'; // 'fit' | 'cover' | 'original'
let canvasBg = '#000000';
let borderEnabled = true;
let borderWidth = 1;
let borderColor = '#ffffff';

// DOM Elements
const folderInput = document.getElementById('folderInput');
const scanBtn = document.getElementById('scanBtn');
const folderStatus = document.getElementById('folderStatus');
const outputFolderInput = document.getElementById('outputFolderInput');

// Source toggle & Upload Batch elements
const tabSourceFolder = document.getElementById('tabSourceFolder');
const tabSourceUpload = document.getElementById('tabSourceUpload');
const folderSourceSection = document.getElementById('folderSourceSection');
const uploadSourceSection = document.getElementById('uploadSourceSection');
const batchDropZone = document.getElementById('batchDropZone');
const batchFileInput = document.getElementById('batchFileInput');
const batchUploadStatus = document.getElementById('batchUploadStatus');
const downloadZipBtn = document.getElementById('downloadZipBtn');

const tabBtns = document.querySelectorAll('.tab-btn');
const textControls = document.getElementById('textControls');
const logoControls = document.getElementById('logoControls');
const watermarkText = document.getElementById('watermarkText');
const textColor = document.getElementById('textColor');
const strokeColor = document.getElementById('strokeColor');
const presetTags = document.querySelectorAll('.preset-tag');

const logoDropZone = document.getElementById('logoDropZone');
const logoFileInput = document.getElementById('logoFileInput');
const logoPreviewStatus = document.getElementById('logoPreviewStatus');

// Canvas & Scaling Elements
const canvasToggle = document.getElementById('canvasToggle');
const canvasControlsBody = document.getElementById('canvasControlsBody');
const canvasZoomSlider = document.getElementById('canvasZoomSlider');
const canvasZoomVal = document.getElementById('canvasZoomVal');
const borderToggle = document.getElementById('borderToggle');
const borderWidthSelect = document.getElementById('borderWidthSelect');
const borderColorInput = document.getElementById('borderColorInput');
const canvasBgInput = document.getElementById('canvasBgInput');
const canvasBgLabel = document.getElementById('canvasBgLabel');
const canvasDimIndicator = document.getElementById('canvasDimIndicator');

// Pattern & Placement Elements
const edu360Btn = document.getElementById('edu360Btn');
const tiledBtn = document.getElementById('tiledBtn');
const singlePosToggleBtn = document.getElementById('singlePosToggleBtn');
const singlePositionContainer = document.getElementById('singlePositionContainer');
const posBtns = document.querySelectorAll('.pos-btn');

// Density & Grid Alignment
const densityGroup = document.getElementById('densityGroup');
const densitySlider = document.getElementById('densitySlider');
const densityVal = document.getElementById('densityVal');
const gridAlignmentRow = document.getElementById('gridAlignmentRow');
const alignParallelBtn = document.getElementById('alignParallelBtn');
const alignStaggerBtn = document.getElementById('alignStaggerBtn');

// Sliders
const opacitySlider = document.getElementById('opacitySlider');
const opacityVal = document.getElementById('opacityVal');
const scaleSlider = document.getElementById('scaleSlider');
const scaleVal = document.getElementById('scaleVal');
const angleSlider = document.getElementById('angleSlider');
const angleVal = document.getElementById('angleVal');

// Action & Previews
const startBatchBtn = document.getElementById('startBatchBtn');
const startBtnText = document.getElementById('startBtnText');
const previewImg = document.getElementById('previewImg');
const previewLoader = document.getElementById('previewLoader');
const noImagePlaceholder = document.getElementById('noImagePlaceholder');
const sampleInfo = document.getElementById('sampleInfo');
const sampleIndex = document.getElementById('sampleIndex');
const prevSampleBtn = document.getElementById('prevSampleBtn');
const nextSampleBtn = document.getElementById('nextSampleBtn');

// Progress
const progressCard = document.getElementById('progressCard');
const progressTitle = document.getElementById('progressTitle');
const progressPercent = document.getElementById('progressPercent');
const progressBarFill = document.getElementById('progressBarFill');
const statProcessed = document.getElementById('statProcessed');
const statTotal = document.getElementById('statTotal');
const statSpeed = document.getElementById('statSpeed');
const statTime = document.getElementById('statTime');
const progressCurrentFile = document.getElementById('progressCurrentFile');
const completionActions = document.getElementById('completionActions');
const openFolderBtn = document.getElementById('openFolderBtn');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  setupEventListeners();
  if (watermarkText) {
    watermarkText.value = 'www.edu360.uz';
  }
  // Auto-scan current folder or default
  scanFolder('.');
});

function setupEventListeners() {
  // Folder Scan
  scanBtn.addEventListener('click', () => scanFolder(folderInput.value.trim()));
  folderInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') scanFolder(folderInput.value.trim());
  });

  // Tab switching (Text vs Logo)
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentMode = btn.dataset.mode;
      if (currentMode === 'text') {
        textControls.classList.add('active');
        logoControls.classList.remove('active');
      } else {
        textControls.classList.remove('active');
        logoControls.classList.add('active');
      }
      triggerPreviewUpdate();
    });
  });

  // Text inputs
  watermarkText.addEventListener('input', triggerPreviewUpdate);
  textColor.addEventListener('input', triggerPreviewUpdate);
  strokeColor.addEventListener('input', triggerPreviewUpdate);

  // Preset tags
  presetTags.forEach(tag => {
    tag.addEventListener('click', () => {
      watermarkText.value = tag.dataset.val;
      if (tag.dataset.val === 'www.edu360.uz') {
        selectEdu360Mode();
      }
      triggerPreviewUpdate();
    });
  });

  // Logo drop zone
  logoDropZone.addEventListener('click', () => logoFileInput.click());
  logoFileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      uploadLogo(e.target.files[0]);
    }
  });

  logoDropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    logoDropZone.classList.add('dragover');
  });
  logoDropZone.addEventListener('dragleave', () => logoDropZone.classList.remove('dragover'));
  logoDropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    logoDropZone.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      uploadLogo(e.dataTransfer.files[0]);
    }
  });

  // --- Canvas Frame & Zoom Scaling Listeners ---
  canvasToggle.addEventListener('change', (e) => {
    canvasEnabled = e.target.checked;
    if (canvasEnabled) {
      canvasControlsBody.classList.remove('disabled');
      if (canvasDimIndicator) canvasDimIndicator.style.display = 'inline-flex';
    } else {
      canvasControlsBody.classList.add('disabled');
      if (canvasDimIndicator) canvasDimIndicator.style.display = 'none';
    }
    triggerPreviewUpdate();
  });

  // Zoom Slider
  canvasZoomSlider.addEventListener('input', (e) => {
    const val = parseInt(e.target.value);
    canvasZoom = val / 100.0;
    canvasZoomVal.textContent = `${val}% (Qo'lda)`;
    triggerPreviewUpdate();
  });

  // Quick Zoom / Fit preset pills
  document.querySelectorAll('[data-zoom]').forEach(btn => {
    btn.addEventListener('click', () => {
      const zoomVal = parseInt(btn.dataset.zoom);
      const mode = btn.dataset.mode;
      canvasMode = mode;
      canvasZoom = zoomVal / 100.0;
      canvasZoomSlider.value = zoomVal;

      if (mode === 'fit' && zoomVal === 100) {
        canvasZoomVal.textContent = '100% (Moslash)';
      } else if (mode === 'cover') {
        canvasZoomVal.textContent = 'To\'ldirish (Fill)';
      } else if (mode === 'original') {
        canvasZoomVal.textContent = '100% (Asl)';
      } else {
        canvasZoomVal.textContent = `${zoomVal}%`;
      }

      const parentPills = btn.closest('.quick-preset-pills');
      if (parentPills) {
        parentPills.querySelectorAll('.pill-btn').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
      }
      triggerPreviewUpdate();
    });
  });

  // Border (Ingichka ramka) Listeners
  borderToggle.addEventListener('change', (e) => {
    borderEnabled = e.target.checked;
    triggerPreviewUpdate();
  });

  borderWidthSelect.addEventListener('change', (e) => {
    borderWidth = parseInt(e.target.value);
    if (borderWidth === 0) {
      borderEnabled = false;
      borderToggle.checked = false;
    } else {
      borderEnabled = true;
      borderToggle.checked = true;
    }
    triggerPreviewUpdate();
  });

  borderColorInput.addEventListener('input', (e) => {
    borderColor = e.target.value;
    triggerPreviewUpdate();
  });

  // Background Color
  canvasBgInput.addEventListener('input', (e) => {
    canvasBg = e.target.value;
    canvasBgLabel.textContent = e.target.value;
    triggerPreviewUpdate();
  });

  // --- Pattern & Placement Listeners ---
  edu360Btn.addEventListener('click', () => {
    selectEdu360Mode();
    triggerPreviewUpdate();
  });

  tiledBtn.addEventListener('click', () => {
    clearActivePatternButtons();
    tiledBtn.classList.add('active');
    currentPosition = 'tiled';
    currentStagger = true;
    singlePositionContainer.style.display = 'none';
    densityGroup.style.display = 'block';
    gridAlignmentRow.style.display = 'block';
    alignStaggerBtn.classList.add('active');
    alignParallelBtn.classList.remove('active');

    angleSlider.value = -30;
    angleVal.textContent = '-30°';
    syncPresetPill('angle', -30);
    triggerPreviewUpdate();
  });

  singlePosToggleBtn.addEventListener('click', () => {
    clearActivePatternButtons();
    singlePosToggleBtn.classList.add('active');
    singlePositionContainer.style.display = 'block';
    densityGroup.style.display = 'none';
    gridAlignmentRow.style.display = 'none';

    let activePos = document.querySelector('.pos-btn.active');
    if (!activePos) {
      const defBtn = document.querySelector('.pos-btn[data-pos="bottom-right"]');
      if (defBtn) defBtn.classList.add('active');
      currentPosition = 'bottom-right';
    } else {
      currentPosition = activePos.dataset.pos;
    }

    if (scaleSlider.value < 10) {
      scaleSlider.value = 18;
      scaleVal.textContent = '18%';
    }
    if (opacitySlider.value < 50) {
      opacitySlider.value = 75;
      opacityVal.textContent = '75%';
      syncPresetPill('opacity', 85);
    }
    triggerPreviewUpdate();
  });

  posBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      posBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentPosition = btn.dataset.pos;
      triggerPreviewUpdate();
    });
  });

  alignParallelBtn.addEventListener('click', () => {
    alignParallelBtn.classList.add('active');
    alignStaggerBtn.classList.remove('active');
    currentStagger = false;
    triggerPreviewUpdate();
  });

  alignStaggerBtn.addEventListener('click', () => {
    alignStaggerBtn.classList.add('active');
    alignParallelBtn.classList.remove('active');
    currentStagger = true;
    triggerPreviewUpdate();
  });

  densitySlider.addEventListener('input', (e) => {
    updateDensityFromSlider(parseFloat(e.target.value));
    triggerPreviewUpdate();
  });

  opacitySlider.addEventListener('input', (e) => {
    opacityVal.textContent = `${e.target.value}%`;
    syncPresetPill('opacity', parseInt(e.target.value));
    triggerPreviewUpdate();
  });

  scaleSlider.addEventListener('input', (e) => {
    scaleVal.textContent = `${e.target.value}%`;
    triggerPreviewUpdate();
  });

  angleSlider.addEventListener('input', (e) => {
    angleVal.textContent = `${e.target.value}°`;
    syncPresetPill('angle', parseInt(e.target.value));
    triggerPreviewUpdate();
  });

  // Presets
  document.querySelectorAll('.pill-btn').forEach(pill => {
    if (pill.dataset.zoom) return; // Handled separately
    pill.addEventListener('click', () => {
      const parentGroup = pill.closest('.slider-group');

      if (pill.dataset.density) {
        const val = parseInt(pill.dataset.density);
        densitySlider.value = val;
        updateDensityFromSlider(val);
      } else if (pill.dataset.opacity) {
        const val = parseInt(pill.dataset.opacity);
        opacitySlider.value = val;
        opacityVal.textContent = `${val}%`;
      } else if (pill.dataset.angle) {
        const val = parseInt(pill.dataset.angle);
        angleSlider.value = val;
        angleVal.textContent = `${val}°`;
      }

      if (parentGroup) {
        parentGroup.querySelectorAll('.pill-btn').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
      }
      triggerPreviewUpdate();
    });
  });

  prevSampleBtn.addEventListener('click', () => {
    if (currentSamples.length > 0) {
      currentSampleIndex = (currentSampleIndex - 1 + currentSamples.length) % currentSamples.length;
      updateSampleView();
    }
  });

  nextSampleBtn.addEventListener('click', () => {
    if (currentSamples.length > 0) {
      currentSampleIndex = (currentSampleIndex + 1) % currentSamples.length;
      updateSampleView();
    }
  });

  startBatchBtn.addEventListener('click', startBatch);

  // Source tab switching (Folder vs Upload)
  if (tabSourceFolder && tabSourceUpload) {
    tabSourceFolder.addEventListener('click', () => {
      tabSourceFolder.classList.add('active');
      tabSourceUpload.classList.remove('active');
      if (folderSourceSection) folderSourceSection.style.display = 'block';
      if (uploadSourceSection) uploadSourceSection.style.display = 'none';
    });

    tabSourceUpload.addEventListener('click', () => {
      tabSourceUpload.classList.add('active');
      tabSourceFolder.classList.remove('active');
      if (folderSourceSection) folderSourceSection.style.display = 'none';
      if (uploadSourceSection) uploadSourceSection.style.display = 'block';
    });
  }

  // Batch drop zone & file input
  if (batchDropZone && batchFileInput) {
    batchDropZone.addEventListener('click', () => batchFileInput.click());
    batchFileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files.length > 0) {
        uploadBatchFiles(e.target.files);
      }
    });

    batchDropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      batchDropZone.classList.add('dragover');
    });
    batchDropZone.addEventListener('dragleave', () => batchDropZone.classList.remove('dragover'));
    batchDropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      batchDropZone.classList.remove('dragover');
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        uploadBatchFiles(e.dataTransfer.files);
      }
    });
  }

  // Download ZIP
  if (downloadZipBtn) {
    downloadZipBtn.addEventListener('click', () => {
      const outFolder = outputFolderInput.value.trim();
      const url = `/api/download-zip?folder=${encodeURIComponent(outFolder)}&_t=${Date.now()}`;
      window.location.href = url;
    });
  }

  openFolderBtn.addEventListener('click', () => {
    fetch('/api/open-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder: outputFolderInput.value.trim() })
    });
  });
}

// Upload Batch Images or ZIP Archive
async function uploadBatchFiles(files) {
  if (!batchUploadStatus) return;
  batchUploadStatus.style.display = 'block';
  batchUploadStatus.innerHTML = `<span>⏳ ${files.length} ta fayl yuklanmoqda...</span>`;
  folderStatus.className = 'folder-status empty';
  folderStatus.innerHTML = `<span>⏳ Fayllar serverga yuklanmoqda va tekshirilmoqda...</span>`;

  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append('files', files[i]);
  }

  try {
    const res = await fetch('/api/upload-batch', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (data.success && data.count > 0) {
      folderInput.value = data.folder;
      batchUploadStatus.innerHTML = `<span>✅ Muvaffaqiyatli yuklandi: <strong>${data.count} ta</strong> rasm</span>`;
      folderStatus.className = 'folder-status success';
      folderStatus.innerHTML = `<span>✅ Yuklangan: <strong>${data.count} ta</strong> rasm tayyor</span>`;
      currentSamples = data.samples || [];
      currentSampleIndex = 0;
      startBatchBtn.disabled = false;
      startBtnText.textContent = `${data.count} ta rasmga qo'llash`;
      updateSampleView();
    } else {
      batchUploadStatus.innerHTML = `<span>⚠️ ${data.error || 'Rasmlar topilmadi'}</span>`;
      folderStatus.className = 'folder-status error';
      folderStatus.innerHTML = `<span>⚠️ ${data.error || 'Rasmlar topilmadi'}</span>`;
    }
  } catch (err) {
    batchUploadStatus.innerHTML = `<span>❌ Xatolik: ${err.message}</span>`;
    folderStatus.className = 'folder-status error';
    folderStatus.innerHTML = `<span>❌ Yuklashda xatolik: ${err.message}</span>`;
  }
}

function selectEdu360Mode() {
  clearActivePatternButtons();
  edu360Btn.classList.add('active');
  currentPosition = 'diagonal-grid';
  currentStagger = false;
  singlePositionContainer.style.display = 'none';
  densityGroup.style.display = 'block';
  gridAlignmentRow.style.display = 'block';

  alignParallelBtn.classList.add('active');
  alignStaggerBtn.classList.remove('active');

  angleSlider.value = 12;
  angleVal.textContent = '12°';
  syncPresetPill('angle', 12);

  opacitySlider.value = 38;
  opacityVal.textContent = '38%';
  syncPresetPill('opacity', 38);

  scaleSlider.value = 4;
  scaleVal.textContent = '4%';

  densitySlider.value = 10;
  updateDensityFromSlider(10);
  syncPresetPill('density', 10);
}

function clearActivePatternButtons() {
  edu360Btn.classList.remove('active');
  tiledBtn.classList.remove('active');
  singlePosToggleBtn.classList.remove('active');
}

function updateDensityFromSlider(val) {
  currentDensity = val / 10.0;
  let textLabel = 'Standart (1.0x)';
  if (currentDensity <= 0.7) textLabel = `Siyrak (${currentDensity.toFixed(1)}x)`;
  else if (currentDensity >= 1.4) textLabel = `Zich (${currentDensity.toFixed(1)}x)`;
  else textLabel = `Standart (${currentDensity.toFixed(1)}x)`;
  densityVal.textContent = textLabel;
}

function syncPresetPill(type, val) {
  const container = document.querySelector(`[data-${type}="${val}"]`);
  if (container) {
    const parent = container.closest('.quick-preset-pills');
    if (parent) {
      parent.querySelectorAll('.pill-btn').forEach(p => p.classList.remove('active'));
      container.classList.add('active');
    }
  }
}

// Scan Folder
async function scanFolder(folder) {
  if (isScanning) return;
  isScanning = true;
  folderStatus.className = 'folder-status empty';
  folderStatus.innerHTML = `<span>🔍 Papka tekshirilmoqda...</span>`;

  try {
    const res = await fetch(`/api/scan?folder=${encodeURIComponent(folder)}`);
    const data = await res.json();

    if (data.success) {
      folderInput.value = data.folder;
      currentSamples = data.samples || [];
      currentSampleIndex = 0;

      if (data.count > 0) {
        folderStatus.className = 'folder-status success';
        folderStatus.innerHTML = `<span>✅ Topildi: <strong>${data.count} ta</strong> rasm</span>`;
        startBatchBtn.disabled = false;
        startBtnText.textContent = `${data.count} ta rasmga qo'llash`;
        updateSampleView();
      } else {
        folderStatus.className = 'folder-status error';
        folderStatus.innerHTML = `<span>⚠️ Bu papkada rasm fayllari topilmadi.</span>`;
        startBatchBtn.disabled = true;
        showPlaceholder(true);
      }
    } else {
      folderStatus.className = 'folder-status error';
      folderStatus.innerHTML = `<span>❌ ${data.error || 'Papka topilmadi'}</span>`;
      startBatchBtn.disabled = true;
      showPlaceholder(true);
    }
  } catch (err) {
    folderStatus.className = 'folder-status error';
    folderStatus.innerHTML = `<span>❌ Xatolik yuz berdi: ${err.message}</span>`;
  } finally {
    isScanning = false;
  }
}

// Logo Upload
async function uploadLogo(file) {
  logoPreviewStatus.style.display = 'block';
  logoPreviewStatus.innerHTML = '<span>⏳ Logo yuklanmoqda...</span>';

  const formData = new FormData();
  formData.append('logo', file);

  try {
    const res = await fetch('/api/upload-logo', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (data.success) {
      currentLogoPath = data.logo_path;
      logoPreviewStatus.innerHTML = `<span>✅ Logo yuklandi: <strong>${file.name}</strong></span>`;
      triggerPreviewUpdate();
    } else {
      logoPreviewStatus.innerHTML = `<span>❌ Xatolik: ${data.error}</span>`;
    }
  } catch (err) {
    logoPreviewStatus.innerHTML = `<span>❌ Yuklashda xatolik: ${err.message}</span>`;
  }
}

// Sample View
function updateSampleView() {
  if (currentSamples.length === 0) {
    showPlaceholder(true);
    return;
  }
  showPlaceholder(false);
  const currentPath = currentSamples[currentSampleIndex];
  const filename = currentPath.split('/').pop();
  sampleInfo.textContent = filename;
  sampleIndex.textContent = `${currentSampleIndex + 1} / ${currentSamples.length}`;
  fetchPreview();
}

function showPlaceholder(show) {
  if (show) {
    noImagePlaceholder.style.display = 'block';
    previewImg.style.display = 'none';
  } else {
    noImagePlaceholder.style.display = 'none';
    previewImg.style.display = 'block';
  }
}

// Debounced Live Preview
function triggerPreviewUpdate() {
  clearTimeout(previewDebounceTimer);
  previewDebounceTimer = setTimeout(fetchPreview, 90);
}

async function fetchPreview() {
  if (currentSamples.length === 0) return;
  const currentFile = currentSamples[currentSampleIndex];

  previewLoader.style.display = 'flex';

  const isGrid = currentPosition === 'diagonal-grid' || currentPosition === 'tiled';
  const effectiveStrokeWidth = isGrid ? 0 : 2;

  const params = new URLSearchParams({
    file: currentFile,
    mode: currentMode,
    position: currentPosition,
    opacity: (parseFloat(opacitySlider.value) / 100).toFixed(2),
    scale: (parseFloat(scaleSlider.value) / 100).toFixed(3),
    angle: angleSlider.value,
    density: (parseFloat(densitySlider.value) / 10.0).toFixed(2),
    stagger: currentStagger ? '1' : '0',
    stroke_width: effectiveStrokeWidth,
    text: watermarkText.value,
    color: textColor.value,
    stroke_color: strokeColor.value,
    logo: currentLogoPath,
    // Canvas Frame & Zoom Parameters
    canvas_enabled: canvasEnabled ? '1' : '0',
    canvas_w: canvasW,
    canvas_h: canvasH,
    canvas_zoom: canvasZoom.toFixed(2),
    canvas_mode: canvasMode,
    canvas_bg: canvasBg,
    border_width: borderEnabled ? borderWidth : 0,
    border_color: borderColor
  });

  const previewUrl = `/api/preview?${params.toString()}&_t=${Date.now()}`;

  const tempImg = new Image();
  tempImg.onload = () => {
    previewImg.src = tempImg.src;
    previewImg.style.display = 'block';
    previewLoader.style.display = 'none';
  };
  tempImg.onerror = () => {
    previewLoader.style.display = 'none';
  };
  tempImg.src = previewUrl;
}

// Batch Start
async function startBatch() {
  if (isProcessing) return;
  const inFolder = folderInput.value.trim();
  const outFolder = outputFolderInput.value.trim();

  if (!inFolder) {
    alert("Iltimos, avval rasmlar papkasini tanlang.");
    return;
  }

  isProcessing = true;
  startBatchBtn.disabled = true;
  progressCard.style.display = 'block';
  completionActions.style.display = 'none';
  progressBarFill.style.width = '0%';
  progressPercent.textContent = '0%';
  progressTitle.textContent = '⏳ Rasmlar qayta ishlanmoqda...';

  const isGrid = currentPosition === 'diagonal-grid' || currentPosition === 'tiled';
  const effectiveStrokeWidth = isGrid ? 0 : 2;

  try {
    const res = await fetch('/api/batch-start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        input_folder: inFolder,
        output_folder: outFolder,
        mode: currentMode,
        logo_path: currentLogoPath,
        params: {
          text: watermarkText.value,
          position: currentPosition,
          opacity: parseFloat(opacitySlider.value) / 100,
          scale: parseFloat(scaleSlider.value) / 100,
          angle: parseInt(angleSlider.value),
          density: parseFloat(densitySlider.value) / 10.0,
          stagger: currentStagger,
          color: textColor.value,
          stroke_color: strokeColor.value,
          stroke_width: effectiveStrokeWidth,
          // Canvas Frame & Zoom
          canvas_enabled: canvasEnabled,
          canvas_w: canvasW,
          canvas_h: canvasH,
          canvas_zoom: canvasZoom,
          canvas_mode: canvasMode,
          canvas_bg: canvasBg,
          border_width: borderEnabled ? borderWidth : 0,
          border_color: borderColor
        }
      })
    });

    const data = await res.json();
    if (data.success) {
      pollBatchStatus();
    } else {
      alert("Xato: " + (data.error || "Boshlab bo'lmadi"));
      isProcessing = false;
      startBatchBtn.disabled = false;
    }
  } catch (err) {
    alert("Xatolik: " + err.message);
    isProcessing = false;
    startBatchBtn.disabled = false;
  }
}

// Poll Progress
function pollBatchStatus() {
  const interval = setInterval(async () => {
    try {
      const res = await fetch('/api/batch-status');
      const state = await res.json();

      const total = state.total || 1;
      const done = state.processed + state.failed;
      const pct = Math.min(100, Math.round((done / total) * 100));

      progressBarFill.style.width = `${pct}%`;
      progressPercent.textContent = `${pct}%`;
      statProcessed.textContent = state.processed;
      statTotal.textContent = state.total;
      statSpeed.textContent = state.speed || 0;
      statTime.textContent = state.time_seconds || 0;
      progressCurrentFile.textContent = state.current_file ? `Hozirgi: ${state.current_file}` : '';

      if (!state.is_running && done >= total && total > 0) {
        clearInterval(interval);
        isProcessing = false;
        startBatchBtn.disabled = false;
        progressTitle.textContent = '🎉 Barcha rasmlar tayyor!';
        progressBarFill.style.width = '100%';
        progressPercent.textContent = '100%';
        completionActions.style.display = 'block';
        if (state.output_folder) {
          outputFolderInput.value = state.output_folder;
        }
      }
    } catch (err) {
      console.error("Poll error:", err);
    }
  }, 250);
}
