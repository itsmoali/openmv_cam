from conf_loader import load_config
from take_img import take_image
from line_seg import process_image
from filter import filter_line_segments
from draw import draw
from line_gap import normalize_segment_by_index


# Load ROI configurations
config = load_config("env.txt")

# Take the Image
# --------------------UNCOMMENT THE LINE BELOW TO TAKE AN IMAGE------------------
# img_path = take_image()
# THIS IS A DUMMY IMAGE
image_path = "IMG_2796.bin"

# Process the image with loaded ROI configurations
processed_file = process_image(image_path, [50, 300, 550], 0)

# Filter the line segments
# Following filters used
#   1. Duplicates Filter
#   2. Angle Filter (Removed vertical lines)
#   3. Horizontal Filter (Keeps only horizontal lines)
output_file = filter_line_segments(processed_file, 0)


final_segments_left_side = normalize_segment_by_index(output_file, max_gap=25, min_gap=10, segment_index=0)


# Draw the final filtered lines
# ---- Use the following uncommented lines in a different file, to see visualizations (RAM exceeds) ----
#draw(output_file, height=420, width=620, offset_y=0)
#img = image.Image("drawn_lines.bmp", copy_to_fb = True)



