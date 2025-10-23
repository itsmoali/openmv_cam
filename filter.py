import json
import math


# Process the segments by converting the local coordinates to global coordinates
def parse_segments(filename, fixed_offset_y):

    segments = []
    current_offset_x = 0

    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()

                if line.startswith("Offset X: "):
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
    unique = set()
    filtered_segments = []

    for seg in segments:
        # Sorts the endpoints to create a unique line signature
        sig = tuple(sorted([(seg['x1'], seg['y1']), (seg['x2'], seg['y2'])]))

        if sig not in unique:
            unique.add(sig)
            filtered_segments.append(seg)

    print(f"After Duplicates Filter: {len(filtered_segments)}")
    return filtered_segments

# The vertical lines are used as cutoff points to reflect the desired ROI


def filter_vertical_cutoff(segments):

    # Sort segments top-to-bottom, left-to-right
    segments.sort(key=lambda s: (
        s['original_offset_x'], min(s['y1'], s['y2'])))

    vertical_line_y_cutoff = None

    for seg in segments:

        theta = seg['theta']
        is_vertical = (theta <= 10) or (theta >= 170)

        if is_vertical:
            # Found the vertical cutoff point
            vertical_line_y_cutoff = min(seg['y1'], seg['y2'])
            break

    if vertical_line_y_cutoff is not None:
        # Keep line segments that are below the vertical cutoff line
        filtered_segments = [seg for seg in segments
                             if min(seg['y1'], seg['y2']) >= vertical_line_y_cutoff]
        print(f"Vertical Cutoff Y found: {vertical_line_y_cutoff}")
        return filtered_segments

    print("Vertical Cutoff: No vertical line found, keeping all.")
    return segments

# Only keep horizontal lines


def filter_only_horizontal(segments):

    # Horizontal threshold
    filtered_segments = [seg for seg in segments
                         if 80 <= seg['theta'] <= 100]

    print(f"Final Horizontal Filtered Segments: {len(filtered_segments)}")
    return filtered_segments


# Main Function
# -----------------------

# Uses the 3 helper functions for filtering
def filter_line_segments(input_file, offset_y):

    # Load data
    segments = parse_segments(input_file, offset_y)
    if segments is None:
        return

    output_file = str(input_file).replace("_processed.txt", "_filtered.txt")
    print(output_file)
    print(f"Initial Segments: {len(segments)}")

    # 2. Apply Filters
    segments = filter_duplicates(segments)        # Remove Duplicates
    segments = filter_vertical_cutoff(
        segments)   # Remove Above Vertical Cutoff
    segments = filter_only_horizontal(segments)   # Keep Only Horizontal Lines

    # Groups lines by original offset X
    groups = {}
    for seg in segments:
        offset_x = seg['original_offset_x']
        if offset_x not in groups:
            groups[offset_x] = []
        groups[offset_x].append(seg['original_json'])

    try:
        with open(output_file, 'w') as out_f:
            for offset_x in sorted(groups.keys()):
                out_f.write(f"Offset X: {offset_x}\n")
                for json_data in groups[offset_x]:
                    out_f.write(json_data + "\n")
        print("Data written successfully.")
        print(f"Successfully wrote filtered data to: {output_file}")
        return output_file
    except Exception as e:
        print(f"Error writing output file: {e}")


# filter_line_segments("IMG_2796_processed.txt", "IMG_2796_filtered.txt", 0)
