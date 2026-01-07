import image
import sensor
import time

import struct
from utils import log_data_to_file, log


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
                    TILE_W, TILE_H, sensor.GRAYSCALE, buffer=data, copy_to_fb=False)

                # Apply Gaussian blur for noise reduction and unsharp masking for edge enhancement
                tile_img.gaussian(2, unsharp=True)

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


def detect_segments(img, length=15, min_degree=0, max_degree=180):
    """
    Detects line segments in a given image object and filters them based on length

    ... (Docstring details omitted) ...
    """
    segments = []

    # img.find_line_segments() returns 'line' objects
    for line in img.find_line_segments(merge_distance=5, max_theta_difference=40):

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


# log_file = "process_img.json"
# output_img = 'output.bmp'
# img_file = "IMG/21.bmp"
# img_file = "testing_bbC.bmp"
# img_file = "snapshot_3762176.bin"
# img = image.Image(img_file, copy_to_fb = True)


coords = {"Left": "50", "Center": "300", "Right": "500"}

# res = process_image(img_file, coords=coords, offset_y=0, sensor_type="VGA", logs= False)
# print(res)
# log_data_to_file(res, log_file)
