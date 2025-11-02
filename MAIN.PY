from log_utils import load_env
from take_img import take_image
from line_seg import process_image
from filter import filter_line_segments
from draw import drawing
from line_gap import normalize_segment_by_index
from intersection import check_lines_in_file

# Load ROI configurations
config = load_env("env.txt")

# Take the Image
# --------------------UNCOMMENT THE LINE BELOW TO TAKE AN IMAGE------------------
# img_path = take_image()
# THIS IS A DUMMY IMAGE
image_path = "IMG_2796.bin"

# Process the image with loaded ROI configurations
processed_file = process_image(image_path, [30, 300, 550], 0)

# Filter the line segments
# Following filters used
#   1. Duplicates Filter
#   2. Angle Filter (Removed vertical lines)
#   3. Horizontal Filter (Keeps only horizontal lines)
output_file = filter_line_segments(processed_file, 0)

# Normalize line segments based on gaps for left and right segments
#NOTE: Currently hard-coded for left and right segments, change later
final_segments_left = normalize_segment_by_index(output_file, max_gap=25, min_gap=10, segment_index=0)
final_segments_right = normalize_segment_by_index(output_file, max_gap=25, min_gap=10, segment_index=2)

# Prints the index of the bounding box which has lines intersecting with it
# The 30 & 300 parameters corresponds to the offsets used during image processing
# Currently they are hard-coded, but would be changed later
print("Waffer positions found using the Left segments:\n")
left_results = check_lines_in_file(final_segments_left, 30, 300, fixed_height=3)

print("Waffer positions found using the Right segments:\n")
right_results = check_lines_in_file(final_segments_right, 550, 300, fixed_height=3)
print("Total number of Waffers found: ", max(left_results, right_results))


# Draw the final filtered lines
# ---- Use the following uncommented lines in a different file, to see visualizations (RAM exceeds) ----
#draw(output_file, height=400, width=620, offset_y=0)




