"""
CAMERA TEST SCRIPT: LIVE REGION-OF-INTEREST VISUALIZATION 📸

This module initializes the camera for continuous 
grayscale image capture at VGA resolution (640x480).

The primary purpose is to visually test and confirm specific X-coordinates on 
the camera feed by drawing persistent vertical white lines, which helps in defining 
and verifying Regions of Interest (ROIs) for subsequent image processing.
"""
import sensor
import image
import time
import os


# A method to test camera and draw lines at specified coordinates

# --- Camera Initialization ---
# Configures the camera sensor for basic operation.
sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE) # Set to grayscale (1 byte per pixel).
sensor.set_framesize(sensor.VGA)      # Set resolution to VGA (640x480).
sensor.skip_frames(time = 2000)       # Wait 2 seconds for the camera to auto-gain/auto-exposure stabilize.


# --- Main Loop Setup ---
clock = time.clock()

def test_camera(coords):
    """
    Captures a single frame from the camera and draws three vertical 
    white lines on the image at specified X-coordinates.

    This function is intended to be called inside a continuous loop for live 
    visualization of fixed vertical ROIs on the camera feed.

    Args:
        coords (list/tuple): A sequence containing exactly three integer 
                             X-coordinates (w1, w2, w3) where the vertical 
                             lines should be drawn. These values must be within 
                             the image width range (0 to 639 for VGA).
                             
    Result:
        None: The function modifies the image buffer in memory (sensor.snapshot()), 
              making the result visible via the frame buffer or ready for further 
              processing/display.
    """
    # Use a try-except block for robust coordinate unpacking
    try:
        w1, w2, w3 = coords
    except (ValueError, TypeError):
        print("Error: 'coords' must be a sequence of exactly three integers.")
        return

    print("Width Coordinates:", w1, w2, w3)
    
    # Tick the clock to track and display frame rate in the console
    clock.tick() 
    
    # Capture image
    img = sensor.snapshot()
    
    # Color for lines
    color = (255, 255, 255) 
    
    # Draw Vertical Lines
    img.draw_line(w1, 0, w1, img.height(), color=color)
    img.draw_line(w2, 0, w2, img.height(), color=color)
    img.draw_line(w3, 0, w3, img.height(), color=color)


# --- Main Execution Loop ---
while(True):
    # Change coordinates here to test different line positions
    test_camera([50, 300, 550])
