import sensor
import time
import image
import json
import os 


# Used to draw line segments from a dictionary-based dataset
def drawing(img_data, height=480, width=640, offset_y=0):
    """
    Draws line segments from a dictionary-based dataset onto a new OpenMV image.
    
    """
    # 1. Initialize the image (Creates a black canvas in GRAYSCALE)
    img = image.Image(width, height, sensor.GRAYSCALE)

    try:
        # Loop over the dictionary items to get the offset and the line data list
        # Sorting ensures the tiles are drawn in order
        sorted_img_data = sorted(img_data.items(), key=lambda item: int(item[0])) # Ensure key is treated as int for sorting

        for offset_x_str, line_segment_list in sorted_img_data:
            # We must convert the key (offset_x) back to an integer
            offset_x = int(offset_x_str)

            # Print the offset for debugging
            print(f"Drawing lines with global offset_x: {offset_x}")

            # Loop over the list of line segment dictionaries
            for segment_data in line_segment_list:
                # 2. Extract Local Coordinates
                x1_local = segment_data["x1"]
                y1_local = segment_data["y1"]
                x2_local = segment_data["x2"]
                y2_local = segment_data["y2"]

                # 3. Calculate Global Coordinates
                x1_global = x1_local + offset_x
                y1_global = y1_local + offset_y
                x2_global = x2_local + offset_x
                y2_global = y2_local + offset_y

                # 4. Draw everything
                img.draw_line(int(x1_global), int(y1_global), int(x2_global), int(y2_global),
                              color=(255, 255, 255), thickness=2)

        img.save("reconstructed_lines.bmp")
        print("Image saved as reconstructed_lines.bmp")

    except Exception as e:
        # Check for potential errors like keys being strings instead of ints
        print(f"Error drawing lines: {e}")

    return img

# --- LOAD JSON DATA ---

def load_json_results(filename):
    """
    Reads a JSON file and returns the Python dictionary data.

    :param filename: The path to the JSON file.
    :return: The dictionary containing the line segments data.
    """


    try:
        with open(filename, 'r') as f:
            # json.load reads the entire JSON document from the file object
            data = json.load(f)

            # The keys of a JSON object (dictionary) are always strings.
            # Convert keys back to integers for drawing logic to work correctly.
            int_keyed_data = {int(k): v for k, v in data.items()}

            return int_keyed_data

    except Exception as e:
        print(f"[ERROR] Failed to load or parse JSON file {filename}: {e}")
        return None

# --- Execution ---

JSON_FILE = "final_segment_data.json" 
IMAGE_HEIGHT = 480
IMAGE_WIDTH = 640

# 1. Load the data from the JSON file
line_data = load_json_results(JSON_FILE)

if line_data:
    print(f"\n[INFO] Successfully loaded {len(line_data)} tiles from JSON.")

    # 2. Use the existing drawing function to plot the lines
    reconstructed_image = drawing(line_data,
                                  height=IMAGE_HEIGHT,
                                  width=IMAGE_WIDTH,
                                  offset_y=0)
else:
    print("\n[INFO] Could not proceed with drawing as data failed to load.")
