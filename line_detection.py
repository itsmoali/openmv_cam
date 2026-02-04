
import image
import sensor
from utils import log, load_env


# -----------------------------------------------------------------------------
# Image Processing Function
# Used to extract tiles and detect line segments
# -----------------------------------------------------------------------------

def process_image(img_path, coords, offset_y=0, sensor_type="VGA", logs=False, img_width=None, img_height=None):
    """
    Reads a raw image file, extracts image tiles based on specified offsets,
    processes each tile, and detects line segments within it.

    Args:
        img_path (str): Path to the raw, binary image file.
        coords (dict): A dictionary where keys are arbitrary identifiers (index)
                       and values are strings representing the **X offset** of the
                       tile start point in pixels (e.g., {'tile_0': '50', 'tile_1': '100'}).
                       The function sorts these by offset value before processing.
        offset_y (int, optional): The fixed vertical offset (Y-coordinate) in pixels
                                  to apply to all tile extractions. Defaults to 0.
        sensor_type (str, optional): Defines the image dimensions and tile size.
                                     Supported values are "VGA", "QVGA", "QXGA", "WQXGA2".
                                     Defaults to "VGA".
        logs (bool, optional): If True, attempts to log the final segment results
                               using the `log` function from `utils`. Defaults to False.
        img_width (int, optional): Override image width (for dynamic resolution).
        img_height (int, optional): Override image height (for dynamic resolution).

    Returns:
        dict: A dictionary where keys are the **X offsets** (int) and values are
              lists of detected line segment dictionaries (local tile coordinates).
              Returns None on fatal error (e.g., FileNotFoundError).

              Example: {50: [{'x1': 5, 'y1': 10, ...}, {...}], 100: [...]}
    """
    try:
        # Verify file exists before opening
        try:
            with open(img_path, "rb") as test:
                test.read(1)
        except OSError:
            # Try with absolute path if relative path fails
            if not img_path.startswith("/"):
                alt_path = "/" + img_path
                try:
                    with open(alt_path, "rb") as test:
                        test.read(1)
                    img_path = alt_path
                    print("Using absolute path: {}".format(img_path))
                except OSError:
                    pass
        
        # Open the raw image file
        with open(img_path, "rb") as img:

            # Sort coordinates by X offset value
            sorted_data_list = sorted(
                coords.items(),
                key=lambda item: int(item[1]))

            print("Processing in order: {}".format(sorted_data_list))

            # 2. Set image/tile dimensions based on sensor type or explicit dimensions
            if img_width and img_height:
                # Use explicit dimensions
                Width = img_width
                Height = img_height
                # Scale tile width proportionally (base: VGA 640x480, tile 50px)
                TILE_W = max(50, int(50 * Width / 640))
                TILE_H = Height
            elif sensor_type == "QVGA":
                TILE_W = 160
                TILE_H = 120
                Width = 320
                Height = 240
            elif sensor_type == "QXGA":
                TILE_W = 160  # ~50 * 3.2
                TILE_H = 1536
                Width = 2048
                Height = 1536
            elif sensor_type == "WQXGA2":
                TILE_W = 200  # ~50 * 4
                TILE_H = 1944
                Width = 2592
                Height = 1944
            else:  # VGA (default)
                TILE_W = 50
                TILE_H = 480
                Width = 640
                Height = 480
            
            print("Image: {}x{}, Tile: {}x{}".format(Width, Height, TILE_W, TILE_H))

            results = {}
            for index, offset_str in sorted_data_list:
                offset = int(offset_str.strip())

                # Calculate file pointer start position (Y-offset * width + X-offset)
                start = (offset_y * Width + offset)
                img.seek(start)

                data = bytearray()

                # Construct data array for image tile
                for i in range(TILE_H):
                    # Read the tile width (TILE_W) of the current row
                    row = img.read(TILE_W)
                    data.extend(row)

                    # Skip the remaining part of the row we aren't reading
                    # Move pointer (Width - TILE_W) bytes forward from the current position (1)
                    img.seek(Width - TILE_W, 1)

                # Create image object for the tile
                tile_img = image.Image(
                    TILE_W, TILE_H, sensor.GRAYSCALE, buffer=data, copy_to_fb=True)

                # Apply Gaussian blur for noise reduction and unsharp masking for edge enhancement
                tile_img.gaussian(2, unsharp=True)

                # Detect segments and store results using the X offset as the key
                results[offset] = detect_segments(tile_img)

        # 3. Logging (Optional)
        if logs:
            try:
                # Assuming log is defined in utils
                log("logs.txt", message=results, function_name="process_image")
            except Exception as log_error:
                print("Logging failed: {}".format(log_error))

        return results

    except OSError as e:
        # MicroPython uses OSError instead of FileNotFoundError
        print("An error occurred: Image file '{}' not found: {}".format(img_path, e))
        return None
    except Exception as e:
        print("An error occurred: {}".format(e))
        return None

# -----------------------------------------------------------------------------
# Line Segment Detection Function
# Helper function to detect line segments in an image tile
# -----------------------------------------------------------------------------
def detect_segments(img,length = 15, min_degree=0, max_degree=180):
    """
    Detects line segments in a given image object and filters them based on length

    Args:
        img (image.Image): The image object (tile) to process.
        length (int, optional): The minimum length (in pixels) for a line segment to be considered.
                            Defaults to 15.
        min_degree (int, optional): The minimum acceptable angle (theta) for a line segment.
                                    Defaults to 0.
        max_degree (int, optional): The maximum acceptable angle (theta) for a line segment.
                                    Defaults to 180.

    Returns:
        list: A list of dictionaries, where each dictionary represents a filtered
              line segment with its local tile coordinates and metrics.

              Keys include: 'x1', 'y1', 'x2', 'y2', 'length', 'theta', 'rho'.
    """
    segments = []

    # img.find_line_segments() returns 'line' objects
    for line in img.find_line_segments(merge_distance=5, max_theta_difference=40):

        # Filter based on length and angle (theta)
        if (line.length() > length) and (min_degree <= line.theta()) and (line.theta() <= max_degree):

            # 2. Manually construct the dictionary from the line object's methods
            segment_dict = {
                "x1": line.x1(),
                "y1": line.y1(),
                "x2": line.x2(),
                "y2": line.y2(),
                "length": line.length(),
                "theta": line.theta(), # Angle in degrees
                "rho": line.rho()       # Distance from origin in Hough space
            }

            # 3. Append the valid dictionary to the list
            segments.append(segment_dict)

    return segments

#---------USAGE-----------
#img_file = "IMG/binary/IMG_2796.bin"
#coords = load_env("env.txt")

# 1. Process the image and detect segments
#res = process_image(img_file, coords=coords, offset_y=0, sensor_type="VGA", logs= False)
#print(res)

