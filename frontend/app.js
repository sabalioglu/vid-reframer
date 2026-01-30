/**
 * Video Reframer - Frontend Application
 * Client-side logic for video upload and processing
 *
 * Features:
 * - User registration with API key
 * - Video upload with progress tracking
 * - Real-time processing status
 * - Results visualization
 */

// Configuration
const API_URL = "https://sabalioglu--video-reframer-web.modal.run";
// Updated: 2026-01-28 - New Modal deployment

let apiKey = localStorage.getItem('vr_api_key');
let currentJobId = null;
let currentResults = null;

// =====================================================
// Initialization
// =====================================================

document.addEventListener('DOMContentLoaded', () => {
    setupUI();
    setupDragAndDrop();
    setupEventListeners();

    // Check if already logged in
    if (apiKey) {
        showProcessingSection();
    } else {
        showLoginSection();
    }
});

// =====================================================
// UI Setup
// =====================================================

function setupUI() {
    const userEmail = localStorage.getItem('vr_user_email');
    if (userEmail) {
        document.getElementById('userEmail').textContent = userEmail;
        document.getElementById('userSection').classList.remove('hidden');
    }
}

function showLoginSection() {
    document.getElementById('loginSection').classList.remove('hidden');
    document.getElementById('processingSection').classList.add('hidden');
    document.getElementById('userSection').classList.add('hidden');
}

function showProcessingSection() {
    document.getElementById('loginSection').classList.add('hidden');
    document.getElementById('processingSection').classList.remove('hidden');
    document.getElementById('userSection').classList.remove('hidden');
}

function setupEventListeners() {
    // Video file input
    document.getElementById('videoInput').addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            uploadVideo(e.target.files[0]);
        }
    });

    // Logout button
    document.getElementById('logoutBtn').addEventListener('click', logout);
}

function setupDragAndDrop() {
    const dropZone = document.getElementById('dropZone');

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('border-purple-500', 'bg-purple-50');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('border-purple-500', 'bg-purple-50');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('border-purple-500', 'bg-purple-50');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            uploadVideo(files[0]);
        }
    });
}

// =====================================================
// User Management
// =====================================================

async function registerUser() {
    const email = document.getElementById('emailInput').value.trim();

    if (!email || !email.includes('@')) {
        alert('Please enter a valid email address');
        return;
    }

    try {
        console.log('Registering user with email:', email);
        console.log('API URL:', `${API_URL}/register`);

        const response = await fetch(`${API_URL}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });

        console.log('Registration response status:', response.status);
        console.log('Registration response headers:', response.headers);

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error response body:', errorText);
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const data = await response.json();
        console.log('Registration data received:', data);

        // Save API key and email
        apiKey = data.api_key;
        console.log('API key saved:', apiKey);

        localStorage.setItem('vr_api_key', apiKey);
        localStorage.setItem('vr_user_email', email);
        console.log('LocalStorage updated');

        // Show success message
        const msg = document.getElementById('registrationMessage');
        document.getElementById('apiKeyDisplay').textContent = apiKey;
        msg.classList.remove('hidden');

        // Update UI
        document.getElementById('userEmail').textContent = email;
        document.getElementById('userSection').classList.remove('hidden');

        // Switch to processing section
        setTimeout(() => {
            showProcessingSection();
        }, 2000);

    } catch (error) {
        console.error('Registration error:', error);
        console.error('Error stack:', error.stack);
        alert(`Registration failed: ${error.message}`);
    }
}

function logout() {
    apiKey = null;
    localStorage.removeItem('vr_api_key');
    localStorage.removeItem('vr_user_email');
    document.getElementById('emailInput').value = '';
    document.getElementById('registrationMessage').classList.add('hidden');
    showLoginSection();
}

// =====================================================
// Video Processing
// =====================================================

async function uploadVideo(file) {
    // Validate file
    if (!file.type.startsWith('video/')) {
        alert('Please select a video file');
        return;
    }

    if (file.size > 500 * 1024 * 1024) {
        alert('File too large (max 500MB)');
        return;
    }

    try {
        // DEBUG: Check API key before upload
        console.log('=== UPLOAD VIDEO DEBUG ===');
        console.log('Current apiKey variable:', apiKey);
        console.log('LocalStorage apiKey:', localStorage.getItem('vr_api_key'));
        console.log('File name:', file.name);
        console.log('File size:', file.size);
        console.log('File type:', file.type);

        // Ensure apiKey is set
        if (!apiKey) {
            console.warn('API key is not set! Reading from localStorage...');
            apiKey = localStorage.getItem('vr_api_key');
            console.log('API key from localStorage:', apiKey);
        }

        if (!apiKey) {
            throw new Error('No API key found. Please register first.');
        }

        // Show processing status
        document.getElementById('processingStatus').classList.remove('hidden');
        document.getElementById('resultsSection').classList.add('hidden');
        updateProgressStep('step2', false, 'Extracting frames...');

        // Upload video
        const formData = new FormData();
        formData.append('file', file);

        console.log('Sending request to:', `${API_URL}/analyze`);
        console.log('With API key:', apiKey);

        const response = await fetch(`${API_URL}/analyze`, {
            method: 'POST',
            headers: { 'X-API-Key': apiKey },
            body: formData
        });

        console.log('Upload response status:', response.status);
        const responseText = await response.text();
        console.log('Upload response body:', responseText);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${responseText}`);
        }

        const data = JSON.parse(responseText);
        currentJobId = data.job_id;

        console.log('Upload successful, job ID:', currentJobId);

        // Poll for job status
        pollJobStatus();

    } catch (error) {
        console.error('Upload error:', error);
        console.error('Error details:', error.message);
        console.error('Error stack:', error.stack);
        alert(`Upload failed: ${error.message}`);
        document.getElementById('processingStatus').classList.add('hidden');
    }
}

async function pollJobStatus() {
    const maxAttempts = 120;  // 2 minutes (1 second intervals)
    let attempts = 0;

    const pollInterval = setInterval(async () => {
        attempts++;

        try {
            const response = await fetch(
                `${API_URL}/job/${currentJobId}`,
                { headers: { 'X-API-Key': apiKey } }
            );

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            const status = data.status;

            // Update progress based on status
            if (status === 'processing') {
                const step = data.current_step || 'Processing...';
                updateProgressMessage(step);
                updateProgressPercent(data.progress_percent || 0);
            } else if (status === 'completed') {
                clearInterval(pollInterval);
                updateProgressPercent(100);
                fetchResults();
                return;
            } else if (status === 'failed') {
                clearInterval(pollInterval);
                document.getElementById('statusText').textContent = `Error: ${data.error_message || 'Unknown error'}`;
                return;
            }

        } catch (error) {
            console.error('Poll error:', error);
        }

        // Timeout after max attempts
        if (attempts >= maxAttempts) {
            clearInterval(pollInterval);
            document.getElementById('statusText').textContent = 'Processing timeout. Check Modal logs.';
        }
    }, 1000);
}

async function fetchResults() {
    try {
        const response = await fetch(
            `${API_URL}/results/${currentJobId}`,
            { headers: { 'X-API-Key': apiKey } }
        );

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        currentResults = await response.json();

        // Display results
        displayResults();
        document.getElementById('processingStatus').classList.add('hidden');
        document.getElementById('resultsSection').classList.remove('hidden');

    } catch (error) {
        console.error('Results fetch error:', error);
        alert(`Failed to fetch results: ${error.message}`);
    }
}

// =====================================================
// Results Display
// =====================================================

function displayResults() {
    console.log('[displayResults] Called with currentResults:', currentResults);
    if (!currentResults) {
        console.error('[displayResults] currentResults is null/undefined!');
        return;
    }

    // Check if this is NEW UNIFIED PIPELINE format
    const finalOutput = currentResults.final_output || currentResults.results?.final_output;
    const pipelineStatus = currentResults.pipeline_status;

    // Fallback to old format if needed
    const geminiAnalysis = currentResults.gemini || currentResults.results?.gemini;
    const yoloData = currentResults.yolo || currentResults.results?.yolo;

    let personCount = 0;
    let productCount = 0;
    let sceneCount = 0;
    let totalFrames = 0;
    let productsUsed = [];
    let statistics = {};

    // ==================== NEW UNIFIED PIPELINE FORMAT ====================
    if (finalOutput && pipelineStatus === 'completed') {
        console.log('[displayResults] Using NEW UNIFIED PIPELINE format');

        const metadata = finalOutput.metadata || {};
        personCount = metadata.total_people || 0;
        sceneCount = metadata.total_scenes || 0;
        totalFrames = metadata.total_frames || 0;

        // Get products from Gemini (not just object detection)
        const products = finalOutput.products || [];
        productCount = products.length;
        productsUsed = products.map(p => p.name);

        console.log('[displayResults] NEW Pipeline: persons=', personCount, 'products=', productCount, 'scenes=', sceneCount, 'frames=', totalFrames);
        console.log('[displayResults] Products used:', productsUsed);

        // Timeline available
        const timeline = finalOutput.timeline || [];
        if (timeline.length > 0) {
            console.log('[displayResults] Timeline events:', timeline.length);
        }

        // YOLO verification stats
        const yoloVerification = finalOutput.yolo_verification || {};
        console.log('[displayResults] YOLO verified:', yoloVerification.total_instances, 'instances of', yoloVerification.verified_detections, 'products');

    }
    // ==================== OLD FORMAT (Fallback) ====================
    else if (geminiAnalysis || yoloData) {
        console.log('[displayResults] Using OLD format (Gemini + YOLOv8)');

        let detections = {};

        // Get YOLOv8 detections
        if (yoloData) {
            detections = yoloData.detections || {};
            statistics = yoloData.statistics || {};
            totalFrames = yoloData.frame_count || Object.keys(detections).length || 0;
        }

        // Get person count from Gemini
        if (geminiAnalysis && geminiAnalysis.status === 'success') {
            const gData = geminiAnalysis.gemini_analysis || {};
            personCount = gData.total_unique_people || 0;
            console.log('[displayResults] Using Gemini unique people:', personCount);
        } else if (yoloData) {
            // Fallback to YOLOv8 per-frame count
            Object.entries(detections).forEach(([_frameId, frameDetections]) => {
                frameDetections.forEach((detection) => {
                    const className = detection.class_name || detection.class || '';
                    if (className.toLowerCase() === 'person') {
                        personCount++;
                    }
                });
            });
        }

        // Count products from verified detections
        const productClasses = ['cup', 'fork', 'knife', 'spoon', 'bowl', 'plate', 'bottle',
                               'oven', 'microwave', 'sink', 'refrigerator', 'toaster',
                               'pot', 'pan', 'chair', 'dining table', 'vase', 'book'];

        Object.entries(detections).forEach(([_frameId, frameDetections]) => {
            frameDetections.forEach((detection) => {
                const classNameLower = (detection.class_name || detection.class || '').toLowerCase();
                if (productClasses.includes(classNameLower)) {
                    productCount++;
                    if (!productsUsed.includes(classNameLower)) {
                        productsUsed.push(classNameLower);
                    }
                }
            });
        });

        console.log('[displayResults] OLD Pipeline: persons=', personCount, 'products=', productCount, 'frames=', totalFrames);
    }

    // Scene count already set above for new pipeline
    // For old pipeline, calculate from metadata
    if (!sceneCount && statistics && statistics.total_detections) {
        sceneCount = 1;
    }

    console.log('[displayResults] Final: persons=', personCount, 'products=', productCount, 'scenes=', sceneCount, 'frames=', totalFrames);
    if (productsUsed.length > 0) {
        console.log('[displayResults] Products identified:', productsUsed.join(', '));
    }

    // Display on UI
    document.getElementById('statScenes').textContent = sceneCount;
    document.getElementById('statPersons').textContent = personCount;
    document.getElementById('statProducts').textContent = productCount;
    document.getElementById('statFrames').textContent = totalFrames;

    // Display JSON results
    document.getElementById('jsonResults').textContent = JSON.stringify(currentResults, null, 2);
}

// =====================================================
// Utility Functions
// =====================================================

function updateProgressStep(stepId, completed, text) {
    const step = document.getElementById(stepId);
    const icon = document.getElementById(stepId + 'Icon');
    const textEl = document.getElementById(stepId + 'Text');

    if (completed) {
        icon.classList.remove('bg-gray-200', 'text-gray-600');
        icon.classList.add('bg-purple-500', 'text-white');
        icon.textContent = '✓';
    } else {
        icon.classList.remove('bg-gray-200', 'text-gray-600');
        icon.classList.add('bg-yellow-500', 'text-white');
        icon.innerHTML = '<div class="spinner"></div>';
    }

    if (text) {
        textEl.textContent = text;
    }
}

function updateProgressMessage(message) {
    document.getElementById('statusText').textContent = message;
}

function updateProgressPercent(percent) {
    document.getElementById('progressPercent').textContent = `Processing: ${Math.min(percent, 100)}%`;
}

// =====================================================
// Download & Copy Functions
// =====================================================

function downloadJSON() {
    if (!currentResults) return;

    const json = JSON.stringify(currentResults, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `video-reframer-results-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function copyToClipboard() {
    if (!currentResults) return;

    const json = JSON.stringify(currentResults, null, 2);
    navigator.clipboard.writeText(json).then(() => {
        alert('Results copied to clipboard!');
    });
}

function processAnother() {
    currentJobId = null;
    currentResults = null;
    document.getElementById('processingStatus').classList.add('hidden');
    document.getElementById('resultsSection').classList.add('hidden');
    document.getElementById('videoInput').value = '';

    // Reset progress steps
    for (let i = 2; i <= 5; i++) {
        updateProgressStep(`step${i}`, false, '');
    }
}

// =====================================================
// Error Handling
// =====================================================

window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
});

window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
});
