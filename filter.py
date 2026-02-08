import math
from utils import log
"""
This module provides a pipeline for filtering line segment data that has been
detected within tiled sections of a larger image. It converts tile-local
coordinates to global coordinates for filtering (to handle duplicates and
vertical cutoffs across tiles), and then returns the filtered results in the
original tile-grouped dictionary structure.
"""

# -----------------------------------------------------------------------------
# Segment Processing Function
# -----------------------------------------------------------------------------
def process_segments(segments_by_offset_x, fixed_offset_y):
    """
    Converts the dictionary of raw segment data (grouped by offset_x) into a flat
    list of dictionaries with global coordinates. This also prepares a 'segment_dict'
    key for easy reconstruction of the final output dictionary.

    Args:
        segments_by_offset_x: Dictionary where keys are 'Offset X' and values are
                                 lists of raw segment dictionaries (local coordinates).
        fixed_offset_y: A constant vertical offset applied to all Y coordinates.

    Return:
        list: List of dictionaries with global coordinates and metadata.
    """
    segments = []

    for current_offset_x, segment_list in segments_by_offset_x.items():
        for segment_data in segment_list:


            # Calculate Global Coordinates (used only for filtering)
            x1 = segment_data["x1"] + current_offset_x
            y1 = segment_data["y1"] + fixed_offset_y
            x2 = segment_data["x2"] + current_offset_x
            y2 = segment_data["y2"] + fixed_offset_y

            # Store the segment with its original data and global coordinates
            segments.append({
                'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                'theta': segment_data['theta'],
                'segment_dict': segment_data, # Store the original dictionary structure
                'original_offset_x': current_offset_x
            })

    return segments

# -----------------------------------------------------------------------------
# Filters out Dulpicates
# -----------------------------------------------------------------------------
def filter_duplicates(segments):
    """
    Removes line segments that are duplicates (have the same global endpoints).
    Creates a unique signature by sorting the endpoints.

    Args:
        segments: List of segment dictionaries with global coordinates.

    Returns:
        List: List of unique segment dictionaries.
    """
    unique = set()
    filtered_segments = []

    for seg in segments:
        # Create a unique tuple signature for the line, irrespective of endpoint order (x1,y1 vs x2,y2)
        sig = tuple(sorted([(seg['x1'], seg['y1']), (seg['x2'], seg['y2'])]))

        if sig not in unique:
            unique.add(sig)
            filtered_segments.append(seg)

    print(f"After Duplicates Filter: {len(filtered_segments)}")
    return filtered_segments

# -----------------------------------------------------------------------------
# Filters Lines below a Vertical Cutoff
# -----------------------------------------------------------------------------
def filter_vertical_cutoff(segments):
    """
    Implements a Region of Interest (ROI) filter by finding the first vertical line
    and discarding all segments that appear ABOVE that line's minimum Y coordinate.

    Args:
        segments: List of segment dictionaries.
    Returns:
        List: List of segments remaining below the determined cutoff Y-coordinate.
    """

    # Sort segments top-to-bottom, left-to-right to find the highest cutoff line first
    segments.sort(key=lambda s: (
        s['original_offset_x'], min(s['y1'], s['y2'])))

    vertical_line_y_cutoff = None

    for seg in segments:
        theta = seg['theta']
        # Define vertical lines as having a theta near 0 or 180 degrees (0-10 or 170-180)
        is_vertical = (theta <= 10) or (theta >= 170)

        if is_vertical:
            # Found the vertical cutoff point (the highest point of the vertical line)
            vertical_line_y_cutoff = min(seg['y1'], seg['y2'])
            break

    if vertical_line_y_cutoff is not None:
        # Keep line segments that are at or below the vertical cutoff line
        filtered_segments = [seg for seg in segments
                             if min(seg['y1'], seg['y2']) >= vertical_line_y_cutoff]
        print(f"Vertical Cutoff Y found: {vertical_line_y_cutoff}")
        return filtered_segments

    print("Vertical Cutoff: No vertical line found, keeping all.")
    return segments

# -----------------------------------------------------------------------------
# Filters Only Horizontal Lines
# -----------------------------------------------------------------------------
def filter_only_horizontal(segments):
    """
    Final filter to keep only lines with an angle (theta) close to 90 degrees.

    Args:
        segments: List of segment dictionaries.
    Returns:
        List: List of segment dictionaries where 80 <= theta <= 100.
    """

    # Horizontal lines are those with theta between 80 and 120 degrees
    filtered_segments = [seg for seg in segments
                         if 80 <= seg['theta'] <= 120]

    print(f"Final Horizontal Filtered Segments: {len(filtered_segments)}")
    return filtered_segments


# -----------------------------------------------------------------------------
# Filters Line Segments Main Function
# -----------------------------------------------------------------------------

def filter_line_segments(segment_data_dict, offset_y, logs = False):
    """
    Processes, filters, and groups line segment data, returning the result
    as a dictionary structured identically to the input.

    Args:
        segment_data_dict:: Dictionary of raw segment data grouped by offset_x.
        offset_y: The fixed vertical offset to apply during processing.
        logs: Boolean flag to enable logging of the filtered results.

    Returns:
        dict: A dictionary of filtered segment data grouped by offset_x, or None on failure.
    """

    # Process data and convert coordinates
    segments = process_segments(segment_data_dict, offset_y)

    print(f"Initial Segments: {len(segments)}")

    # 2. Apply Filters sequentially
    segments = filter_duplicates(segments)
    segments = filter_vertical_cutoff(segments)
    segments = filter_only_horizontal(segments)

    # 3. Re-group filtered lines into the target output structure (dictionary)
    # The output structure is {offset_x: [segment_dict, segment_dict, ...]}
    filtered_groups = {}

    for seg in segments:
        offset_x = seg['original_offset_x']

        if offset_x not in filtered_groups:
            filtered_groups[offset_x] = []

        # Append the original segment dictionary stored during processing
        filtered_groups[offset_x].append(seg['segment_dict'])

    print(f"Successfully processed and grouped filtered data.")

    if logs:
        try:
            log("logs.txt", message=filtered_groups, function_name="filter_line_segments")
        except Exception as log_error:
            print(f"Logging failed: {log_error}")

    # 4. Return the resulting dictionary
    return filtered_groups


# ---------USAGE-----------
#img_file = "IMG/binary/IMG_2796.bin"
#coords = load_env("env.txt")
#res = process_image(img_file, coords=coords, offset_y=0, sensor_type="VGA", logs= False)
#results = filter_line_segments(res, offset_y=0, logs=True)
#print(results)
