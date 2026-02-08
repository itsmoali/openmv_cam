"""
OV5640 exposure calibration + calibrated capture.

Used by the pipeline for calibrated grayscale binary capture.
Only calls sensor.reset() when run as a script.
"""

import sensor
import time
import os

# -------------------------------------------------
# SD mount (your firmware uses /sdcard)
# -------------------------------------------------
SD_ROOT = "/sdcard"

# -------------------------------------------------
# Configuration
# -------------------------------------------------

# Metering (fast, safe)
METER_FRAMESIZE = sensor.QVGA
METER_PIXFORMAT = sensor.RGB565

# Final capture
FINAL_FRAMESIZE = sensor.FHD
FINAL_PIXFORMAT = sensor.GRAYSCALE

# Exposure / gain limits
EXPOSURE_MIN_US = 2000
EXPOSURE_MAX_US = 600000
FINAL_EXPOSURE_MAX_US = 400000

GAIN_MIN_DB = 0
GAIN_MAX_DB = 24

# Histogram targets (8-bit luminance)
TARGET_Q10 = 40
TARGET_Q50 = 120
TARGET_Q95 = 245

MAX_CLIP_LO = 0.01
MAX_CLIP_HI = 0.004

# Iteration control
MAX_ITERS = 8
EXPOSURE_UP_FACTOR = 1.5
EXPOSURE_DOWN_FACTOR = 0.85

# Histogram sampling
SAMPLE_STEP = 4

# Output (raw grayscale bytes)
OUT_PATH = SD_ROOT + "/final.bmp"

# -------------------------------------------------
# Helpers
# -------------------------------------------------

def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x

def settle(ms):
    sensor.skip_frames(time=ms)

def force_exposure(us):
    sensor.set_auto_exposure(False)
    sensor.set_auto_exposure(False, exposure_us=int(us))

def force_gain(db):
    sensor.set_auto_gain(False)
    sensor.set_auto_gain(False, gain_db=float(db))

# -------------------------------------------------
# RGB -> luminance
# -------------------------------------------------

def rgb_to_luma(px):
    if isinstance(px, tuple):
        r, g, b = px
    else:
        r5 = (px >> 11) & 0x1F
        g6 = (px >> 5)  & 0x3F
        b5 = px & 0x1F
        r = (r5 * 255) // 31
        g = (g6 * 255) // 63
        b = (b5 * 255) // 31
    return (77*r + 150*g + 29*b) >> 8

# -------------------------------------------------
# Histogram utilities
# -------------------------------------------------

def histogram_from_image(img):
    w, h = img.width(), img.height()
    bins = [0] * 256
    total = 0
    for y in range(0, h, SAMPLE_STEP):
        for x in range(0, w, SAMPLE_STEP):
            y8 = rgb_to_luma(img.get_pixel(x, y))
            bins[y8] += 1
            total += 1
    return bins, total


def quantile(bins, total, q):
    if total == 0:
        return 0
    tgt = total * q
    acc = 0
    for i, c in enumerate(bins):
        acc += c
        if acc >= tgt:
            return i
    return 255


def clip_fractions(bins, total):
    lo = sum(bins[0:6]) / total if total else 0
    hi = sum(bins[250:256]) / total if total else 0
    return lo, hi

# -------------------------------------------------
# Exposure calibration
# -------------------------------------------------

def calibrate(verbose=True):
    print("Calibrating exposure…")

    sensor.set_pixformat(METER_PIXFORMAT)
    sensor.set_framesize(METER_FRAMESIZE)
    sensor.set_auto_whitebal(False)

    # Start from auto baseline
    sensor.set_auto_exposure(True)
    sensor.set_auto_gain(True)
    settle(800)

    try:
        exp = sensor.get_exposure_us()
    except:
        exp = 20000
    try:
        gain = sensor.get_gain_db()
    except:
        gain = 6.0

    sensor.set_auto_exposure(False)
    sensor.set_auto_gain(False)

    force_exposure(exp)
    force_gain(gain)
    settle(200)

    for i in range(MAX_ITERS):
        img = sensor.snapshot()
        bins, total = histogram_from_image(img)

        q10 = quantile(bins, total, 0.10)
        q50 = quantile(bins, total, 0.50)
        q95 = quantile(bins, total, 0.95)
        clip_lo, clip_hi = clip_fractions(bins, total)

        if verbose:
            print(
                "iter", i,
                "exp", int(exp),
                "gain", round(gain,1),
                "q10", q10,
                "q50", q50,
                "q95", q95,
                "clip_lo", round(clip_lo,3),
                "clip_hi", round(clip_hi,3)
            )

        shadows_ok = (q10 >= TARGET_Q10) and (clip_lo <= MAX_CLIP_LO)
        mids_ok    = abs(q50 - TARGET_Q50) <= 20
        highs_ok   = (q95 <= TARGET_Q95) and (clip_hi <= MAX_CLIP_HI)

        if shadows_ok and mids_ok and highs_ok:
            break

        # Lift shadows / mids
        if (not shadows_ok) or (q50 < TARGET_Q50):
            if exp < EXPOSURE_MAX_US:
                exp = clamp(exp * EXPOSURE_UP_FACTOR,
                            EXPOSURE_MIN_US, EXPOSURE_MAX_US)
                force_exposure(exp)
                settle(200)
                continue
            elif gain < GAIN_MAX_DB:
                gain = clamp(gain + 2.0, GAIN_MIN_DB, GAIN_MAX_DB)
                force_gain(gain)
                settle(200)
                continue

        # Pull back highlights if mass-clipping
        if not highs_ok:
            exp = clamp(exp * EXPOSURE_DOWN_FACTOR,
                        EXPOSURE_MIN_US, EXPOSURE_MAX_US)
            force_exposure(exp)
            settle(200)

    print("Locked exposure:", int(exp), "gain:", round(gain,1))
    return int(exp), float(gain)

# -------------------------------------------------
# Calibrated capture (for pipeline)
# -------------------------------------------------

def capture_and_save_grayscale(filename, framesize=None):
    """
    Calibrate, capture GRAYSCALE image at max resolution, and save to file.

    Args:
        filename: Path to save the image (.bin for raw grayscale)
        framesize: sensor framesize constant (default: sensor.WQXGA2 for 2592x1944)

    Returns:
        dict: Metadata with exposure_us, gain_db, width, height
    """
    # Default to maximum resolution for OV5640
    if framesize is None:
        framesize = sensor.WQXGA2  # 2592x1944 (5MP)

    exp, gain = calibrate(verbose=True)

    print("Switching to GRAYSCALE capture mode...")
    sensor.set_pixformat(sensor.GRAYSCALE)

    # Step up through resolutions for stability (OV5640 quirk)
    print("Setting framesize (step-up)...")
    try:
        sensor.set_framesize(sensor.SXGA)  # 1280x1024 first
        settle(200)
        sensor.set_framesize(framesize)    # Then target resolution
    except Exception as e:
        print("Failed to set framesize: {}, trying fallback...".format(e))
        try:
            sensor.set_framesize(sensor.UXGA)  # Try 1600x1200
        except:
            sensor.set_framesize(sensor.VGA)   # Last resort

    sensor.set_auto_whitebal(False)
    force_exposure(exp)
    force_gain(gain)

    print("Settling...")
    settle(1000)  # Longer settle for high res

    # Capture image
    print("Capturing snapshot...")
    img = sensor.snapshot()
    w, h = img.width(), img.height()
    print("Captured: {}x{}".format(w, h))

    # Write raw bytes directly
    print("Writing to file...")
    pixels = bytes(img)
    with open(filename, "wb") as f:
        f.write(pixels)

    print("Saved {}x{} ({:.1f}MB)".format(w, h, len(pixels)/1024/1024))
    return {"exposure_us": exp, "gain_db": gain, "width": w, "height": h}

# -------------------------------------------------
# Final capture (standalone)
# -------------------------------------------------

def capture_final(exp, gain):
    print("Capturing final image…")

    sensor.set_pixformat(FINAL_PIXFORMAT)
    settle(300)

    sensor.set_framesize(sensor.SXGA)
    settle(300)
    sensor.set_framesize(FINAL_FRAMESIZE)
    settle(600)

    sensor.set_auto_whitebal(False)

    force_exposure(min(exp, FINAL_EXPOSURE_MAX_US))
    force_gain(gain)

    sensor.set_brightness(0)
    sensor.set_contrast(0)

    settle(800)

    img = sensor.snapshot()
    pixels = bytes(img)
    with open(OUT_PATH, "wb") as f:
        f.write(pixels)

    time.sleep_ms(800)
    img = None

    print("Saved:", OUT_PATH)


def main():
    # Confirm SD is present
    if "sdcard" not in os.listdir("/"):
        raise OSError("SD card not mounted at /sdcard")

    sensor.reset()

    exp, gain = calibrate(verbose=True)
    capture_final(exp, gain)

    print("Done.")


if __name__ == "__main__":
    main()
