import os
import time
import image
import sensor
import json  # Required for saving structured data
from log_utils import load_env
from draw import drawing


def save_results_to_file(results_data, filename="detection_results.txt"):
    """
    Serializes the final results dictionary to a text file using JSON.

    :param results_data: The dictionary containing all detected line segments.
    :param filename: The name of the file to save the data to.
    """
    try:
        # 1. Serialize the dictionary to a JSON string
        # The indent=4 argument makes the file human-readable
        json_string = json.dumps(results_data)

        # 2. Write the JSON string to the specified file
        with open(filename, 'a') as f:
            f.write(json_string)

        print(f"\n[SUCCESS] Final results saved to: {filename}")
        f.close()

    except Exception as e:
        print(f"[ERROR] Could not save final results to file: {e}")


def process_image(img, coords, offset_y=0, sensor_type="VGA"):
    # ... [rest of the process_image function remains the same] ...

    try:
        # Open image file in binary read mode
        # NOTE: This part assumes OpenMV or a similar environment where
        # 'open' correctly handles file descriptors and memory.
        img = open(img, "rb")
        if not img:
            raise FileNotFoundError("Image file not found.")

        # 1. Sort coordinates by value (offset)
        sorted_data_list = sorted(
            coords.items(),
            key=lambda item: int(item[1].strip())
        )
        sorted_data_dict = dict(sorted_data_list)
        print(f"Processing in order: {sorted_data_dict}")

        # 2. Set image/tile dimensions based on sensor type
        if sensor_type == "QVGA":
            TILE_W = 160
            TILE_H = 120
            Width = 320
            Height = 240
        else:  # VGA
            TILE_W = 50
            TILE_H = 480
            Width = 640
            Height = 480

        results = {}
        for index, offset_str in sorted_data_dict.items():
            offset = int(offset_str.strip())

            # Calculate file pointer start position (Y-offset * width + X-offset)
            start = (offset_y * Width + offset)
            img.seek(start)

            data = bytearray()

            # Construct data array for image tile
            for i in range(TILE_H):
                row = img.read(TILE_W)
                data.extend(row)
                # Skip the remaining part of the row we aren't reading (Width - TILE_W)
                img.seek(Width - TILE_W, 1)

            # Create image object for the tile
            tile_img = image.Image(
                TILE_W, TILE_H, sensor.GRAYSCALE, buffer=data, copy_to_fb=True)
            tile_img.gaussian(2, unsharp=True)

            # Store results using the offset as the key
            results[offset] = detect_segments(tile_img, logs=True)

        img.close()

        return results

    except Exception as e:
        print(f"An error occurred: {e}")


def detect_segments(img, min_degree=0, max_degree=180, logs=True):
    segments = []
    # img.find_line_segments() returns 'line' objects
    for line in img.find_line_segments(merge_distance=5, max_theta_difference=40):
        # 1. Apply your filtering logic
        if (line.length() > 15) and (min_degree <= line.theta()) and (line.theta() <= max_degree):

            # 2. FIX: Manually construct the dictionary from the line object's methods
            segment_dict = {
                "x1": line.x1(),
                "y1": line.y1(),
                "x2": line.x2(),
                "y2": line.y2(),
                "length": line.length(),
                "theta": line.theta(),
                "rho": line.rho()
                # You can add other attributes if needed, like magnitude()
            }

            # 3. Append the valid dictionary to the list
            segments.append(segment_dict)

    return segments

# Example

#img_file = "IMG_2796.bin"
#coords = load_env("env.txt")

# 1. Process the image and detect segments
#res = process_image(img_file, coords=coords, offset_y=0, sensor_type="VGA")

# 2. Draw the results onto a new image (using the imported function)
#save_results_to_file(res)
