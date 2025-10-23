# Line Detection MVP for Wafer Cassette Holder 📏
This repository contains the Minimum Viable Product (MVP) implementation for the line detection model designed specifically for identifying and normalizing lines on a wafer cassette holder image.

***

## 🚀 Getting Started
The pipeline is set up to run all necessary steps—from image loading and processing to final line segment filtering and normalization—with a single command.

To execute the entire pipeline, simply run the main script:

python MAIN.py

***
## ⚙️ Configuration
Region of Interest (ROI) Parameters
To define or adjust the areas of the image the model processes, modify the env.txt file.

Location: env.txt
***


## 📈 Results and Visualization
To review the output, including the raw coordinates and filtered line segments, look for the generated output files (e.g., IMG_XXXX_gaps.txt).

For visualizing the results:

Refer to the last section in the MAIN.py file. This section contains the code snippet responsible for drawing and displaying the results. You can adjust the plotting settings here.
***
## 🚧 Current Implementation Notes
Visualization Limitation
The current implementation doesn't overlay the final detected lines onto the original RGB image.

Reason: The pipeline currently initializes and processes the image using only grayscale images.

Workaround Needed: We'll have to find a workaround to load the original RGB image for visualization, or modify the initial processing, to correctly overlay the final line results.
