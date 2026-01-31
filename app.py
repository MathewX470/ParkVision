import cv2
import json
import numpy as np
import threading
import time
from flask import Flask, render_template, Response, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'parkvision_secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Load parking slots for both cameras
with open("parking_slots.json") as f:
    parking_slots_data1 = json.load(f)
    parking_slots1 = {k: [tuple(pt) for pt in v] for k, v in parking_slots_data1.items()}

with open("parking_slots2.json") as f:
    parking_slots_data2 = json.load(f)
    parking_slots2_raw = {k: [tuple(pt) for pt in v] for k, v in parking_slots_data2.items()}


def scale_parking_slots(slots, original_width, original_height, target_width, target_height):
    """Scale parking slot coordinates from one resolution to another"""
    scale_x = target_width / original_width
    scale_y = target_height / original_height
    
    scaled_slots = {}
    for slot_id, points in slots.items():
        scaled_points = [(int(x * scale_x), int(y * scale_y)) for x, y in points]
        scaled_slots[slot_id] = scaled_points
    
    return scaled_slots


# parking_slots2 was marked at 1280x720, actual video is 3840x2160
# Scale coordinates to match actual video resolution
parking_slots2 = scale_parking_slots(parking_slots2_raw, 1280, 720, 3840, 2160)

# Global state
parking_status = {
    "camera1": {"free": 0, "occupied": 0, "total": len(parking_slots1), "slots": {}},
    "camera2": {"free": 0, "occupied": 0, "total": len(parking_slots2), "slots": {}}
}

# Frame storage for thread-safe access
current_frames = {
    "camera1": None,
    "camera2": None
}
frame_locks = {
    "camera1": threading.Lock(),
    "camera2": threading.Lock()
}


def is_occupied_by_pixels(frame, slot_points, edge_threshold=8, std_threshold=35):
    """
    Determine if a parking slot is occupied by analyzing pixel content.
    """
    pts = np.array(slot_points, np.int32)
    x, y, w, h = cv2.boundingRect(pts)
    
    if w == 0 or h == 0:
        return False
    
    frame_h, frame_w = frame.shape[:2]
    x = max(0, x)
    y = max(0, y)
    x2 = min(x + w, frame_w)
    y2 = min(y + h, frame_h)
    w = x2 - x
    h = y2 - y
    
    if w <= 0 or h <= 0:
        return False
    
    mask = np.zeros((h, w), dtype=np.uint8)
    shifted_pts = pts - [x, y]
    shifted_pts = np.clip(shifted_pts, [0, 0], [w - 1, h - 1])
    cv2.fillPoly(mask, [shifted_pts], 255)
    
    slot_region = frame[y:y2, x:x2]
    
    if slot_region.size == 0 or slot_region.shape[0] != h or slot_region.shape[1] != w:
        return False
    
    gray = cv2.cvtColor(slot_region, cv2.COLOR_BGR2GRAY)
    masked_gray = cv2.bitwise_and(gray, gray, mask=mask)
    edges = cv2.Canny(masked_gray, 50, 150)
    
    edge_pixels = cv2.countNonZero(cv2.bitwise_and(edges, edges, mask=mask))
    mask_pixels = cv2.countNonZero(mask)
    
    if mask_pixels == 0:
        return False
    
    edge_density = (edge_pixels / mask_pixels) * 100
    mean, std = cv2.meanStdDev(gray, mask=mask)
    std_value = np.mean(std)
    
    is_occupied = edge_density > edge_threshold or std_value > std_threshold
    return is_occupied


def process_frame(frame, parking_slots):
    """Process a single frame and return annotated frame with slot status"""
    free, occupied = 0, 0
    slots_status = {}
    
    for slot_id, pts in parking_slots.items():
        occupied_flag = is_occupied_by_pixels(frame, pts)
        
        color = (0, 0, 255) if occupied_flag else (0, 255, 0)
        status = "occupied" if occupied_flag else "free"
        
        if occupied_flag:
            occupied += 1
        else:
            free += 1
        
        slots_status[slot_id] = status
        
        # Draw polygon
        cv2.polylines(frame, [np.array(pts, np.int32)], True, color, 2)
        
        # Draw fill with transparency
        overlay = frame.copy()
        cv2.fillPoly(overlay, [np.array(pts, np.int32)], color)
        cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
    
    return frame, free, occupied, slots_status


class VideoProcessor(threading.Thread):
    def __init__(self, video_path, parking_slots, camera_id, socketio_instance):
        super().__init__(daemon=True)
        self.video_path = video_path
        self.parking_slots = parking_slots
        self.camera_id = camera_id
        self.socketio_instance = socketio_instance
        self.running = True
        self.last_emit_time = 0
        self.emit_interval = 0.5  # Emit every 0.5 seconds
        
    def run(self):
        print(f"Starting video processor for {self.camera_id}: {self.video_path}")
        
        cap = cv2.VideoCapture(self.video_path)
        
        if not cap.isOpened():
            print(f"ERROR: Could not open video {self.video_path}")
            return
        
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frame_delay = 1.0 / min(fps, 30)  # Cap at 30 fps
        
        print(f"{self.camera_id}: Video opened successfully. FPS: {fps}")
        
        while self.running and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                # Loop the video
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            
            # Process frame
            processed_frame, free, occupied, slots_status = process_frame(frame.copy(), self.parking_slots)
            
            # Update global status
            parking_status[self.camera_id] = {
                "free": free,
                "occupied": occupied,
                "total": len(self.parking_slots),
                "slots": slots_status
            }
            
            # Store frame for streaming
            with frame_locks[self.camera_id]:
                current_frames[self.camera_id] = processed_frame.copy()
            
            # Emit status update via SocketIO (throttled)
            current_time = time.time()
            if current_time - self.last_emit_time >= self.emit_interval:
                self.last_emit_time = current_time
                
                total_free = parking_status["camera1"]["free"] + parking_status["camera2"]["free"]
                total_occupied = parking_status["camera1"]["occupied"] + parking_status["camera2"]["occupied"]
                total_slots = parking_status["camera1"]["total"] + parking_status["camera2"]["total"]
                
                try:
                    self.socketio_instance.emit('parking_update', {
                        'camera_id': self.camera_id,
                        'free': free,
                        'occupied': occupied,
                        'slots': slots_status,
                        'total': {
                            'total_slots': total_slots,
                            'free': total_free,
                            'occupied': total_occupied
                        },
                        'timestamp': time.strftime('%I:%M %p')
                    })
                except Exception as e:
                    print(f"Socket emit error: {e}")
            
            time.sleep(frame_delay)
        
        cap.release()
    
    def stop(self):
        self.running = False


# Global video processors
video_processor1 = None
video_processor2 = None


def generate_frames(camera_id):
    """Generate frames for video streaming"""
    print(f"Starting frame generator for {camera_id}")
    
    while True:
        with frame_locks[camera_id]:
            frame = current_frames[camera_id]
        
        if frame is not None:
            # Resize for web display
            resized = cv2.resize(frame, (640, 360))
            _, buffer = cv2.imencode('.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        else:
            # Send a placeholder frame while waiting
            placeholder = np.zeros((360, 640, 3), dtype=np.uint8)
            cv2.putText(placeholder, "Loading...", (250, 180), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            _, buffer = cv2.imencode('.jpg', placeholder)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        time.sleep(0.033)  # ~30 fps


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """REST API endpoint for current status"""
    total_free = parking_status["camera1"]["free"] + parking_status["camera2"]["free"]
    total_occupied = parking_status["camera1"]["occupied"] + parking_status["camera2"]["occupied"]
    total_slots = parking_status["camera1"]["total"] + parking_status["camera2"]["total"]
    
    return jsonify({
        'camera1': parking_status["camera1"],
        'camera2': parking_status["camera2"],
        'total': {
            'total_slots': total_slots,
            'free': total_free,
            'occupied': total_occupied
        },
        'timestamp': time.strftime('%I:%M %p')
    })


@app.route('/video_feed/1')
def video_feed_1():
    return Response(generate_frames("camera1"),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/video_feed/2')
def video_feed_2():
    return Response(generate_frames("camera2"),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@socketio.on('connect')
def handle_connect():
    print('Client connected')
    # Send initial status
    total_free = parking_status["camera1"]["free"] + parking_status["camera2"]["free"]
    total_occupied = parking_status["camera1"]["occupied"] + parking_status["camera2"]["occupied"]
    total_slots = parking_status["camera1"]["total"] + parking_status["camera2"]["total"]
    
    emit('parking_update', {
        'camera1': parking_status["camera1"],
        'camera2': parking_status["camera2"],
        'total': {
            'total_slots': total_slots,
            'free': total_free,
            'occupied': total_occupied
        },
        'timestamp': time.strftime('%I:%M %p')
    })


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')


@socketio.on('request_status')
def handle_request_status():
    """Handle explicit status request from client"""
    total_free = parking_status["camera1"]["free"] + parking_status["camera2"]["free"]
    total_occupied = parking_status["camera1"]["occupied"] + parking_status["camera2"]["occupied"]
    total_slots = parking_status["camera1"]["total"] + parking_status["camera2"]["total"]
    
    emit('parking_update', {
        'camera1': parking_status["camera1"],
        'camera2': parking_status["camera2"],
        'total': {
            'total_slots': total_slots,
            'free': total_free,
            'occupied': total_occupied
        },
        'timestamp': time.strftime('%I:%M %p')
    })


if __name__ == '__main__':
    print("=" * 50)
    print("Starting Smart Parking System...")
    print("=" * 50)
    
    # Start video processors (daemon threads will stop when main exits)
    video_processor1 = VideoProcessor("carPark.mp4", parking_slots1, "camera1", socketio)
    video_processor2 = VideoProcessor("2.mp4", parking_slots2, "camera2", socketio)
    
    video_processor1.start()
    video_processor2.start()
    
    print("Video processors started!")
    print(f"Parking Lot 1: {len(parking_slots1)} slots")
    print(f"Parking Lot 2: {len(parking_slots2)} slots")
    print("Server will be available at http://127.0.0.1:5000")
    print("=" * 50)
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
