import cv2
import json
import numpy as np

# Load parking slots and convert to tuples
with open("parking_slots2.json") as f:
    parking_slots_data = json.load(f)
    parking_slots = {k: [tuple(pt) for pt in v] for k, v in parking_slots_data.items()}

cap = cv2.VideoCapture("2.mp4")

# Get original frame size and calculate resize scale
ret_test, frame_test = cap.read()
if ret_test:
    max_width = 1280
    h, w = frame_test.shape[:2]
    if w > max_width:
        scale = max_width / w
        new_size = (int(w * scale), int(h * scale))
        print(f"Resizing from {w}x{h} to {new_size[0]}x{new_size[1]}")
    else:
        scale = 1.0
        new_size = (w, h)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Reset to beginning
else:
    scale = 1.0
    new_size = None


def is_occupied_by_pixels(frame, slot_points, edge_threshold=8, std_threshold=35):
    """
    Determine if a parking slot is occupied by analyzing pixel content.
    
    - Empty slots (asphalt) have low edge density and uniform color
    - Occupied slots (cars) have high edge density and varied colors
    """
    # Get bounding rect for efficiency
    pts = np.array(slot_points, np.int32)
    x, y, w, h = cv2.boundingRect(pts)
    
    if w == 0 or h == 0:
        return False
    
    # Clamp to frame boundaries
    frame_h, frame_w = frame.shape[:2]
    x = max(0, x)
    y = max(0, y)
    x2 = min(x + w, frame_w)
    y2 = min(y + h, frame_h)
    w = x2 - x
    h = y2 - y
    
    if w <= 0 or h <= 0:
        return False
    
    # Create mask for this slot (same size as bounding rect)
    mask = np.zeros((h, w), dtype=np.uint8)
    # Shift points to local coordinates
    shifted_pts = pts - [x, y]
    # Clamp shifted points to valid range
    shifted_pts = np.clip(shifted_pts, [0, 0], [w - 1, h - 1])
    cv2.fillPoly(mask, [shifted_pts], 255)
    
    # Extract the slot region
    slot_region = frame[y:y2, x:x2]
    
    if slot_region.size == 0 or slot_region.shape[0] != h or slot_region.shape[1] != w:
        return False
    
    # Convert to grayscale
    gray = cv2.cvtColor(slot_region, cv2.COLOR_BGR2GRAY)
    
    # Apply mask to grayscale
    masked_gray = cv2.bitwise_and(gray, gray, mask=mask)
    
    # Detect edges using Canny
    edges = cv2.Canny(masked_gray, 50, 150)
    
    # Count non-zero pixels (edges) within the mask
    edge_pixels = cv2.countNonZero(cv2.bitwise_and(edges, edges, mask=mask))
    mask_pixels = cv2.countNonZero(mask)
    
    if mask_pixels == 0:
        return False
    
    # Calculate edge density (percentage of edge pixels)
    edge_density = (edge_pixels / mask_pixels) * 100
    
    # Calculate standard deviation of pixel values within the mask
    mean, std = cv2.meanStdDev(gray, mask=mask)
    std_value = np.mean(std)
    
    # Slot is occupied if edge density OR color variance is high
    # Tune these thresholds based on your video
    is_occupied = edge_density > edge_threshold or std_value > std_threshold
    
    return is_occupied


while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Resize frame to match slot_marker2 resolution
    if new_size:
        frame = cv2.resize(frame, new_size)

    free, occupied = 0, 0

    for slot_id, pts in parking_slots.items():
        occupied_flag = is_occupied_by_pixels(frame, pts)

        color = (0, 0, 255) if occupied_flag else (0, 255, 0)
        label = "OCCUPIED" if occupied_flag else "FREE"

        if occupied_flag:
            occupied += 1
        else:
            free += 1

        cv2.polylines(frame, [np.array(pts, np.int32)], True, color, 2)
        
        # Position text at top-left of the slot with offset
        text_pos = (pts[0][0], pts[0][1] - 5)
        cv2.putText(
            frame,
            f"{slot_id} {label}",
            text_pos,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2
        )

    cv2.putText(
        frame,
        f"FREE: {free}  OCCUPIED: {occupied}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 255, 255),
        2
    )

    cv2.imshow("Smart Parking", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
