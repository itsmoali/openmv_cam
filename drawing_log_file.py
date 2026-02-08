from drawing import drawing
import time, image

# File is to be mainly used for drawing the image based on the log files
# Choose which log file to use

log_file = "virtual_slots.json"
#log_file = "filtered.json"
#log_file = "right_gaps.json"
#log_file = "left_gaps.json"
#log_file = "boundaries.json"
output_img = 'output.bmp'
# Define image parameters
FRAME_HEIGHT = 1080
FRAME_WIDTH = 1920
Y_OFFSET = 0

new_img = drawing(
    data_filename=log_file,
    save_file=output_img,
    height=FRAME_HEIGHT,
    width=FRAME_WIDTH,
    offset_y=Y_OFFSET,
#    dic=True
    dic = False
)

image.Image(output_img, copy_to_fb=True)
time.sleep(1)
