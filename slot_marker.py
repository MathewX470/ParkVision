import cv2
import json
import numpy as np

slots = {}
slot_id = 1
drawing = False
start_point = None
end_point = None
last_slot = None  # Store last slot for duplication
offset_x = 0  # Offset for duplication
offset_y = 35  # Default vertical offset (adjust with arrow keys)

# Load existing slots if file exists
try:
    with open("parking_slots.json", "r") as f:
        existing = json.load(f)
        slots = {k: [tuple(pt) for pt in v] for k, v in existing.items()}
        if slots:
            slot_id = max(int(k[1:]) for k in slots.keys()) + 1
            # Get last slot for potential duplication
            last_key = f"S{slot_id - 1}"
            if last_key in slots:
                last_slot = slots[last_key]
        print(f"Loaded {len(slots)} existing slots")
except FileNotFoundError:
    print("Starting fresh - no existing slots")


def rect_to_points(x1, y1, x2, y2):
    """Convert rectangle corners to 4-point polygon (top-left, top-right, bottom-right, bottom-left)"""
    return [
        (min(x1, x2), min(y1, y2)),  # top-left
        (max(x1, x2), min(y1, y2)),  # top-right
        (max(x1, x2), max(y1, y2)),  # bottom-right
        (min(x1, x2), max(y1, y2))   # bottom-left
    ]


def duplicate_slot(slot_points, dx, dy):
    """Duplicate a slot with offset"""
    return [(x + dx, y + dy) for x, y in slot_points]


def mouse_callback(event, x, y, flags, param):
    global drawing, start_point, end_point, slots, slot_id, last_slot

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        start_point = (x, y)
        end_point = (x, y)

    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            end_point = (x, y)

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        end_point = (x, y)
        
        # Create slot from rectangle
        if start_point and end_point and start_point != end_point:
            points = rect_to_points(start_point[0], start_point[1], end_point[0], end_point[1])
            slots[f"S{slot_id}"] = points
            last_slot = points
            print(f"Created S{slot_id}: {points}")
            slot_id += 1
            start_point = None
            end_point = None


def draw_frame(frame):
    """Draw all slots and current rectangle being drawn"""
    display = frame.copy()
    
    # Draw existing slots
    for sid, pts in slots.items():
        pts_array = np.array(pts, np.int32)
        cv2.polylines(display, [pts_array], True, (0, 255, 0), 2)
        cv2.putText(display, sid, pts[0], cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    # Draw rectangle being drawn
    if drawing and start_point and end_point:
        cv2.rectangle(display, start_point, end_point, (255, 255, 0), 2)
    
    # Draw preview of next duplicate position if we have a last slot
    if last_slot:
        preview = duplicate_slot(last_slot, offset_x, offset_y)
        pts_array = np.array(preview, np.int32)
        cv2.polylines(display, [pts_array], True, (255, 0, 255), 1)  # Magenta preview
        cv2.putText(display, f"[D to place S{slot_id}]", preview[0], cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)
    
    # Instructions
    instructions = [
        "DRAG: Draw rectangle slot",
        "F: Duplicate last slot",
        "W/S: Offset up/down",
        "A/D: Offset left/right",
        "U: Undo last slot",
        "P: Save & Exit",
        "ESC: Exit without save"
    ]
    for i, text in enumerate(instructions):
        cv2.putText(display, text, (10, 25 + i * 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    cv2.putText(display, f"Offset: ({offset_x}, {offset_y})", (10, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    cv2.putText(display, f"Slots: {len(slots)}", (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    
    return display


# Load video frame
cap = cv2.VideoCapture("carPark.mp4")
ret, frame = cap.read()
cap.release()

if not ret:
    print("Error: Could not read video")
    exit()

window_name = "Slot Marker"
cv2.namedWindow(window_name)
cv2.setMouseCallback(window_name, mouse_callback)

print("\n=== IMPROVED SLOT MARKER ===")
print("DRAG to draw rectangle slots")
print("Press D to duplicate last slot with offset")
print("Arrow keys to adjust duplication offset")
print("Press U to undo last slot")
print("Press S to save and exit")
print("Press ESC to exit without saving\n")

while True:
    display = draw_frame(frame)
    cv2.imshow(window_name, display)
    
    key = cv2.waitKey(30) & 0xFF
    
    if key == 27:  # ESC - exit without saving
        print("Exited without saving")
        break
    
    elif key == ord('p') or key == ord('P'):  # Save and exit
        with open("parking_slots.json", "w") as f:
            # Convert tuples to lists for JSON
            json_slots = {k: [list(pt) for pt in v] for k, v in slots.items()}
            json.dump(json_slots, f, indent=4)
        print(f"\n✅ Saved {len(slots)} slots to parking_slots.json")
        break
    
    elif key == ord('f') or key == ord('F'):  # Duplicate
        if last_slot:
            new_slot = duplicate_slot(last_slot, offset_x, offset_y)
            slots[f"S{slot_id}"] = new_slot
            last_slot = new_slot
            print(f"Duplicated to S{slot_id}")
            slot_id += 1
        else:
            print("No slot to duplicate - draw one first!")
    
    elif key == ord('u') or key == ord('U'):  # Undo
        if slot_id > 1:
            slot_id -= 1
            key_to_remove = f"S{slot_id}"
            if key_to_remove in slots:
                del slots[key_to_remove]
                # Update last_slot to previous one
                if slot_id > 1:
                    last_slot = slots.get(f"S{slot_id - 1}")
                else:
                    last_slot = None
                print(f"Undone {key_to_remove}")
    
    elif key == ord('w') or key == ord('W'):  # W - Up
        offset_y -= 5
        print(f"Offset: ({offset_x}, {offset_y})")
    
    elif key == ord('s') or key == ord('S'):  # S - Down
        offset_y += 5
        print(f"Offset: ({offset_x}, {offset_y})")
    
    elif key == ord('a') or key == ord('A'):  # A - Left
        offset_x -= 5
        print(f"Offset: ({offset_x}, {offset_y})")
    
    elif key == ord('d') or key == ord('D'):  # D - Right
        offset_x += 5
        print(f"Offset: ({offset_x}, {offset_y})")

cv2.destroyAllWindows()
