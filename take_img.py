# take_img.py
# Image capture library (NO sensor.reset(), NO __main__)

import sensor
import time
import os
from exposure_calibration import capture_and_save_grayscale

# Save to SD card for large files (internal flash ~2MB limit)
SD_ROOT = "/sdcard"
SNAPSHOT_FILE = SD_ROOT + "/snapshot.bmp"

# Resolution: Maximum for OV5640 on H7 Plus
# sensor.FHD = 1920x1080 (2.1MP)
# sensor.WQXGA2 = 2592x1944 (5MP) - MAXIMUM
# sensor.QXGA = 2048x1536 (3.1MP) - high res alternative
# sensor.UXGA = 1600x1200 (1.9MP) - safer high res
# sensor.SXGA = 1280x1024 (1.3MP) - reliable fallback
CAPTURE_FRAMESIZE = sensor.FHD
EXPECTED_WIDTH = 1920
EXPECTED_HEIGHT = 1080
EXPECTED_SIZE = EXPECTED_WIDTH * EXPECTED_HEIGHT


def get_file_size(filepath):
    """Get file size using os.stat (efficient, no file read)."""
    try:
        return os.stat(filepath)[6]  # st_size is index 6
    except OSError:
        return -1


def verify_sd_mounted():
    """Check if SD card is available."""
    try:
        os.listdir(SD_ROOT)
        return True
    except OSError:
        return False


def take_image():
    """
    Capture calibrated GRAYSCALE image at maximum resolution and save to SD card.

    Returns:
        tuple: (filename, width, height)

    Raises:
        RuntimeError: If SD card not mounted or save fails
    """
    # Verify SD card (required for 5MB files)
    if not verify_sd_mounted():
        raise SystemExit("ERROR: SD card not mounted at /sdcard. Insert SD card and restart.")

    filename = SNAPSHOT_FILE

    # Capture and save at maximum resolution (overwrites previous)
    meta = capture_and_save_grayscale(filename, framesize=CAPTURE_FRAMESIZE)

    # Verify file exists
    time.sleep_ms(200)  # Longer delay for large file
    size = get_file_size(filename)

    if size < 0:
        raise RuntimeError("File not found: {}".format(filename))

    width = meta.get("width", EXPECTED_WIDTH)
    height = meta.get("height", EXPECTED_HEIGHT)
    expected = width * height

    if size != expected:
        print("WARNING: Size {} != expected {}".format(size, expected))

    print("Captured {}x{} ({:.1f}MB)".format(width, height, size/1024/1024))
    print("Exposure: {} us, Gain: {} dB".format(meta["exposure_us"], meta["gain_db"]))
    return filename, width, height
