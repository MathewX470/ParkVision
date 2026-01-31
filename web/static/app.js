// Smart Parking System - Real-time WebSocket Client

class ParkingMonitor {
    constructor() {
        this.socket = null;
        this.connected = false;
        this.pollingInterval = null;
        this.init();
    }

    init() {
        this.connectSocket();
        this.setupEventListeners();
        // Start polling as fallback
        this.startPolling();
    }

    connectSocket() {
        // Connect to the Socket.IO server
        this.socket = io({
            reconnection: true,
            reconnectionAttempts: Infinity,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            transports: ['websocket', 'polling']
        });

        this.socket.on('connect', () => {
            console.log('Connected to parking server');
            this.connected = true;
            this.updateConnectionStatus(true);
            // Request initial status
            this.socket.emit('request_status');
        });

        this.socket.on('disconnect', () => {
            console.log('Disconnected from parking server');
            this.connected = false;
            this.updateConnectionStatus(false);
        });

        this.socket.on('connect_error', (error) => {
            console.error('Connection error:', error);
            this.updateConnectionStatus(false);
        });

        // Listen for parking updates
        this.socket.on('parking_update', (data) => {
            this.handleParkingUpdate(data);
        });
    }

    startPolling() {
        // Poll API as fallback every 2 seconds
        this.pollingInterval = setInterval(() => {
            this.fetchStatus();
        }, 2000);
    }

    async fetchStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            this.handleParkingUpdate(data);
        } catch (error) {
            console.log('Polling error:', error);
        }
    }

    handleParkingUpdate(data) {
        console.log('Received parking update:', data);
        
        // Get the camera ID from the page (set by template)
        const cameraId = window.CAMERA_ID || 1;
        const cameraKey = `camera${cameraId}`;

        // Handle full status update (from API or initial load)
        if (data.camera1 && data.camera2) {
            // Only update the relevant camera for this page
            const cameraData = data[cameraKey];
            if (cameraData) {
                this.updateCameraStats(cameraKey, cameraData.free, cameraData.occupied);
                // Update totals with only this camera's data
                this.updateTotalStats({
                    total_slots: cameraData.total,
                    free: cameraData.free,
                    occupied: cameraData.occupied
                });
            }
        }

        // Handle camera-specific updates
        if (data.camera_id === cameraKey) {
            this.updateCameraStats(cameraKey, data.free, data.occupied);
            // Update totals for single camera
            this.updateTotalStats({
                total_slots: data.slots ? Object.keys(data.slots).length : 0,
                free: data.free,
                occupied: data.occupied
            });
        }

        // Update timestamp
        if (data.timestamp) {
            document.getElementById('last-update').textContent = data.timestamp;
        }

        // Update slot status display
        if (data.slots) {
            this.updateSlotStatus(data.camera_id, data.slots);
        }
    }

    updateCameraStats(cameraId, free, occupied) {
        const freeElement = document.getElementById(`${cameraId}-free`);
        const occupiedElement = document.getElementById(`${cameraId}-occupied`);

        if (freeElement) {
            freeElement.textContent = free;
            this.animateValue(freeElement);
        }

        if (occupiedElement) {
            occupiedElement.textContent = occupied;
            this.animateValue(occupiedElement);
        }
    }

    updateTotalStats(total) {
        const totalSlotsEl = document.getElementById('total-slots');
        const freeSlotsEl = document.getElementById('free-slots');
        const occupiedSlotsEl = document.getElementById('occupied-slots');
        const availableCountEl = document.getElementById('available-count');

        if (totalSlotsEl) {
            totalSlotsEl.textContent = total.total_slots;
            this.animateValue(totalSlotsEl);
        }

        if (freeSlotsEl) {
            freeSlotsEl.textContent = total.free;
            this.animateValue(freeSlotsEl);
        }

        if (occupiedSlotsEl) {
            occupiedSlotsEl.textContent = total.occupied;
            this.animateValue(occupiedSlotsEl);
        }

        if (availableCountEl) {
            availableCountEl.textContent = total.free;
        }

        // Update slot status text
        const slotStatusEl = document.getElementById('slot-status');
        if (slotStatusEl) {
            if (total.free > 0) {
                slotStatusEl.textContent = 'Available';
                slotStatusEl.style.color = '#22c55e';
            } else {
                slotStatusEl.textContent = 'Full';
                slotStatusEl.style.color = '#ef4444';
            }
        }
    }

    updateSlotStatus(cameraId, slots) {
        // This could be used to show individual slot details
        // For now, we just log it
        const freeSlots = Object.entries(slots).filter(([id, status]) => status === 'free');
        const occupiedSlots = Object.entries(slots).filter(([id, status]) => status === 'occupied');
        
        console.log(`${cameraId}: ${freeSlots.length} free, ${occupiedSlots.length} occupied`);
    }

    animateValue(element) {
        element.classList.add('value-updated');
        setTimeout(() => {
            element.classList.remove('value-updated');
        }, 300);
    }

    updateConnectionStatus(connected) {
        const statusContainer = document.getElementById('connection-status');
        const indicator = statusContainer.querySelector('.status-indicator');
        const text = statusContainer.querySelector('.status-text');

        if (connected) {
            indicator.classList.remove('disconnected');
            indicator.classList.add('connected');
            text.textContent = 'Connected';
        } else {
            indicator.classList.remove('connected');
            indicator.classList.add('disconnected');
            text.textContent = 'Disconnected';
        }
    }

    setupEventListeners() {
        // Switch preview between cameras on click
        const videoFeed1 = document.getElementById('video-feed-1');
        const videoFeed2 = document.getElementById('video-feed-2');
        const previewImage = document.getElementById('preview-image');

        if (videoFeed1) {
            videoFeed1.parentElement.addEventListener('click', () => {
                if (previewImage) {
                    previewImage.src = '/video_feed/1';
                    document.getElementById('slot-title').textContent = 'Parking Lot 1';
                }
            });
        }

        if (videoFeed2) {
            videoFeed2.parentElement.addEventListener('click', () => {
                if (previewImage) {
                    previewImage.src = '/video_feed/2';
                    document.getElementById('slot-title').textContent = 'Parking Lot 2';
                }
            });
        }
    }
}

// Add CSS for animation
const style = document.createElement('style');
style.textContent = `
    .value-updated {
        animation: flash 0.3s ease-out;
    }
    
    @keyframes flash {
        0% { transform: scale(1); }
        50% { transform: scale(1.1); }
        100% { transform: scale(1); }
    }
`;
document.head.appendChild(style);

// Initialize the parking monitor when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.parkingMonitor = new ParkingMonitor();
});
