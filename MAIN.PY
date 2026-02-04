# main.py
# Entry point - ONLY file that auto-executes
# sensor.reset() appears ONCE here

import sensor
import os
from utils import load_env
from take_img import take_image
from line_detection import process_image
from filter import filter_line_segments
from gaps import normalize_gaps
from intersection import check_lines_in_dict

# ============================================================================
# Configuration
# ============================================================================

OFFSET_Y = 0
MAX_GAP = 25
MIN_GAP = 10
FIXED_HEIGHT = 3
BBOX_WIDTH = 50
LEFT_SEGMENT_INDEX = 0
RIGHT_SEGMENT_INDEX = 2
USE_CALIBRATED_CAPTURE = True
DUMMY_IMAGE_PATH = "IMG_2796.bin"

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
        config = load_env("env.txt")
        # Return dict format expected by process_image
        return config
    except Exception as e:
        print("Warning: Could not load config from env.txt: {}".format(e))
        print("Using default ROI offsets")
        return {"LEFT_ROI": "30", "CENTER_ROI": "300", "RIGHT_ROI": "550"}

# ============================================================================
# Main Pipeline
# ============================================================================

# Load configuration (dict format for process_image)
roi_config = load_config()
print("Loaded ROI config: {}".format(roi_config))

# Base ROI offsets (designed for VGA 640x480)
BASE_WIDTH = 640
BASE_LEFT_OFFSET = int(roi_config.get("LEFT_ROI", "30"))
BASE_CENTER_OFFSET = int(roi_config.get("CENTER_ROI", "300"))
BASE_RIGHT_OFFSET = int(roi_config.get("RIGHT_ROI", "550"))

# Step 1: Capture image
if USE_CALIBRATED_CAPTURE:
    print("Capturing calibrated image...")
    image_path, img_width, img_height = take_image()
else:
    print("Using dummy image: {}".format(DUMMY_IMAGE_PATH))
    image_path = DUMMY_IMAGE_PATH
    img_width, img_height = 640, 480  # Assume VGA for dummy

# Scale ROI offsets based on actual resolution
scale_factor = img_width / BASE_WIDTH
LEFT_OFFSET = int(BASE_LEFT_OFFSET * scale_factor)
CENTER_OFFSET = int(BASE_CENTER_OFFSET * scale_factor)
RIGHT_OFFSET = int(BASE_RIGHT_OFFSET * scale_factor)
print("Scaled ROI offsets ({}x): LEFT={}, CENTER={}, RIGHT={}".format(
    round(scale_factor, 2), LEFT_OFFSET, CENTER_OFFSET, RIGHT_OFFSET))

# Create scaled config for process_image
scaled_roi_config = {
    "LEFT_ROI": str(LEFT_OFFSET),
    "CENTER_ROI": str(CENTER_OFFSET),
    "RIGHT_ROI": str(RIGHT_OFFSET)
}

# Step 2: Process image and detect line segments
print("Processing image and detecting segments...")
processed_file = process_image(image_path, scaled_roi_config, OFFSET_Y, 
                               img_width=img_width, img_height=img_height)
if processed_file is None:
    raise RuntimeError("Image processing failed")

# Step 3: Filter line segments
print("Filtering line segments...")
output_file = filter_line_segments(processed_file, OFFSET_Y)
if output_file is None:
    raise RuntimeError("Line segment filtering failed")

# Step 4: Normalize gaps for left and right segments
print("Normalizing gaps for left and right segments...")
final_segments_left = normalize_gaps(
    output_file, 
    max_gap=MAX_GAP, 
    min_gap=MIN_GAP, 
    segment_index=LEFT_SEGMENT_INDEX
)
final_segments_right = normalize_gaps(
    output_file, 
    max_gap=MAX_GAP, 
    min_gap=MIN_GAP, 
    segment_index=RIGHT_SEGMENT_INDEX
)

# Step 5: Detect wafer positions
print("\nWafer positions found using the Left segments:")
left_results = check_lines_in_dict(
    final_segments_left,
    LEFT_OFFSET,
    CENTER_OFFSET,
    fixed_height=FIXED_HEIGHT,
    width=BBOX_WIDTH
)

print("\nWafer positions found using the Right segments:")
right_results = check_lines_in_dict(
    final_segments_right,
    RIGHT_OFFSET,
    CENTER_OFFSET,
    fixed_height=FIXED_HEIGHT,
    width=BBOX_WIDTH
)

# Step 6: Report results
total_wafers = max(left_results, right_results)
print("\n" + "="*50)
print("Total number of Wafers found: {}".format(total_wafers))
print("="*50)

# No __name__ == "__main__" block - OpenMV auto-runs main.py
