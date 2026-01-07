import image
import json

import sensor
import time

def drawing(data_filename, save_file, height=480, width=640, offset_y=0, dic=False):
    """
    Draws lines from a dictionary, loaded from a JSON file, onto a new image buffer.

    Args:
        data_filename (str): The path to the JSON file containing the line data.
        save_file (str): The filename/path to save the output image to (e.g., "output.png").
        height (int): The height of the new image frame to create.
        width (int): The width of the new image frame to create.
        offset_y (int): A vertical offset to shift all drawn lines on the y-axis.

    Returns:
        image.Image: The newly created image object with the lines drawn on it.
    """

    # 1. LOAD DATA FROM JSON FILE
    try:
        # Open the file in read mode
        with open(data_filename, 'r') as f:
            img_data = json.load(f)
        print(f"Successfully loaded line data from {data_filename}")
    except FileNotFoundError:
        print(f"Error: Data file not found at {data_filename}")
        # Create a blank image to return on failure
        img = image.Image(width, height, sensor.GRAYSCALE)

        return img
    except Exception as e:
        print(f"Error loading JSON data: {e}")
        # Create a blank image to return on failure
        img = image.Image(width, height, sensor.GRAYSCALE)
        return img

    # 2. INITIALIZE IMAGE BUFFER
    # Create a new image object (width, height, pixformat).
    img = image.Image(width, height, sensor.GRAYSCALE)

    # Clear the screen to a blank gray color

    line_count = 0

    # 3. DRAW LINES
    # Iterate through the line categories (keys like "550", "50", "350")
    for category, lines in img_data.items():

        category = int(category)  # Convert category key to integer for coordinate offset
        if category:
            print(f"Processing Category: {category}")

            # Iterate through each individual line object
            for line in lines:
                try:
                    if dic:
                        line = json.loads(line)
                    # Extract coordinates and apply the vertical offset
                    x1 = line['x1'] #+ (category//2)
                    y1 = line['y1'] + offset_y
                    x2 = line['x2'] #+ (category//2)
                    y2 = line['y2'] + offset_y

                    # Draw the line on the image object in white, 2 pixels thick
                    print(x1)
                    img.draw_line(x1, y1, x2, y2, (255,255,255), 2)
                    line_count += 1
                except KeyError as e:
                    # Log error if a line object is malformed
                    print(f"Error: Line object is missing required key: {e} - Skipping line.")
                except Exception as e:
                    # Log other drawing errors
                    print(f"Error drawing line: {e} - Skipping line.")

    # Optionally draw the total count for verification
    print(f"Total lines drawn in this frame: {line_count}")

    # 4. SAVE IMAGE
    try:
        # Save the drawn image to the specified file
        img.save(save_file)
        print(f"Image saved to {save_file}")
    except Exception as e:
        print(f"Error saving image to {save_file}: {e}")

    # Return the drawn image
    return img

#log_file = "process_img.json"
#log_file = "filtered.json"
#log_file = "gaps.json"
#output_img = 'output.bmp'
# Define image parameters
#FRAME_HEIGHT = 1080
#FRAME_WIDTH = 1920
#Y_OFFSET = 0

#new_img = drawing(
#    data_filename=log_file,
#    save_file=output_img,
#    height=FRAME_HEIGHT,
#    width=FRAME_WIDTH,
#    offset_y=Y_OFFSET,
#    dic=True
#    dic = False
#)
#time.sleep(1)


#img = image.Image(output_img, copy_to_fb=True)
#time.sleep(1)
