from utils import log
import math
import json
import image
import sensor
import time
from drawing import drawing
from gap import normalize_gaps, check_lines_in_file
from utils import log_data_to_file
from bmp_line_detection import process_image
from filter import filter_line_segments



def main():
    sensor.reset()
    sensor.set_pixformat(sensor.GRAYSCALE)
    sensor.set_framesize(sensor.FHD)
    sensor.skip_frames(time=2000)

    img_file = sensor.snapshot()

    coords = {"Left": "200", "Center": "800", "Right": "1500"}



    pre_process = process_image(img_file, coords=coords, offset_y=0,
                        sensor_type="FHD", logs=False)

    log_data_to_file(pre_process, filename='pre_process.json')


    filtered = filter_line_segments(pre_process, offset_y=0, logs=False)

    log_data_to_file(filtered, filename='filtered.json')

    gaps = normalize_gaps(filtered, max_gap=45, min_gap=25, segment_index=0)

    log_data_to_file(gaps, filename='gaps.json')
    results, arr = check_lines_in_file('gaps.json', 200, 800, fixed_height=10, width=50)

    time.sleep(1)
    print(results, arr)

main()
