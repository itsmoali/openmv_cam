import sensor
import image
import time
import os



# A method to test camera and draw lines at specified coordinates

# --- Camera Initialization ---
sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.VGA)
sensor.skip_frames(time = 2000)


# --- Main Loop ---
clock = time.clock()
def test_camera(coords):

    w1, w2, w3 = coords
    print("Width Coordinates:", w1, w2, w3)
    clock.tick()
    img = sensor.snapshot()
    color = (255,255,255)
    img.draw_line(w1, 0, w1, img.height(), color= color)
    img.draw_line(w2, 0, w2, img.height(), color=color)
    img.draw_line(w3, 0, w3, img.height(), color= color)




while(True):
# Change coordinates here to test different line positions
    test_camera([50,300,550])

