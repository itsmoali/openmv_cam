from utils import log
import time
from gap import normalize_gaps, check_lines_in_file
from utils import log_data_to_file, load_env
from take_img import take_image
from bmp_line_detection import process_image
from estimate import extract_boundary_segments, get_box_reference_metrics
from filter import filter_line_segments
import sensor



# ------ MAIN CONFIG-----------

MODE = "GAP_ANALYSIS" # Options: "VIRTUAL_SLOTS", "GAP_ANALYSIS"

OFFSET_Y = 0
MAX_GAP = 40
MIN_GAP = 20
FIXED_HEIGHT = 10
BBOX_WIDTH = 50
LEFT_SEGMENT_INDEX = 0
RIGHT_SEGMENT_INDEX = 2
USE_CALIBRATED_CAPTURE = True
DUMMY_IMAGE_PATH = "IMG_2796.bin"
# Used for Virutal slot detection
VIRTUAL_HEIGHT = 920.0
VIRTUAL_START_POS= 100.0
VIRTUAL_GAP = 30.0


# ============================================================================
# Boot sequence
# ============================================================================

sensor.reset()

# ============================================================================
# Helper Functions
# ============================================================================

def load_config():
    """Load configuration from env.txt file. Returns dict for process_image()."""
    try:
        config = load_env("e.txt")
        # Return dict format expected by process_image
        return config
    except Exception as e:
        print("Warning: Could not load config from env.txt: {}".format(e))
        print("Using default ROI offsets")
        return {"LEFT_ROI": "200", "CENTER_ROI": "800", "RIGHT_ROI": "1500"}

def analyze_virtual_slots(filtered_groups, box_top, box_height, roi_config):
    """
    Creates 24 virtual windows starting 100px from the box top and checks for disks.

    Args:
        filtered_groups: Dict of filtered lines.
        box_top: The average Y coordinate of the box's top boundary.
        box_height: The average vertical height of the box (Bottom Y - Top Y).
    """
    # Calculate Scaling Factor (Current Height / Reference Height)
    S = box_height / VIRTUAL_HEIGHT


    # Scaled reference values
    scaled_offset = VIRTUAL_START_POS * S
    scaled_pitch = VIRTUAL_GAP * S
    window_half_height = scaled_pitch / 2.0  # Window size to prevent overlap

    # Get center detections from the 800 offset
    roi_center = int(roi_config.get("CENTER_ROI", 800))
    center_disks = filtered_groups.get(roi_center, [])

    inventory = {}

    for i in range(1, 25):  # Slots 1 through 24
        # Calculate the expected center Y for this slot
        expected_y = box_top + scaled_offset + ((i - 1) * scaled_pitch)

        # Define the virtual bounding box (Window)
        win_top = expected_y - window_half_height
        win_bottom = expected_y + window_half_height

        # Check if any detected disk falls within this window
        found_disk = None
        for disk in center_disks:
            disk_y = (disk['y1'] + disk['y2']) / 2.0
            if win_top <= disk_y <= win_bottom:
                found_disk = disk
                break

        inventory[f"Slot_{i}"] = {
            "status": "Occupied" if found_disk else "Empty",
            "expected_y": round(expected_y, 1),
            "actual_y": round((found_disk['y1'] + found_disk['y2']) / 2.0, 1) if found_disk else None
        }

    return inventory

roi_config = load_config()
print("Loaded ROI config: {}".format(roi_config))

if USE_CALIBRATED_CAPTURE:
    print("Capturing calibrated image...")
    image_path, img_width, img_height = take_image()
else:
    print("Using dummy image: {}".format(DUMMY_IMAGE_PATH))
    image_path = DUMMY_IMAGE_PATH
    img_width, img_height = 1920, 1080  # Assume FHD for dummy

# ============================================================================
# Main Pipeline
# ============================================================================

#--------------------- Virtual Slot Estimation Mode--------------
if MODE == "VIRTUAL_SLOTS":
    print("--- Running Virtual Slot Estimation ---")
    pre_process = process_image(image_path, coords=roi_config, offset_y=OFFSET_Y,
                                sensor_type="FHD", logs=False)

    log_data_to_file(pre_process, filename='pre_process.json')

    # Get boundaries to establish the box frame
    boundaries = extract_boundary_segments(pre_process)
    box_top, current_box_height = get_box_reference_metrics(boundaries)

    # Map slots based on pre-defined positioning and the detected box dimensions
    inventory = analyze_virtual_slots(pre_process, box_top, current_box_height, roi_config)

    # Sort inventory by slot number for display
    sorted_slots = sorted(inventory.keys(), key=lambda x: int(x.split('_')[1]))
    for slot_id in sorted_slots:
        data = inventory[slot_id]
        status = data["status"]
        y_val = data['actual_y']
        print(f"[{slot_id}]: {status}" + (f" at Y={y_val}" if y_val else ""))

    occupied_count = sum(1 for s in inventory.values() if s["status"] == "Occupied")
    print(f"\nTotal Disks (Estimation): {occupied_count} / 24")

    # --- LOGGING ---
    roi_center = int(roi_config.get("CENTER_ROI", 800))
    visual_data = { str(roi_center): [] }

    # Scaling math for the boxes
    S = current_box_height / VIRTUAL_HEIGHT
    win_h = int((VIRTUAL_GAP * S) / 2.0)
    half_w = 55 # Box width

    for slot_id in sorted_slots:
        data = inventory[slot_id]
        y_mid = int(data["expected_y"])

        # Define Box Edges
        top, bot = y_mid - (win_h // 2), y_mid + (win_h // 2)
        l_edge, r_edge = roi_center - half_w, roi_center + half_w

        # 1. Add 4 lines for the Bounding Box (Normal thickness)
        visual_data[str(roi_center)].extend([
            {"x1": l_edge, "y1": top, "x2": r_edge, "y2": top},
            {"x1": l_edge, "y1": bot, "x2": r_edge, "y2": bot},
            {"x1": l_edge, "y1": top, "x2": l_edge, "y2": bot},
            {"x1": r_edge, "y1": top, "x2": r_edge, "y2": bot}
        ])

        # 2. Add the Detected Line (Marked for Boldness)
        if data["status"] == "Occupied" and data["actual_y"]:
            ay = int(data["actual_y"])
            visual_data[str(roi_center)].append(
                {"x1": l_edge + 5, "y1": ay, "x2": r_edge - 5, "y2": ay, "is_bold": True}
            )

    # Log the formatted visual lines and trigger the drawing function
    log_data_to_file(visual_data, filename='virtual_slots.json')


#------------------------ Gap Analysis Mode -------------------------
elif MODE == "GAP_ANALYSIS":
    print("--- Running Gap Analysis ---")
    pre_process = process_image(image_path, coords=roi_config, offset_y=OFFSET_Y,
                                sensor_type="FHD", logs=False)
    log_data_to_file(pre_process, filename='pre_process.json')

    # Filter lines for horizontal consistency
    filtered = filter_line_segments(pre_process, offset_y=0, logs=False)
    log_data_to_file(filtered, filename='filtered.json')

    # --- DYNAMIC ROI EXTRACTION ---
    # We extract these from roi_config and convert to int for the analysis functions
    roi_left   = int(roi_config.get("LEFT_ROI", 200))
    roi_center = int(roi_config.get("CENTER_ROI", 800))
    roi_right  = int(roi_config.get("RIGHT_ROI", 1500))
    print(f"Using ROIs - Left: {roi_left}, Center: {roi_center}, Right: {roi_right}")

    # Calculate Gaps for both sides
    # Side 1: Left to Center
    left_gaps = normalize_gaps(filtered, max_gap=MAX_GAP, min_gap=MIN_GAP, segment_index=LEFT_SEGMENT_INDEX)
    log_data_to_file(left_gaps, filename='left_gaps.json')

    # Side 2: Center to Right
    right_gaps = normalize_gaps(filtered, max_gap=MAX_GAP, min_gap=MIN_GAP, segment_index=RIGHT_SEGMENT_INDEX)
    log_data_to_file(right_gaps, filename='right_gaps.json')

    # Analyze the gaps using the dynamic ROI constants
    # check_lines_in_file(filename, start_x, end_x, ...)
    left_results, left_arr = check_lines_in_file('left_gaps.json', roi_left, roi_center,
                                                fixed_height=FIXED_HEIGHT, width=BBOX_WIDTH)

    right_results, right_arr = check_lines_in_file('right_gaps.json', roi_center, roi_right,
                                                  fixed_height=FIXED_HEIGHT, width=BBOX_WIDTH)

    print(f"--- Results for ROIs: {roi_left}, {roi_center}, {roi_right} ---")
    print(f"Left Gap Results: {left_results}")
    print(f"Left Array: {left_arr}")
    print(f"Right Gap Results: {right_results}")
    print(f"Right Array: {right_arr}")

