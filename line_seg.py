# Line Detection and Line Segment Detection on binary images stored as .bin files

import sensor
import time
import image
import os
import math


Height = 480
Width = 640

TILE_H = 480
TILE_W = 50


min_degree = 0
max_degree = 180


def process_image(img, offset_x, offset_y):

    try:
        img_bin = open(img, "rb")
        img_processed = str(img).replace(".bin", "_processed.txt")
        txt_file = open(img_processed, "w")
        if not img_bin:
            print("Error: Could not open image file.")
            return
        # Start the search in the image binary

        for offset in offset_x:
            txt_file.write("Offset X: " + str(offset) + "\n")
            print(offset)
            start = (offset_y * Width + offset)
            img_bin.seek(start)

            data = bytearray()

            # construct data array for image tile
            for i in range(TILE_H):
                row = img_bin.read(TILE_W)
                data.extend(row)
                img_bin.seek(Width - TILE_W, 1)
            tile_img = image.Image(
                TILE_W, TILE_H, sensor.GRAYSCALE, buffer=data, copy_to_fb=True)
            tile_img.gaussian(2, unsharp=True)
            detect_segments(tile_img, txt_file)

        img_bin.close()
        txt_file.close()
        return img_processed
    except Exception as e:
        print(f"An error occurred: {e}")


def detect_segments(img, txt_file):
    for line in img.find_line_segments(merge_distance=5, max_theta_difference=40):
        if (line.length() > 15) and (min_degree <= line.theta()) and (line.theta() <= max_degree):
            txt_file.write(str(line) + "\n")
    print("Processing Done")
