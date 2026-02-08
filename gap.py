import json

# Applies vertical spacing & fills gaps, using a dictionary input


def parse_lines(key_val, data, target_list):
    """
    Helper function to safely extract and parse nested JSON strings.
    Checks for both integer (MicroPython common) and string (standard JSON) keys.
    """

    key_int = int(key_val)
    key_str = str(key_val)
    lines_to_parse = None

    # 1. Attempt lookup using the integer key
    if key_int in data:
        lines_to_parse = data[key_int]
    # 2. Attempt lookup using the string key
    elif key_str in data:
        lines_to_parse = data[key_str]

    if lines_to_parse is None:
        return

    # 3. Process the found list of line segments
    for line_json_string in lines_to_parse:
        try:
            line_dict = json.loads(line_json_string)
            # CRITICAL FIX: Explicitly cast coordinates to integers
            segment = {
                'x1': int(line_dict['x1']),
                'y1': int(line_dict['y1']),
                'x2': int(line_dict['x2']),
                'y2': int(line_dict['y2'])
            }
            target_list.append(segment)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Skipping malformed line for offset {key_val}: {e}")


def check_lines_in_file(filename: str, offset_1: int, offset_2: int, fixed_height: int = 5, width: int = 50) -> int:
    """
    Loads line segment data from a JSON file, creates bounding boxes around
    segments associated with offset_1, and checks for intersections with
    segments associated with offset_2.
    """

    # 1. LOAD THE ENTIRE JSON DICTIONARY
    try:
        with open(filename, 'r') as f:
            data = json.load(f)

    except FileNotFoundError:
        print(f"Error: Data file not found at {filename}")
        return 0
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {filename}: {e}")
        return 0
    except OSError as e:
        print(f"Error opening or reading file {filename}: {e}")
        return 0

    # 2. EXTRACT AND PARSE REQUIRED LINES
    lines1 = []  # Lines for Bounding Boxes (offset_1)
    lines2 = []  # Lines for Intersection Check (offset_2)

    # Call the robust helper function with integer offsets
    parse_lines(offset_1, data, lines1)
    parse_lines(offset_2, data, lines2)

    if not lines1 or not lines2:
        print(f"Could not find required line segments (Offset {
              offset_1} or {offset_2}) in the file.")
        return 0

    # 3. CREATE BOUNDING BOXES (from lines1)
    offset_diff = offset_2 - offset_1

    bbox = []
    for line in lines1:
        # Use the explicit integer coordinates
        min_x1 = min(line['x1'], line['x2'])
        min_x_bbox = min_x1 + offset_diff
        # print(min_x_bbox)

        max_x_bbox = min_x_bbox + width

        y_center = line['y2']
        min_y_bbox = y_center - fixed_height
        max_y_bbox = y_center + fixed_height

        bounding_box_structure = (
            min_x_bbox, min_y_bbox, max_x_bbox, max_y_bbox)
        bbox.append(bounding_box_structure)

    # 4. CHECK FOR INTERSECTIONS (between bbox and lines2)
    count = 0
    hit_array = []
    # To understand AABB intersection, imagine checking if the projections
    # of the two boxes on both the X and Y axes overlap.
    for index, box in enumerate(bbox):
        min_x1, min_y1, max_x1, max_y1 = box  # Bounding box coordinates

        for line in lines2:
            box_hit = False
            # Line segment 2's implicit AABB coordinates
            min_x2 = min(line['x1'], line['x2'])
            max_x2 = max(line['x1'], line['x2'])

            min_y2 = min(line['y1'], line['y2'])
            max_y2 = max(line['y1'], line['y2'])

            # Check for overlap on the x-axis
            x_overlap = (max_x2 >= min_x1) and (min_x2 <= max_x1)
            # if x_overlap:
            # print(f"X Overlap Detected - Box {index}: Box X({min_x1},{max_x1}) Line X({min_x2},{max_x2})")

            # Check for overlap on the y-axis
            y_overlap = (max_y2 >= min_y1) and (min_y2 <= max_y1)
          #  if y_overlap:
            #    print(f"Y Overlap Detected - Box {index}: Box Y({min_y1},{max_y1}) Line Y({min_y2},{max_y2})")
            # print(f"Overlap Check - Box {index}: X Overlap={x_overlap}, Y Overlap={y_overlap}")
            # Check for intersection
            if x_overlap and y_overlap:
                box_hit = True
               # print(f"INTERSECTION: Box {index} ({offset_1}) hit line in {offset_2} (Count: {count + 1})")
                print(f"Intersection: Box {index}")
                count += 1
                break  # Move to the next bounding box
        hit_array.append(box_hit)
    print(f"Total bounding boxes checked: {len(bbox)}")
    print(f"Final total intersections found: {count}")
    print(hit_array)
    return count, hit_array


# Applies vertical spacing & fills gaps, using a dictionary input


def normalize_gaps(
        segments_by_offset_input,
        max_gap,
        min_gap,
        segment_index,
        logs=False):
    """
    Normalizes the vertical spacing and fills gaps for segments at a specific
    Offset X index, ensuring a minimum segment count is met by extending from the bottom.

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

    # 1. Populate all_segments and group them
    for offset_x, segments in segments_by_offset_input.items():
        current_offset_x = offset_x
        # Handle the case where values might be JSON strings or dicts
        for segment_data_raw in segments:
            try:
                segment_data = json.loads(segment_data_raw) if isinstance(
                    segment_data_raw, str) else segment_data_raw
            except json.JSONDecodeError:
                continue  # Skip malformed data

            original_json = json.dumps(segment_data)

            # Calculate Global Coordinates
            x1 = segment_data.get("x1", 0) + current_offset_x
            y1 = segment_data.get("y1", 0) + fixed_offset_y
            x2 = segment_data.get("x2", 0) + current_offset_x
            y2 = segment_data.get("y2", 0) + fixed_offset_y

            all_segments.append({
                'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                'original_json': original_json,
                'original_offset_x': current_offset_x,
                'original_segment_data': segment_data
            })

    # Group the segments by Offset X and determine the target offset
    segments_by_offset = {}
    for seg in all_segments:
        segments_by_offset.setdefault(seg['original_offset_x'], []).append(seg)

    sorted_offsets = sorted(segments_by_offset.keys())

    if not sorted_offsets or segment_index >= len(sorted_offsets) or segment_index < -len(sorted_offsets):
        print(f"Error: Segment index {
              segment_index} is out of range or no offsets found.")
        return {}

    TARGET_OFFSET_X = sorted_offsets[segment_index]
    target_segments = segments_by_offset[TARGET_OFFSET_X]

    print(f"Targeting Segment Index {segment_index} (Offset X: {
          TARGET_OFFSET_X}) for normalization.")

    # 2. Apply vertical spacing (Min Gap removal and Max Gap filling)
    target_segments.sort(key=lambda s: (
        min(s['y1'], s['y2']), min(s['x1'], s['x2'])))

    processed_segments = []
    i = 0
    LIMIT_LINES = 30

    while i < len(target_segments):
        current_segment = target_segments[i]
        current_y = min(current_segment['y1'], current_segment['y2'])
        processed_segments.append(current_segment)

        if len(processed_segments) >= LIMIT_LINES:
            # print(f"Normalization for Offset {TARGET_OFFSET_X} stopped at {LIMIT_LINES} lines.")
            break

        if i + 1 < len(target_segments):
            next_segment = target_segments[i+1]
            next_y = min(next_segment['y1'], next_segment['y2'])
            vertical_distance = next_y - current_y

            # Remove lines too close (Min Gap)
            if vertical_distance < min_gap:
                # print(f"  [Remove] Line at Y={next_y} (Distance {vertical_distance} < {min_gap})")
                target_segments.pop(i + 1)
                continue

            # Add lines if gap is too large (Max Gap)
            elif vertical_distance > max_gap:
                original_data = current_segment['original_segment_data']
                local_x1 = original_data.get('x1', 0)
                local_x2 = original_data.get('x2', 0)

                new_y = current_y + (vertical_distance // 2)

                # Reconstruct the minimal segment dictionary
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

                # print(f"  [Insert] New line at Y={new_y} (Distance {vertical_distance} > {max_gap})")

                i += 1  # Advance 'i' by one more to skip the newly inserted line

        i += 1

    final_segments_target = processed_segments

    # 5. MINIMUM SEGMENT COUNT ENFORCEMENT (Extending from the Bottom)
    MIN_REQUIRED_SEGMENTS = 30
    MAX_IMAGE_HEIGHT = 1080  # Assuming FHD height for the vertical span

    if len(final_segments_target) < MIN_REQUIRED_SEGMENTS:
        print(f"\n[QC Check] Segment count ({len(final_segments_target)}) is below minimum ({
              MIN_REQUIRED_SEGMENTS}). Extending from the bottom...")

        segments_to_add = MIN_REQUIRED_SEGMENTS - len(final_segments_target)

        # --- 1. DETERMINE STARTING Y AND SPAN ---
        if not final_segments_target:
            # Fallback: If no segments were found, start at the top
            starting_y = 0
            vertical_span_to_fill = MAX_IMAGE_HEIGHT
            local_x1 = TARGET_OFFSET_X
            local_x2 = TARGET_OFFSET_X + 50
        else:
            # Find the y-coordinate of the bottom-most segment
            last_segment = final_segments_target[-1]
            last_y = max(last_segment['y1'], last_segment['y2'])

            starting_y = last_y
            vertical_span_to_fill = MAX_IMAGE_HEIGHT - last_y

            # Use the data from the last segment as a template
            original_data = last_segment['original_segment_data']
            local_x1 = original_data.get('x1', 0)
            local_x2 = original_data.get('x2', 0)

        # Calculate the required spacing based on the remaining distance and number of segments needed
        # We divide the remaining vertical span by the number of segments to add plus one (to account for the gap after the last one).
        if segments_to_add > 0:
            ideal_spacing = vertical_span_to_fill // (segments_to_add + 1)
        else:
            ideal_spacing = 0

        # --- 2. ADD THE REQUIRED SEGMENTS ---
        for k in range(1, segments_to_add + 1):

            # Place the new line k * ideal_spacing units below the starting Y
            new_y_global = starting_y + (k * ideal_spacing)

            if new_y_global >= MAX_IMAGE_HEIGHT:
                # print("Warning: Hit maximum image height during aggressive filling.")
                break

            # Reconstruct the minimal segment dictionary (relative coordinates)
            new_segment_data = {
                "x1": local_x1, "y1": new_y_global - fixed_offset_y,
                "x2": local_x2, "y2": new_y_global - fixed_offset_y,
                "length": 0, "magnitude": 0, "theta": 90, "rho": new_y_global - fixed_offset_y
            }
            new_original_json = json.dumps(new_segment_data)

            # Create the new segment dictionary (global coordinates)
            new_segment = {
                'x1': local_x1 + TARGET_OFFSET_X, 'y1': new_y_global,
                'x2': local_x2 + TARGET_OFFSET_X, 'y2': new_y_global,
                'original_json': new_original_json,
                'original_offset_x': TARGET_OFFSET_X,
                'original_segment_data': new_segment_data
            }
            final_segments_target.append(new_segment)

        print(f"Total segments after extending from bottom: {
              len(final_segments_target)}")

    # 6. Combining the results

    # Sort the final list again to maintain order after aggressive filling
    final_segments_target.sort(key=lambda s: (
        min(s['y1'], s['y2']), min(s['x1'], s['x2'])))

    final_segments = final_segments_target

    print(f"Total segments after normalization at Offset {
          TARGET_OFFSET_X}: {len(final_segments_target)}")

    # Add back all the untouched segments
    for offset, segments in segments_by_offset.items():
        if offset != TARGET_OFFSET_X:
            final_segments.extend(segments)

    # Group the final list by offset for the final output format
    final_groups = {}
    for seg in final_segments:
        final_groups.setdefault(seg['original_offset_x'], []).append(
            seg['original_json'])

    print(f"\nNormalization complete. Returning final data structure.")
    if logs:
        try:
            log("logs.txt", message=final_groups,
                function_name="normalize_gaps")
        except Exception as log_error:
            print(f"Logging failed: {log_error}")

    return final_groups
