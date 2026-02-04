import json
import math
from utils import log

# Applies vertical spacing & fills gaps, using a dictionary input
def normalize_gaps(
    segments_by_offset_input,
    max_gap,
    min_gap,
    segment_index,
    logs=False):
    """
    Normalizes the vertical spacing and fills gaps for segments at a specific
    Offset X index, taking data as a dictionary input.

    Args:
        segments_by_offset_input: A dictionary where keys are Offset X values (int)
                                  and values are lists of segment dictionaries.
        max_gap: The maximum vertical distance allowed between segments before
                 a new segment is inserted.
        min_gap: The minimum vertical distance allowed between segments before
                 the later segment is removed.
        segment_index: The index of the Offset X group to target for normalization.

    Returns:
        A dictionary where keys are Offset X values and values are lists of
        the processed segments as their original JSON strings.
    """

    fixed_offset_y = 0
    all_segments = []

    # 1. Populate all_segments from the input dictionary
    for offset_x, segments in segments_by_offset_input.items():
        current_offset_x = offset_x
        for segment_data in segments:
            # Recreate 'original_json' for later output formatting
            original_json = json.dumps(segment_data)

            # Calculate Global Coordinates
            x1 = segment_data.get("x1", 0) + current_offset_x
            y1 = segment_data.get("y1", 0) + fixed_offset_y
            x2 = segment_data.get("x2", 0) + current_offset_x
            y2 = segment_data.get("y2", 0) + fixed_offset_y

            all_segments.append({
                'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                # Store the original JSON string for output
                'original_json': original_json,
                'original_offset_x': current_offset_x,
                # Store original data fields for use when creating new segments
                'original_segment_data': segment_data
            })

    # Group the segments by Offset X and determine the target offset
    segments_by_offset = {}
    for seg in all_segments:
        segments_by_offset.setdefault(seg['original_offset_x'], []).append(seg)

    sorted_offsets = sorted(segments_by_offset.keys())

    if segment_index >= len(sorted_offsets):
        print("Error: Segment index {} is out of range. Found {} offsets.".format(
              segment_index, len(sorted_offsets)))
        return {}

    TARGET_OFFSET_X = sorted_offsets[segment_index]
    target_segments = segments_by_offset[TARGET_OFFSET_X]

    print("Targeting Segment Index {} (Offset X: {}) for normalization.".format(
          segment_index, TARGET_OFFSET_X))

    # Apply vertical spacing

    # Sort from top to bottom
    target_segments.sort(key=lambda s: (
        min(s['y1'], s['y2']), min(s['x1'], s['x2'])))

    processed_segments = []
    i = 0
    # Limit to prevent excessive processing
    LIMIT_LINES = 27

    while i < len(target_segments):
        current_segment = target_segments[i]
        current_y = min(current_segment['y1'], current_segment['y2'])
        processed_segments.append(current_segment)

        if len(processed_segments) >= LIMIT_LINES:
            print("Normalization for Offset {} stopped at {} lines.".format(
                  TARGET_OFFSET_X, LIMIT_LINES))
            break

        if i + 1 < len(target_segments):
            next_segment = target_segments[i+1]
            next_y = min(next_segment['y1'], next_segment['y2'])
            vertical_distance = next_y - current_y

            # Remove lines too close
            if vertical_distance < min_gap:
                print("  [Remove] Line at Y={} (Distance {} < {})".format(
                      next_y, vertical_distance, min_gap))
                target_segments.pop(i + 1)
                # Keep 'i' the same to re-evaluate the new line at i+1
                continue

            # Add lines if gap is too large
            elif vertical_distance > max_gap:
                original_data = current_segment['original_segment_data']
                local_x1 = original_data.get('x1', 0)
                local_x2 = original_data.get('x2', 0)

                new_y = current_y + (vertical_distance // 2)

                # New segment data
                # Reconstruct the minimal segment dictionary for the original_json string
                new_segment_data = {
                    "x1": local_x1, "y1": new_y - fixed_offset_y,
                    "x2": local_x2, "y2": new_y - fixed_offset_y,
                    "length": 0, "magnitude": 0, "theta": 90, "rho": new_y - fixed_offset_y
                }
                new_original_json = json.dumps(new_segment_data)

                new_segment = {
                    'x1': local_x1 + TARGET_OFFSET_X, 'y1': new_y,
                    'x2': local_x2 + TARGET_OFFSET_X, 'y2': new_y,
                    'original_json': new_original_json,
                    'original_offset_x': TARGET_OFFSET_X,
                    'original_segment_data': new_segment_data
                }

                target_segments.insert(i + 1, new_segment)
                processed_segments.append(new_segment)

                print("  [Insert] New line at Y={} (Distance {} > {})".format(
                      new_y, vertical_distance, max_gap))

                # Advance 'i' by one more to skip the newly inserted line for the next comparison
                i += 1

        i += 1

    # Combining the results
    final_segments = processed_segments

    # Add back all the untouched segments
    for offset, segments in segments_by_offset.items():
        if offset != TARGET_OFFSET_X:
            final_segments.extend(segments)

    # Group the final list by offset for the final output format
    # The output format is a dictionary of {offset_x: [json_string, ...]}
    final_groups = {}
    for seg in final_segments:
        final_groups.setdefault(seg['original_offset_x'], []).append(
            seg['original_json'])

    print("\nNormalization complete. Returning final data structure.")
    # Return the processed data structure instead of writing to a file
    if logs:
        try:
            log("logs.txt", message=final_groups, function_name="normalize_gaps")
        except Exception as log_error:
            print("Logging failed: {}".format(log_error))
    return final_groups
