# ENV loader - By: moali - Thu Oct 23 2025

import sensor
import time
import os

# Loads the environment variables for the roi regions from a config file
def load_config(file_path):
    config = {}
    try:
        with open(file_path , 'r') as f:
            for line in f:
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = int(value.strip())
    except Exception as e:
        print("Error loading config:", e)
    return config

