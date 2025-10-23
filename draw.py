# Drawing lines inside the openmv camera - By: moali - Thu Oct 23 2025

import sensor
import time
import image
import json


def draw(txt_file, height=480, width=640, offset_y=0):
    img = image.Image(width, height, sensor.GRAYSCALE)

    current_offset_x = 0  # Initialize the X offset tracker

    try:
        with open(txt_file, 'r') as f:
            for line in f:
                # Extract offset value
                if line.startswith("Offset X: "):

                    try:
                        current_offset_x = int(
                            line.split("Offset X: ")[1].strip())
                        print(f"Tracking new X Offset: {current_offset_x}")
                    except ValueError:
                        print("Error parsing X Offset. Skipping line.")
                        continue

                # 2. Parse & draw lines
                else:

                    try:

                        segment_data = json.loads(line)

                        # 2. Extract Local Coordinates
                        x1_local = segment_data["x1"]
                        y1_local = segment_data["y1"]
                        x2_local = segment_data["x2"]
                        y2_local = segment_data["y2"]

                        # 3. Calculate Global Coordinates
                        # Global X = Local X (from tile) + Current X Offset
                        # Global Y = Local Y (from tile) + Fixed Y Offset

                        x1_global = x1_local + current_offset_x
                        y1_global = y1_local + offset_y
                        x2_global = x2_local + current_offset_x
                        y2_global = y2_local + offset_y
                        print(segment_data)

                        # 4. Draw everything
                        img.draw_line(x1_global, y1_global, x2_global, y1_global,
                                      color=(255, 255, 255), thickness=2)

                    except Exception as e:
                        print(f"Error parsing line segment: {
                              line.strip()}. Error: {e}")
        img.save("drawn_lines.bmp")
        print("Image saved")

    except FileNotFoundError:
        print(f"Error: Results file '{txt_file}' not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
