import time
import os

def logging(log_file, message, function_name=None):
    current_time = time.localtime()

    date_time_str = time.strftime("%Y-%m-%d , %H:%M:%S", current_time)
    try:
        with open(log_file, 'a') as file:
            log_entry = (
                f"{date_time_str}\n"  # Date , time
                f"Function: {function_name}\n"  # Function name:
                f"Result: {message}\n"            # Message
                f"\n\n")                           # 2 line spaces
            file.write(log_entry)
        print(f"Logged message to {log_file}")
        return
    except Exception as e:
        print(f"Failed to log message: {e}")
        raise RuntimeError(f"Failed to log message: {e}")





def load_env(file_path, logs=None):

    try:
        variables = {}
        with open(file_path, 'r') as file:
            for line in file:
                key, value = line.strip().split('=', 1)
                variables[key] = value
        file.close()
        if logs:
            logging("logs.txt", message=variables, function_name="load_env")

        return variables
    except Exception as e:
        raise RuntimeError(f"Failed to load environment variables: {e}")


#print(load_env("env.txt"))


