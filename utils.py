import os
import time
import sensor

# -----------------------------------------------------------------------------
# This module provides functions for file I/O (logging and configuration)

#
# Functions Summary:
# 1. log(log_file, message, function_name)
# 2. load_env(file_path, logs)
# 3. take_image(grayscale, resolution)
# -----------------------------------------------------------------------------



# -----------------------------------------------------------------------------
# Logging Function
# -----------------------------------------------------------------------------

def log(log_file, message, function_name="N/A"):
    """

    Logs a message to a file, optimized for MicroPython/OpenMV.

    Args:
        log_file (str): Path to the log file (e.g., "log.txt").
        message (str): The message content to log.
        function_name (str, optional): The name of the function calling the log.
    """

    try:
        current_time = time.localtime()
        date_time_str = time.strftime("%Y-%m-%d %H:%M:%S", current_time)
        with open(log_file, 'a') as file:
            log_entry = (
                f"{date_time_str}\n"
                f"Function: {function_name}\n"
                f"Result: {message}\n"
                f"\n\n")
            file.write(log_entry)
        file.close()

        print(f"Logged message to {log_file}")
    except Exception as e:
        print(f"Failed to log message: {e}")
        raise RuntimeError(f"Failed to log message: {e}")

#---------USAGE-----------
#log_file = "test_log.txt"
#result = ["Image 1: Coordinates (x1, y1, x2, y2)"]
#log(log_file, res, "Check Image coordinates")

# -----------------------------------------------------------------------------
# Loading Environment Varaibles for dividing the image
# -----------------------------------------------------------------------------

def load_env(file_path, logs=None):
    """
    Loads environment variables from a file, skipping comments and empty lines.

    Args:
        file_path: The path to the environment file (e.g., '.env').
        logs: Optional logger function to log messages.

    Returns:
        A dictionary containing the loaded environment variables.
        {Directional key: piexl value}
    """
    variables = {}

    try:
        with open(file_path, 'r') as file:
            for line in file:
                # Remove whitespace
                line = line.strip()
                # Skip comments
                if not line or line.startswith('#'):
                    continue
                # Ensure the line is in key=value format
                if '=' in line:
                    # Use partition instead of split for slight efficiency and robustness
                    key, _, value = line.partition('=')

                    # Store the key-value pair, trimming whitespace from both
                    variables[key.strip()] = value.strip()
        if logs:
            log("logs.txt", message=variables, function_name="load_env")
        return variables
    except OSError as e:
        # MicroPython uses OSError instead of FileNotFoundError
        # Handle the common case specifically for a better error message
        raise RuntimeError(
            f"Failed to load environment variables: File not found at {file_path}: {e}")
    except Exception as e:
        # Catch other unexpected errors
        raise RuntimeError(
            f"Failed to load environment variables from {file_path}: {e}")

#---------USAGE-----------
#res = load_env("env.txt", logs = None)
#print(res)


# -----------------------------------------------------------------------------
# Camera Control Function
# -----------------------------------------------------------------------------

# NOTE: take_image() removed - use take_img.take_image() instead
# This function had sensor.reset() which violates OpenMV library rules
#---------USAGE-----------
#take_image()


