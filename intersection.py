import json

# Used the create bounding boxes and check for intersections
def check_lines_in_dict(segments_dict, offset_1, offset_2, fixed_height=5, width=50):
    """
    Check for line intersections using a dictionary of segments.
    
    Args:
        segments_dict: Dictionary where keys are offset_x (int) and values are 
                      lists of JSON strings or segment dictionaries
        offset_1: X offset for first segment group
        offset_2: X offset for second segment group  
        fixed_height: Fixed height for bounding boxes
        width: Width of bounding boxes
        
    Returns:
        int: Count of intersections found
    """
    lines1 = []
    lines2 = []
    
    # Extract segments from dictionary
    for offset_x, segments in segments_dict.items():
        for segment_data in segments:
            # Handle both JSON strings and dictionaries
            if isinstance(segment_data, str):
                try:
                    segment_data = json.loads(segment_data)
                except json.JSONDecodeError:
                    continue
            
            segment = {
                'x1': segment_data.get('x1', 0),
                'y1': segment_data.get('y1', 0),
                'x2': segment_data.get('x2', 0),
                'y2': segment_data.get('y2', 0)
            }
            
            if offset_x == offset_1:
                lines1.append(segment)
            elif offset_x == offset_2:
                lines2.append(segment)
    
    if not lines1 or not lines2:
        print("Could not find both segments (Offset {} and {}) in dictionary.".format(offset_1, offset_2))
        return 0
    
    # Create bounding boxes from lines1
    bbox = []
    for line in lines1:
        min_x1 = min(line['x1'], line['x2'])
        min_x1_offset = min_x1
        max_x1_offset = min_x1_offset + width
        y2_center = line['y2']
        min_y_fixed = y2_center - fixed_height
        max_y_fixed = y2_center + fixed_height
        
        bounding_box_structure = (min_x1_offset, min_y_fixed, max_x1_offset, max_y_fixed)
        bbox.append(bounding_box_structure)
    
    # Check intersections
    count = 0
    for index, box in enumerate(bbox):
        min_x1, min_y1, max_x1, max_y1 = box
        
        for line in lines2:
            min_x2 = min(line['x1'], line['x2'])
            max_x2 = max(line['x1'], line['x2'])
            min_y2 = min(line['y1'], line['y2'])
            max_y2 = max(line['y1'], line['y2'])
            
            # Check for overlap on both axes
            x_overlap = (max_x2 >= min_x1) and (min_x2 <= max_x1)
            y_overlap = (max_y2 >= min_y1) and (min_y2 <= max_y1)
            
            if x_overlap and y_overlap:
                print("Line found in bounding box: {}".format(index))
                count += 1
    
    return count

def check_lines_in_file(filename, offset_1, offset_2, fixed_height=5, width = 50):


    lines1 = []
    lines2 = []
    current_offset = None

    #Use the filtered line segments to create bounding boxes and check for intersections
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # Check for the offset header
                # Just a quickfix, should be standradized later
                if line.startswith("Offset X:"):
                    try:
                        current_offset = int(line.split(":")[1].strip())
                    except ValueError:
                        current_offset = None
                    continue

                # Parsing lines
                if current_offset is not None:
                    try:
                        line_data = json.loads(line)
                        segment = {
                            'x1': line_data['x1'], 'y1': line_data['y1'],
                            'x2': line_data['x2'], 'y2': line_data['y2']
                        }

                        if current_offset == offset_1:
                            lines1.append(segment)
                        elif current_offset == offset_2:
                            lines2.append(segment)

                    except json.JSONDecodeError:
                        print("Skipping malformed JSON line: {}".format(line))

    except OSError as e:
        print("Error opening or reading file {}: {}".format(filename, e))
        return []

    if not lines1 or not lines2:
        # should never happen
        # Have to write code to handle this case
        print("Could not find both segments (Offset {} and {}) in the file.".format(offset_1, offset_2))
        return []

    # Storing bounding boxes
    bbox = []

    for line in lines1:
        min_x1 = min(line['x1'], line['x2'])
        min_x1_offset = min_x1
        max_x1_offset = min_x1_offset + width
        y2_center = line['y2']
        min_y_fixed = y2_center - fixed_height
        max_y_fixed = y2_center + fixed_height

        bounding_box_structure = (min_x1_offset, min_y_fixed, max_x1_offset, max_y_fixed)
        bbox.append(bounding_box_structure)

    count = 0
    for index,box in enumerate(bbox):
        #Boundibg box coordinates
        min_x1, min_y1, max_x1, max_y1 = box

        for line in lines2:
            min_x2 = min(line['x1'], line['x2'])
            max_x2 = max(line['x1'], line['x2'])

            min_y2 = min(line['y1'], line['y2'])
            max_y2 = max(line['y1'], line['y2'])

            # Check for overlap on the x-axis
            x_overlap = (max_x2 >= min_x1) and (min_x2 <= max_x1)

            # CHeck for overlap on the y-axis
            y_overlap = (max_y2 >= min_y1) and (min_y2 <= max_y1)

            #Check for intersection. Both have to be true
            if x_overlap and y_overlap:
                 print("Line found in bounding box: {}".format(index))
                 count+=1

    return count






#results = check_lines_in_file(output_file, 30, 300, fixed_height=3)

