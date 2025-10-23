import json
import math

# Applies vertical spacing & fills gaps
def normalize_segment_by_index(input_file, max_gap, min_gap, segment_index):


    fixed_offset_y = 0
    all_segments = []
    current_offset_x = 0

    output_file = str(input_file).replace("_filtered.txt", "_gaps.txt")
    try:
        with open(input_file, 'r') as f:
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

                        all_segments.append({
                            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                            'original_json': line,
                            'original_offset_x': current_offset_x
                        })
                    except (json.JSONDecodeError, KeyError):
                        pass
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
        return

    # Group the segments by Offset X and determine the target offset
    segments_by_offset = {}
    for seg in all_segments:
        segments_by_offset.setdefault(seg['original_offset_x'], []).append(seg)

    sorted_offsets = sorted(segments_by_offset.keys())

    if segment_index >= len(sorted_offsets):
        print(f"Error: Segment index {segment_index} is out of range. Found {
              len(sorted_offsets)} offsets.")
        return

    TARGET_OFFSET_X = sorted_offsets[segment_index]
    target_segments = segments_by_offset[TARGET_OFFSET_X]

    print(f"Targeting Segment Index {segment_index} (Offset X: {
          TARGET_OFFSET_X}) for normalization.")

    # Apply vertical spacing

    # Sort from top to bottom
    target_segments.sort(key=lambda s: (
        min(s['y1'], s['y2']), min(s['x1'], s['x2'])))

    processed_segments = []
    i = 0

    while i < len(target_segments):
        current_segment = target_segments[i]
        current_y = min(current_segment['y1'], current_segment['y2'])
        processed_segments.append(current_segment)

        # Limits the total number of lines to 24
        # 24 doesnt give correct results (look into it more)
        if len(processed_segments) >= 30:
            print(f"Normalization for Offset {
                  TARGET_OFFSET_X} stopped at 24 lines.")
            break

        if i + 1 < len(target_segments):
            next_segment = target_segments[i+1]
            next_y = min(next_segment['y1'], next_segment['y2'])
            vertical_distance = next_y - current_y

            # 2. Remove lines too close
            if vertical_distance < min_gap:
                print(f"  [Remove] Line at Y={
                      next_y} (Distance {vertical_distance} < {min_gap})")
                target_segments.pop(i + 1)
                # Keep 'i' the same to re-evaluate the new line at i+1
                continue

            # Add lines if gap is too large
            elif vertical_distance > max_gap:
                new_y = current_y + (vertical_distance // 2)

                # New segment data
                new_segment = {
                    'x1': current_segment['x1'], 'y1': new_y,
                    'x2': current_segment['x2'], 'y2': new_y,
                    'original_json': f'{{"x1":{current_segment["x1"]}, "y1":{new_y}, "x2":{current_segment["x2"]}, "y2":{new_y}, "length":0, "magnitude":0, "theta":90, "rho":{new_y}}}',
                    'original_offset_x': TARGET_OFFSET_X
                }

                target_segments.insert(i + 1, new_segment)
                processed_segments.append(new_segment)

                print(f"  [Insert] New line at Y={
                      new_y} (Distance {vertical_distance} > {max_gap})")

                # Advance 'i' by one more to skip the newly inserted line for the next comparison
                i += 1

        i += 1

    # Combining the results
    final_segments = processed_segments

    # Add back all the untouched segments
    for offset, segments in segments_by_offset.items():
        if offset != TARGET_OFFSET_X:
            final_segments.extend(segments)

    # Group the final list by offset for correct output file format
    final_groups = {}
    for seg in final_segments:
        final_groups.setdefault(seg['original_offset_x'], []).append(
            seg['original_json'])

    try:
        with open(output_file, 'w') as out_f:
            for offset_x in sorted(final_groups.keys()):
                out_f.write(f"Offset X: {offset_x}\n")
                for json_data in final_groups[offset_x]:
                    out_f.write(json_data + "\n")
        print(f"\nSuccessfully wrote final normalized data to: {
              output_file}")
    except Exception as e:
        print(f"Error writing output file: {e}")
