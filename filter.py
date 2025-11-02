import json
import math


def parse_segments(filename, fixed_offset_y):
    """
    Loads line segment data from a file and converts local tile coordinates
    (x1, y1, x2, y2) to global image coordinates by adding the X offset
    (read from file headers) and a fixed Y offset.

    Input file format expected: Interspersed 'Offset X: <value>' headers and
    single-line JSON objects containing segment data.

    :param filename: Path to the input segment data file.
    :param fixed_offset_y: A constant vertical offset applied to all Y coordinates.
    :return: List of dictionaries with global coordinates and metadata, or None on failure.
    """
    segments = []
    current_offset_x = 0

    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()

                if line.startswith("Offset X: "):
                    # Update the current horizontal tile offset
                    current_offset_x = int(line.split(":")[1].strip())

                elif line.startswith("{") and line.endswith("}"):
                    try:
                        segment_data = json.loads(line)

                        # Calculate Global Coordinates
                        x1 = segment_data["x1"] + current_offset_x
                        y1 = segment_data["y1"] + fixed_offset_y
                        x2 = segment_data["x2"] + current_offset_x
                        y2 = segment_data["y2"] + fixed_offset_y

                        # Store the segment with its original data and global coordinates
                        segments.append({
                            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                            'theta': segment_data['theta'],
                            'original_json': line,
                            'original_offset_x': current_offset_x
                        })
                    except (json.JSONDecodeError, KeyError):
                        pass
    except FileNotFoundError:
        print(f"Error: Input file '{filename}' not found.")
        return None

    return segments


# Filter Functions
# ---------------------------

def filter_duplicates(segments):
    """
    Removes line segments that are duplicates (have the same global endpoints).
    Creates a unique signature by sorting the endpoints.

    :param segments: List of segment dictionaries with global coordinates.
    :return: List of unique segment dictionaries.
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


def filter_vertical_cutoff(segments):
    """
    Implements a Region of Interest (ROI) filter by finding the first vertical line
    and discarding all segments that appear ABOVE that line's minimum Y coordinate.

    :param segments: List of segment dictionaries.
    :return: List of segments remaining below the determined cutoff Y-coordinate.
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


def filter_only_horizontal(segments):
    """
    Final filter to keep only lines with an angle (theta) close to 90 degrees.

    :param segments: List of segment dictionaries.
    :return: List of segment dictionaries where 80 <= theta <= 100.
    """

    # Horizontal lines are those with theta between 80 and 100 degrees
    filtered_segments = [seg for seg in segments
                         if 80 <= seg['theta'] <= 100]

    print(f"Final Horizontal Filtered Segments: {len(filtered_segments)}")
    return filtered_segments


# Main Function
# -----------------------

def filter_line_segments(input_file, offset_y):
    """
    Main function that orchestrates the loading, filtering, grouping, and saving
    of line segment data.

    :param input_file: The path to the raw segment data file (e.g., 'IMG_xxx_processed.txt').
    :param offset_y: The fixed vertical offset to apply during parsing.
    :return: The path to the newly created filtered output file, or None on failure.
    """

    # 1. Load data and convert coordinates
    segments = parse_segments(input_file, offset_y)
    if segments is None:
        return

    output_file = str(input_file).replace("_processed.txt", "_filtered.txt")
    print(output_file)
    print(f"Initial Segments: {len(segments)}")

    # 2. Apply Filters sequentially
    segments = filter_duplicates(segments)      
    segments = filter_vertical_cutoff(segments) 
    segments = filter_only_horizontal(segments)  

    # 3. Group filtered lines back by original tile offset
    groups = {}
    for seg in segments:
        offset_x = seg['original_offset_x']
        if offset_x not in groups:
            groups[offset_x] = []
        # Store the original JSON data for clean output
        groups[offset_x].append(seg['original_json'])

    # 4. Write the final grouped data to the output file
    try:
        with open(output_file, 'w') as out_f:
            # Write headers and segment data, sorted by tile offset
            for offset_x in sorted(groups.keys()):
                out_f.write(f"Offset X: {offset_x}\n")
                for json_data in groups[offset_x]:
                    out_f.write(json_data + "\n")
        print("Data written successfully.")
        print(f"Successfully wrote filtered data to: {output_file}")
        return output_file
    except Exception as e:
        print(f"Error writing output file: {e}")
