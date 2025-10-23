# Image taking Interface - By: moali - Thu Oct 23 2025

import sensor
import time

sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.VGA)
sensor.skip_frames(time=2000)


# Takes the image and saves it with a timestamped filename
def take_image():
    img = sensor.snapshot()
    timestamp = time.ticks_ms()
    filename = "IMG/snapshot_{}.bin".format(timestamp)
    img.save(filename)
    print("Image saved as:", filename)

    return filename



