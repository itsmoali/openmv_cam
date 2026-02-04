# Line Detection MVP for Wafer Cassette Holder
This repository contains the MVP implementation for detecting and normalizing lines on a wafer cassette holder image.

## Getting Started
The pipeline runs end-to-end from calibrated capture through line detection with a single entry point:

`main.py`

## Exposure Calibration and Capture
Exposure calibration is a required pre-step before any image is sent through the line detection pipeline. The calibration routine measures scene brightness on a low-resolution preview frame, locks exposure and gain, then switches to full-resolution grayscale capture. This keeps the capture consistent while minimizing clipping and shadow loss.

Integration path:

`main.py` → `take_img.py` → `exposure_calibration.py`

`exposure_calibration.py` performs:
1) Auto-baseline measurement (short metering phase)  
2) Iterative exposure/gain tuning using histogram targets  
3) Locking exposure/gain and capturing a full-resolution grayscale frame  
4) Writing raw bytes to a `.bin` file

The capture output is a raw grayscale binary file (default: `/sdcard/snapshot.bin`). The downstream pipeline assumes this binary format and will not work with JPEG output.

## Configuration
Region of Interest (ROI) parameters live in `env.txt`. Update those values to adjust the processing windows.

## Results and Visualization
Pipeline outputs include raw coordinates and filtered line segments (for example: `IMG_XXXX_gaps.txt`).

For visualization, see the final section of `main.py`. That section contains the drawing logic you can tweak.

## Current Implementation Notes
The pipeline currently processes grayscale images only, so the final detected lines are not overlaid on the original RGB image. If overlay visualization is needed, we can load the RGB frame alongside the grayscale capture or adjust the processing flow.
