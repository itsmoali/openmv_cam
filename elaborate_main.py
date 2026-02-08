from utils import log
import time
from gap import normalize_gaps, check_lines_in_file
from utils import log_data_to_file, load_env
import image
import sensor
import struct
import os


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


# -------------------------------------------------
# SD mount (your firmware uses /sdcard)
# -------------------------------------------------
SD_ROOT = "/sdcard"

# -------------------------------------------------
# Configuration for Calibration
# -------------------------------------------------

# Metering (fast, safe)
METER_FRAMESIZE = sensor.QVGA
METER_PIXFORMAT = sensor.RGB565

# Final capture
FINAL_FRAMESIZE = sensor.FHD
FINAL_PIXFORMAT = sensor.GRAYSCALE

# Exposure / gain limits
EXPOSURE_MIN_US = 2000
EXPOSURE_MAX_US = 600000
FINAL_EXPOSURE_MAX_US = 400000

GAIN_MIN_DB = 0
GAIN_MAX_DB = 24

# Histogram targets (8-bit luminance)
TARGET_Q10 = 40
TARGET_Q50 = 120
TARGET_Q95 = 245

MAX_CLIP_LO = 0.01
MAX_CLIP_HI = 0.004

# Iteration control
MAX_ITERS = 8
EXPOSURE_UP_FACTOR = 1.5
EXPOSURE_DOWN_FACTOR = 0.85

# Histogram sampling
SAMPLE_STEP = 4

# Output (raw grayscale bytes)
OUT_PATH = SD_ROOT + "/final.bmp"



# ============================================================================
# Redundant Function (Quirk--SHOULD BE IGNORED)
# ============================================================================

# -------------------------------------------------
# Helpers
# -------------------------------------------------

def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x

def settle(ms):
    sensor.skip_frames(time=ms)

def force_exposure(us):
    sensor.set_auto_exposure(False)
    sensor.set_auto_exposure(False, exposure_us=int(us))

def force_gain(db):
    sensor.set_auto_gain(False)
    sensor.set_auto_gain(False, gain_db=float(db))

# -------------------------------------------------
# RGB -> luminance
# -------------------------------------------------

def rgb_to_luma(px):
    if isinstance(px, tuple):
        r, g, b = px
    else:
        r5 = (px >> 11) & 0x1F
        g6 = (px >> 5)  & 0x3F
        b5 = px & 0x1F
        r = (r5 * 255) // 31
        g = (g6 * 255) // 63
        b = (b5 * 255) // 31
    return (77*r + 150*g + 29*b) >> 8

# -------------------------------------------------
# Histogram utilities
# -------------------------------------------------

def histogram_from_image(img):
    w, h = img.width(), img.height()
    bins = [0] * 256
    total = 0
    for y in range(0, h, SAMPLE_STEP):
        for x in range(0, w, SAMPLE_STEP):
            y8 = rgb_to_luma(img.get_pixel(x, y))
            bins[y8] += 1
            total += 1
    return bins, total


def quantile(bins, total, q):
    if total == 0:
        return 0
    tgt = total * q
    acc = 0
    for i, c in enumerate(bins):
        acc += c
        if acc >= tgt:
            return i
    return 255


def clip_fractions(bins, total):
    lo = sum(bins[0:6]) / total if total else 0
    hi = sum(bins[250:256]) / total if total else 0
    return lo, hi

# -------------------------------------------------
# Exposure calibration
# -------------------------------------------------

def calibrate(verbose=True):
    print("Calibrating exposure…")

    sensor.set_pixformat(METER_PIXFORMAT)
    sensor.set_framesize(METER_FRAMESIZE)
    sensor.set_auto_whitebal(False)

    # Start from auto baseline
    sensor.set_auto_exposure(True)
    sensor.set_auto_gain(True)
    settle(800)

    try:
        exp = sensor.get_exposure_us()
    except:
        exp = 20000
    try:
        gain = sensor.get_gain_db()
    except:
        gain = 6.0

    sensor.set_auto_exposure(False)
    sensor.set_auto_gain(False)

    force_exposure(exp)
    force_gain(gain)
    settle(200)

    for i in range(MAX_ITERS):
        img = sensor.snapshot()
        bins, total = histogram_from_image(img)

        q10 = quantile(bins, total, 0.10)
        q50 = quantile(bins, total, 0.50)
        q95 = quantile(bins, total, 0.95)
        clip_lo, clip_hi = clip_fractions(bins, total)

        if verbose:
            print(
                "iter", i,
                "exp", int(exp),
                "gain", round(gain,1),
                "q10", q10,
                "q50", q50,
                "q95", q95,
                "clip_lo", round(clip_lo,3),
                "clip_hi", round(clip_hi,3)
            )

        shadows_ok = (q10 >= TARGET_Q10) and (clip_lo <= MAX_CLIP_LO)
        mids_ok    = abs(q50 - TARGET_Q50) <= 20
        highs_ok   = (q95 <= TARGET_Q95) and (clip_hi <= MAX_CLIP_HI)

        if shadows_ok and mids_ok and highs_ok:
            break

        # Lift shadows / mids
        if (not shadows_ok) or (q50 < TARGET_Q50):
            if exp < EXPOSURE_MAX_US:
                exp = clamp(exp * EXPOSURE_UP_FACTOR,
                            EXPOSURE_MIN_US, EXPOSURE_MAX_US)
                force_exposure(exp)
                settle(200)
                continue
            elif gain < GAIN_MAX_DB:
                gain = clamp(gain + 2.0, GAIN_MIN_DB, GAIN_MAX_DB)
                force_gain(gain)
                settle(200)
                continue

        # Pull back highlights if mass-clipping
        if not highs_ok:
            exp = clamp(exp * EXPOSURE_DOWN_FACTOR,
                        EXPOSURE_MIN_US, EXPOSURE_MAX_US)
            force_exposure(exp)
            settle(200)

    print("Locked exposure:", int(exp), "gain:", round(gain,1))
    return int(exp), float(gain)

# -------------------------------------------------
# Calibrated capture (for pipeline)
# -------------------------------------------------

def capture_and_save_grayscale(filename, framesize=None):
    """
    Calibrate, capture GRAYSCALE image at max resolution, and save to file.

    Args:
        filename: Path to save the image (.bin for raw grayscale)
        framesize: sensor framesize constant (default: sensor.WQXGA2 for 2592x1944)

    Returns:
        dict: Metadata with exposure_us, gain_db, width, height
    """
    # Default to FHD
    if framesize is None:
        framesize = sensor.FHD

    exp, gain = calibrate(verbose=True)

    print("Switching to GRAYSCALE capture mode...")
    sensor.set_pixformat(sensor.GRAYSCALE)

    # Step up through resolutions for stability (OV5640 quirk)
    print("Setting framesize (step-up)...")
    try:
        sensor.set_framesize(sensor.SXGA)  # 1280x1024 first
        settle(200)
        sensor.set_framesize(framesize)    # Then target resolution
    except Exception as e:
        print("Failed to set framesize: {}, trying fallback...".format(e))
        try:
            sensor.set_framesize(sensor.UXGA)  # Try 1600x1200
        except:
            sensor.set_framesize(sensor.VGA)   # Last resort

    sensor.set_auto_whitebal(False)
    force_exposure(exp)
    force_gain(gain)

    print("Settling...")
    settle(1000)  # Longer settle for high res

    # Capture image
    print("Capturing snapshot...")
    img = sensor.snapshot()
    w, h = img.width(), img.height()
    print("Captured: {}x{}".format(w, h))

    # Write raw bytes directly
    print("Writing to file...")
    pixels = bytes(img)
    with open(filename, "wb") as f:
        f.write(pixels)

    print("Saved {}x{} ({:.1f}MB)".format(w, h, len(pixels)/1024/1024))
    return {"exposure_us": exp, "gain_db": gain, "width": w, "height": h}

# -------------------------------------------------
# Final capture (standalone)
# -------------------------------------------------

def capture_final(exp, gain):
    print("Capturing final image…")

    sensor.set_pixformat(FINAL_PIXFORMAT)
    settle(300)

    sensor.set_framesize(sensor.SXGA)
    settle(300)
    sensor.set_framesize(FINAL_FRAMESIZE)
    settle(600)

    sensor.set_auto_whitebal(False)

    force_exposure(min(exp, FINAL_EXPOSURE_MAX_US))
    force_gain(gain)

    sensor.set_brightness(0)
    sensor.set_contrast(0)

    settle(800)

    img = sensor.snapshot()
    pixels = bytes(img)
    with open(OUT_PATH, "wb") as f:
        f.write(pixels)

    time.sleep_ms(800)
    img = None

    print("Saved:", OUT_PATH)

# Save to SD card for large files (internal flash ~2MB limit)
SD_ROOT = "/sdcard"
SNAPSHOT_FILE = SD_ROOT + "/snapshot.bmp"

# Resolution: Maximum for OV5640 on H7 Plus
# sensor.FHD = 1920x1080 (2.1MP)
# sensor.WQXGA2 = 2592x1944 (5MP) - MAXIMUM
# sensor.QXGA = 2048x1536 (3.1MP) - high res alternative
# sensor.UXGA = 1600x1200 (1.9MP) - safer high res
# sensor.SXGA = 1280x1024 (1.3MP) - reliable fallback
CAPTURE_FRAMESIZE = sensor.FHD
EXPECTED_WIDTH = 1920
EXPECTED_HEIGHT = 1080
EXPECTED_SIZE = EXPECTED_WIDTH * EXPECTED_HEIGHT


def get_file_size(filepath):
    """Get file size using os.stat (efficient, no file read)."""
    try:
        return os.stat(filepath)[6]  # st_size is index 6
    except OSError:
        return -1


def verify_sd_mounted():
    """Check if SD card is available."""
    try:
        os.listdir(SD_ROOT)
        return True
    except OSError:
        return False


def take_image():
    """
    Capture calibrated GRAYSCALE image at maximum resolution and save to SD card.

    Returns:
        tuple: (filename, width, height)

    Raises:
        RuntimeError: If SD card not mounted or save fails
    """
    # Verify SD card (required for 5MB files)
    if not verify_sd_mounted():
        raise SystemExit("ERROR: SD card not mounted at /sdcard. Insert SD card and restart.")

    filename = SNAPSHOT_FILE

    # Capture and save at maximum resolution (overwrites previous)
    meta = capture_and_save_grayscale(filename, framesize=CAPTURE_FRAMESIZE)

    # Verify file exists
    time.sleep_ms(200)  # Longer delay for large file
    size = get_file_size(filename)

    if size < 0:
        raise RuntimeError("File not found: {}".format(filename))

    width = meta.get("width", EXPECTED_WIDTH)
    height = meta.get("height", EXPECTED_HEIGHT)
    expected = width * height

    if size != expected:
        print("WARNING: Size {} != expected {}".format(size, expected))

    print("Captured {}x{} ({:.1f}MB)".format(width, height, size/1024/1024))
    print("Exposure: {} us, Gain: {} dB".format(meta["exposure_us"], meta["gain_db"]))
    return filename, width, height


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



def read_raw_pixel_data_from_bmp(img_path, Width, Height):
    """
    Reads a standard 8-bit grayscale BMP file, skips the header and padding.
    Critically, it reverses the row order (bottom-up) to correctly orient
    the image (top-down) for the OpenMV/MicroPython environment.

    Returns: bytearray of raw pixel data (top-down), or None on error.
    """
    try:
        with open(img_path, "rb") as f:
            # 1. Read the data offset (same as before)
            f.seek(10)
            data_offset_bytes = f.read(4)
            data_offset = struct.unpack('<I', data_offset_bytes)[0]

            # 2. Calculate row metrics
            row_padding = (4 - (Width % 4)) % 4
            row_size = Width + row_padding

            # The BMP pixel data starts at the data_offset.
            # We want to start seeking from the LAST row of the image data,
            # which is (data_offset + (Height - 1) * row_size)

            raw_data = bytearray()

            # 3. Iterate through rows in REVERSE (from top of the image buffer)
            for i in range(Height):
                # Calculate the starting position of the row we want to read
                # We start at the total image data end, and subtract the size of
                # all rows *above* the current one.
                current_row_start = data_offset + (Height - 1 - i) * row_size
                f.seek(current_row_start)

                # Read the actual pixel data for the row
                row_data = f.read(Width)

                # Append to raw_data. Because we are iterating from the bottom-most
                # row (which should be the top row of the output image) down to the
                # top-most row (which should be the bottom row of the output image),
                # the result is a correctly oriented image buffer.
                raw_data.extend(row_data)

            return raw_data

    # NOTE: Using the general 'Exception' or 'OSError' for file errors is still
    # necessary in MicroPython, but I'll use 'OSError' as it's typically
    # a better fit than 'Exception' for I/O problems when available.
    except OSError:
        print(f"Error: Image file '{img_path}' not found (OSError).")
        return None
    except Exception as e:
        print(f"Error reading BMP structure: {e}")
        return None


def process_image(img_path, coords, offset_y=0, sensor_type="VGA", logs=False):
    """
    Reads a BMP image file by segment (tile) to avoid memory allocation errors,
    correcting for BMP structure, padding, and vertical orientation.
    """
    try:
        # 1. Set image/tile dimensions
        if sensor_type == "QVGA":
            TILE_W = 160
            TILE_H = 120
            Width = 320
            Height = 240
        elif sensor_type == "VGA":  # VGA (default)
            TILE_W = 50
            TILE_H = 480
            Width = 640
            Height = 480
        elif sensor_type == "FHD":
            TILE_W = 200
            TILE_H = 1080
            Width = 1920
            Height = 1080
        elif sensor_type == "WQXGA2":
            TILE_W = 200
            TILE_H = 1944
            Width = 2592
            Height = 1944
        else:
            TILE_W = 200
            TILE_H = 480
            Width = 640
            Height = 480

        # Sort coordinates by X offset value
        sorted_data_list = sorted(
            coords.items(),
            key=lambda item: int(item[1]))

        print(f"Processing in order: {sorted_data_list}")

        results = {}

        with open(img_path, "rb") as img:
            # --- BMP HEADER CALCULATION ---
            # 2. Get the file offset to the start of pixel data
            img.seek(10)
            data_offset_bytes = img.read(4)
            data_offset = struct.unpack('<I', data_offset_bytes)[0]

            # 3. Calculate row metrics for seeking
            row_padding = (4 - (Width % 4)) % 4
            # Size of a row in the file (data + padding)
            file_row_size = Width + row_padding
            # --- END BMP HEADER CALCULATION ---

            for index, offset_str in sorted_data_list:
                tile_x_offset = int(offset_str.strip())
                print("offset", tile_x_offset)

                # Use a list to hold tile rows to allow reversing the order easily
                tile_rows = []

                # 4. Construct data array for image tile, reading row by row
                for i in range(TILE_H):
                    # i is the current row index of the TILE (0 to TILE_H-1)

                    # Calculate the Y-coordinate in the full LOGICAL (Top-Down) image
                    logical_y = i + offset_y

                    # Convert LOGICAL Y to FILE ROW INDEX (0 = file bottom, Height-1 = file top)
                    # This ensures we are always targeting the correct pixel content.
                    file_row_index = (Height - 1) - logical_y

                    if file_row_index < 0 or file_row_index >= Height:
                        # Skip if the logical tile row is outside the image bounds
                        row_data = b'\x00' * TILE_W  # Pad with black pixels
                    else:
                        # Calculate the start position in the file for this row:
                        # = (Data Start) + (Row Index * Row Size in File) + (X Offset)
                        file_start_pos = (
                            data_offset +
                            (file_row_index * file_row_size) +
                            tile_x_offset
                        )

                        # Move pointer and read the tile segment
                        img.seek(file_start_pos)
                        row_data = img.read(TILE_W)

                    # Store the row data for later reordering
                    tile_rows.append(row_data)

                # --- NEW LOGIC: Correct the vertical flip ---
                # BMP stores rows bottom-to-top. The loop above read them in the file's order,
                # meaning tile_rows[0] is the bottom row of the tile.
                # Reversing the list puts the visual top row first, correcting the orientation.
                tile_rows.reverse()
                data = bytearray().join(tile_rows)
                # --- END NEW LOGIC ---

                # 5. Process the Tile (Rest of the logic is retained)
                tile_img = image.Image(
                    TILE_W, TILE_H, sensor.GRAYSCALE, buffer=data, copy_to_fb=True)

                # Apply Gaussian blur for noise reduction and unsharp masking for edge enhancement
                #tile_img.gaussian(1, unsharp=True)

                # Detect segments and store results
                local_segments = detect_segments(tile_img)

                global_segments = []
                for segment in local_segments:
                    global_segment = segment.copy()

                    # Add the X-offset and Y-offset to the coordinates
                    global_segment["x1"] += tile_x_offset
                    global_segment["x2"] += tile_x_offset
                    global_segment["y1"] += offset_y
                    global_segment["y2"] += offset_y

                    global_segments.append(global_segment)

                results[tile_x_offset] = global_segments

        # 6. Logging (Optional)
        if logs:
            try:
                # Use the provided log function from utils
                log("logs.txt", message=results, function_name="process_image")
            except Exception as log_error:
                print(f"Logging failed: {log_error}")

        return results

    # Catching the most general file/system errors available in MicroPython
    except OSError:
        print(f"An error occurred: Image file '{
              img_path}' not found (OSError).")
        return None
    except Exception as e:
        # This catches memory allocation failures, struct errors, etc.
        print(f"An error occurred: {e}")
        return None

    # The detect_segments function remains unchanged.

# Line Segment Detection Function (Unchanged)


def detect_segments(img, length=30, min_degree=0, max_degree=180):
    """
    Detects line segments in a given image object and filters them based on length

    ... (Docstring details omitted) ...
    """
    segments = []

    # img.find_line_segments() returns 'line' objects
    for line in img.find_line_segments(merge_distance=10, max_theta_difference=30):

        # Filter based on length and angle (theta)
        if (line.length() > length) and (min_degree <= line.theta()) and (line.theta() <= max_degree):

            # Manually construct the dictionary from the line object's methods
            segment_dict = {
                "x1": line.x1(),
                "y1": line.y1(),
                "x2": line.x2(),
                "y2": line.y2(),
                "length": line.length(),
                "theta": line.theta(),  # Angle in degrees
                "rho": line.rho()       # Distance from origin in Hough space
            }

            segments.append(segment_dict)

    return segments


def extract_boundary_segments(filtered_segments_dict):
    """
    Identifies the top-most and bottom-most line segments and returns them
    in a list format compatible with the existing drawing function.

    Args:
        filtered_segments_dict: Dictionary {offset_x: [segment_list]}

    Returns:
        dict: A dictionary {offset_x: [top_segment, bottom_segment]}
    """
    boundary_results = {}

    for offset_x, segment_list in filtered_segments_dict.items():
        if not segment_list:
            continue

        # Find the segment with the lowest Y value (Top)
        top_segment = min(segment_list, key=lambda s: min(s['y1'], s['y2']))

        # Find the segment with the highest Y value (Bottom)
        bottom_segment = max(segment_list, key=lambda s: max(s['y1'], s['y2']))

        # We store them in a LIST so your drawing function can iterate through them
        boundary_results[offset_x] = [top_segment, bottom_segment]


    print(f"Extracted boundaries for {len(boundary_results)} groups.")
    return boundary_results

def calculate_boundary_difference(boundary_dict):
    """
    Calculates the vertical distance (height) between the top and bottom
    segments for each offset group.

    Args:
        boundary_dict: Dictionary {offset_x: [top_segment, bottom_segment]}

    Returns:
        dict: A dictionary {offset_x: vertical_difference_in_pixels}
    """
    differences = {}

    for offset_x, segments in boundary_dict.items():
        # Ensure we have both segments to compare
        if len(segments) < 2:
            continue

        top = segments[0]
        bottom = segments[1]

        # Calculate the average Y for the top line
        avg_y_top = (top['y1'] + top['y2']) / 2

        # Calculate the average Y for the bottom line
        avg_y_bottom = (bottom['y1'] + bottom['y2']) / 2

        # Difference (Bottom Y is higher than Top Y in image coordinates)
        height_diff = avg_y_bottom - avg_y_top

        differences[offset_x] = round(height_diff, 2)

    return differences
def get_box_reference_metrics(boundary_dict, left_key=200, right_key=1500):
    """
    Calculates the actual top boundary and height of the box in the current frame.
    """
    heights = []
    tops = []

    for key in [left_key, right_key]:
        if key in boundary_dict:
            top_seg, bottom_seg = boundary_dict[key]
            y_top = (top_seg['y1'] + top_seg['y2']) / 2
            y_bottom = (bottom_seg['y1'] + bottom_seg['y2']) / 2
            heights.append(y_bottom - y_top)
            tops.append(y_top)

    # Use averages to define the "Box" for this frame
    actual_height = sum(heights) / len(heights) if heights else 920
    actual_top = sum(tops) / len(tops) if tops else 0

    return actual_top, actual_height

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


def process_segments(segments_by_offset_x, fixed_offset_y):
    """
    Converts the dictionary of raw segment data (grouped by offset_x) into a flat
    list of dictionaries with global coordinates. This also prepares a 'segment_dict'
    key for easy reconstruction of the final output dictionary.

    Args:
        segments_by_offset_x: Dictionary where keys are 'Offset X' and values are
                                 lists of raw segment dictionaries (local coordinates).
        fixed_offset_y: A constant vertical offset applied to all Y coordinates.

    Return:
        list: List of dictionaries with global coordinates and metadata.
    """
    segments = []

    for current_offset_x, segment_list in segments_by_offset_x.items():
        for segment_data in segment_list:


            # Calculate Global Coordinates (used only for filtering)
            x1 = segment_data["x1"] + current_offset_x
            y1 = segment_data["y1"] + fixed_offset_y
            x2 = segment_data["x2"] + current_offset_x
            y2 = segment_data["y2"] + fixed_offset_y

            # Store the segment with its original data and global coordinates
            segments.append({
                'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                'theta': segment_data['theta'],
                'segment_dict': segment_data, # Store the original dictionary structure
                'original_offset_x': current_offset_x
            })

    return segments


def filter_duplicates(segments):
    """
    Removes line segments that are duplicates (have the same global endpoints).
    Creates a unique signature by sorting the endpoints.

    Args:
        segments: List of segment dictionaries with global coordinates.

    Returns:
        List: List of unique segment dictionaries.
    """
    unique = set()
    filtered_segments = []

    for seg in segments:
        # Create a unique tuple signature for the line, irrespective of endpoint order (x1,y1 vs x2,y2)
        sig = tuple(sorted([(seg['x1'], seg['y1']), (seg['x2'], seg['y2'])]))

        if sig not in unique:
            unique.add(sig)
            filtered_segments.append(seg)

    print(f"After Duplicates Filter: {len(filtered_segments)}")
    return filtered_segments

def filter_vertical_cutoff(segments):
    """
    Implements a Region of Interest (ROI) filter by finding the first vertical line
    and discarding all segments that appear ABOVE that line's minimum Y coordinate.

    Args:
        segments: List of segment dictionaries.
    Returns:
        List: List of segments remaining below the determined cutoff Y-coordinate.
    """

    # Sort segments top-to-bottom, left-to-right to find the highest cutoff line first
    segments.sort(key=lambda s: (
        s['original_offset_x'], min(s['y1'], s['y2'])))

    vertical_line_y_cutoff = None

    for seg in segments:
        theta = seg['theta']
        # Define vertical lines as having a theta near 0 or 180 degrees (0-10 or 170-180)
        is_vertical = (theta <= 10) or (theta >= 170)

        if is_vertical:
            # Found the vertical cutoff point (the highest point of the vertical line)
            vertical_line_y_cutoff = min(seg['y1'], seg['y2'])
            break

    if vertical_line_y_cutoff is not None:
        # Keep line segments that are at or below the vertical cutoff line
        filtered_segments = [seg for seg in segments
                             if min(seg['y1'], seg['y2']) >= vertical_line_y_cutoff]
        print(f"Vertical Cutoff Y found: {vertical_line_y_cutoff}")
        return filtered_segments

    print("Vertical Cutoff: No vertical line found, keeping all.")
    return segments

def filter_only_horizontal(segments):
    """
    Final filter to keep only lines with an angle (theta) close to 90 degrees.

    Args:
        segments: List of segment dictionaries.
    Returns:
        List: List of segment dictionaries where 80 <= theta <= 100.
    """

    # Horizontal lines are those with theta between 80 and 120 degrees
    filtered_segments = [seg for seg in segments
                         if 80 <= seg['theta'] <= 120]

    print(f"Final Horizontal Filtered Segments: {len(filtered_segments)}")
    return filtered_segments



def filter_line_segments(segment_data_dict, offset_y, logs = False):
    """
    Processes, filters, and groups line segment data, returning the result
    as a dictionary structured identically to the input.

    Args:
        segment_data_dict:: Dictionary of raw segment data grouped by offset_x.
        offset_y: The fixed vertical offset to apply during processing.
        logs: Boolean flag to enable logging of the filtered results.

    Returns:
        dict: A dictionary of filtered segment data grouped by offset_x, or None on failure.
    """

    # Process data and convert coordinates
    segments = process_segments(segment_data_dict, offset_y)

    print(f"Initial Segments: {len(segments)}")

    # 2. Apply Filters sequentially
    segments = filter_duplicates(segments)
    segments = filter_vertical_cutoff(segments)
    segments = filter_only_horizontal(segments)

    # 3. Re-group filtered lines into the target output structure (dictionary)
    # The output structure is {offset_x: [segment_dict, segment_dict, ...]}
    filtered_groups = {}

    for seg in segments:
        offset_x = seg['original_offset_x']

        if offset_x not in filtered_groups:
            filtered_groups[offset_x] = []

        # Append the original segment dictionary stored during processing
        filtered_groups[offset_x].append(seg['segment_dict'])

    print(f"Successfully processed and grouped filtered data.")

    if logs:
        try:
            log("logs.txt", message=filtered_groups, function_name="filter_line_segments")
        except Exception as log_error:
            print(f"Logging failed: {log_error}")

    # 4. Return the resulting dictionary
    return filtered_groups

# ----------------------END IGNORED FUNCTIONS-----------------------


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

