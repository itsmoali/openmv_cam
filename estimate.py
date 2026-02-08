def extract_boundary_segments(filtered_segments_dict):
    """
    Identifies the top-most and bottom-most line segments and returns them
    in a list format compatible with the existing drawing function.

    Args:
        filtered_segments_dict: Dictionary {offset_x: [segment_list]}

    Returns:
        dict: A dictionary {offset_x: [top_segment, bottom_segment]}
    """
    boundary_results = {}

    for offset_x, segment_list in filtered_segments_dict.items():
        if not segment_list:
            continue

        # Find the segment with the lowest Y value (Top)
        top_segment = min(segment_list, key=lambda s: min(s['y1'], s['y2']))

        # Find the segment with the highest Y value (Bottom)
        bottom_segment = max(segment_list, key=lambda s: max(s['y1'], s['y2']))

        # We store them in a LIST so your drawing function can iterate through them
        boundary_results[offset_x] = [top_segment, bottom_segment]


    print(f"Extracted boundaries for {len(boundary_results)} groups.")
    return boundary_results

def calculate_boundary_difference(boundary_dict):
    """
    Calculates the vertical distance (height) between the top and bottom
    segments for each offset group.

    Args:
        boundary_dict: Dictionary {offset_x: [top_segment, bottom_segment]}

    Returns:
        dict: A dictionary {offset_x: vertical_difference_in_pixels}
    """
    differences = {}

    for offset_x, segments in boundary_dict.items():
        # Ensure we have both segments to compare
        if len(segments) < 2:
            continue

        top = segments[0]
        bottom = segments[1]

        # Calculate the average Y for the top line
        avg_y_top = (top['y1'] + top['y2']) / 2

        # Calculate the average Y for the bottom line
        avg_y_bottom = (bottom['y1'] + bottom['y2']) / 2

        # Difference (Bottom Y is higher than Top Y in image coordinates)
        height_diff = avg_y_bottom - avg_y_top

        differences[offset_x] = round(height_diff, 2)

    return differences
def get_box_reference_metrics(boundary_dict, left_key=200, right_key=1500):
    """
    Calculates the actual top boundary and height of the box in the current frame.
    """
    heights = []
    tops = []

    for key in [left_key, right_key]:
        if key in boundary_dict:
            top_seg, bottom_seg = boundary_dict[key]
            y_top = (top_seg['y1'] + top_seg['y2']) / 2
            y_bottom = (bottom_seg['y1'] + bottom_seg['y2']) / 2
            heights.append(y_bottom - y_top)
            tops.append(y_top)

    # Use averages to define the "Box" for this frame
    actual_height = sum(heights) / len(heights) if heights else 920
    actual_top = sum(tops) / len(tops) if tops else 0

    return actual_top, actual_height

def analyze_virtual_slots(filtered_groups, box_top, box_height, center_offset=800):
    """
    Creates 24 virtual windows starting 100px from the box top and checks for disks.

    Args:
        filtered_groups: Dict of filtered lines.
        box_top: The average Y coordinate of the box's top boundary.
        box_height: The average vertical height of the box (Bottom Y - Top Y).
    """
    # Calculate Scaling Factor (Current Height / Reference Height)
    S = box_height / 920.0

    # Scaled reference values
    scaled_offset = 100.0 * S
    scaled_pitch = 30.0 * S
    window_half_height = scaled_pitch / 2.0  # Window size to prevent overlap

    # Get center detections from the 800 offset
    center_disks = filtered_groups.get(center_offset, [])

    inventory = {}

    for i in range(1, 25):  # Slots 1 through 24
        # Calculate the expected center Y for this slot
        expected_y = box_top + scaled_offset + ((i - 1) * scaled_pitch)

        # Define the virtual bounding box (Window)
        win_top = expected_y - window_half_height
        win_bottom = expected_y + window_half_height

        # Check if any detected disk falls within this window
        found_disk = None
        for disk in center_disks:
            disk_y = (disk['y1'] + disk['y2']) / 2.0
            if win_top <= disk_y <= win_bottom:
                found_disk = disk
                break

        inventory[f"Slot_{i}"] = {
            "status": "Occupied" if found_disk else "Empty",
            "expected_y": round(expected_y, 1),
            "actual_y": round((found_disk['y1'] + found_disk['y2']) / 2.0, 1) if found_disk else None
        }

    return inventory
