import sensor, image, time, json

#-------------------------------------
#USAGE
# Run 'calibrate()' to check the camera calibration. Encouraged to change
# calibration values to fit the setup.
# Comment out 'calibrate()' and uncomment 'save_image()' to save a calibration image.

def save_calibration_data(red, green, blue_start, blue_gap, filename="calib.json"):
    """
    Saves the calibration variables to a JSON file on the OpenMV disk.
    """
    data = {
        "red_line": red,
        "green_line": green,
        "start_blue_line": blue_start,
        "gap_blue_line": blue_gap
    }
    try:
        with open(filename, "w") as f:
            json.dump(data, f)
        print("Calibration saved to", filename)
    except Exception as e:
        print("Failed to save calibration:", e)

def save_image(img, prefix="calibration"):
    """
    Saves the given image as a BMP file with an auto-generated filename.
    """
    t = time.localtime()
    timestamp = "{:04d}{:02d}{:02d}_{:02d}{:02d}{:02d}".format(t[0], t[1], t[2], t[3], t[4], t[5])
    filename = "{}_{}.bmp".format(prefix, timestamp)

    #Save image
    img.save(filename, quality=100)
    print("Image saved as:", filename)

def draw_horizontal_lines(img, top_y, second_line_offset=100, color_top=(255,0,0), color_second=(0,255,0)):
    """
    Draws two horizontal lines on the image.
    The lines represent the vertical positioning for the
    area where the waffer carrier has small attachement holes.

    Parameters:
    - img: image object
    - top_y: y-coordinate of the top line
    - second_line_offset: vertical distance from top line for the second line
    - color_top: color for top line
    - color_second: color for bottom line
    """
    #Top line
    img.draw_line(0, top_y, img.width(), top_y, color=color_top)

    #Bottom line
    second_y = top_y + second_line_offset
    img.draw_line(0, second_y, img.width(), second_y, color=color_second)



def draw_slot_lines(img, start_y, num_lines=25, gap=20, color=(0,0,255)):
    """
    Draws the slot positioning lines on the image. These can be used as
    ROI references for slot detection.

    Parameters:
    - img: image object f
    - start_y: y-coordinate to start drawing the first line
    - num_lines: number of lines to draw
    - gap: vertical distance between lines
    - color: color of the lines
    """
    for i in range(num_lines):
        y = start_y + i * gap
        img.draw_line(0, y, img.width(), y, color=color)


def calibrate(top_y, second_line_offset, slot_y, slot_gap):
    """
    Runs a calibration loop that displays the camera feed with overlayed
    reference lines for calibration.
    Parameters:
    - top_y: y-coordinate of the top reference line
    - second_line_offset: vertical distance from top line for the second line
    - slot_y: y-coordinate to start drawing the first slot line
    - slot_gap: vertical distance between slot lines
    """
    while True:
        clock.tick()
        img = sensor.snapshot()
        # Apply lens correction
        # Can be adjusted to 1 if there is no distortion of straight lines.
        img.lens_corr(strength = 1.8)

        # Draw first two lines
        draw_horizontal_lines(img, top_y=red_line, second_line_offset=green_line)

        # Draw 24 slot positions
        draw_slot_lines(img, start_y=start_blue_line, num_lines=24, gap=gap_blue_line)
        #fps counter
        img.draw_string(10, 10, "FPS: {:.2f}".format(clock.fps()), color=(255,255,255))

# Initialize camera
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.FHD)
sensor.skip_frames(time = 2000)
clock = time.clock()

#ADJUST VALUES HERE
red_line = 100
green_line = 100
start_blue_line = 230
gap_blue_line = 30

#Run calibration to first check the camera angles
calibrate(top_y=red_line, second_line_offset=green_line, slot_y=start_blue_line, slot_gap=gap_blue_line)
# To save an image, uncomment the following lines:
#save_image(sensor.snapshot(), prefix="calibration")
#save_calibration_data(red_line, green_line, start_blue_line, gap_blue_line, filename="calib.json")
