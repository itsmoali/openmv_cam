import time
import sensor
from pyb import USB_VCP

# Initialize the USB VCP object
usb = USB_VCP()

# --- SENSOR INITIALIZATION ---
sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time = 2000)
# ---------------------------

def take():
    img =sensor.snapshot()
    img.save("new.jpg")
# Example: Continuously check for and process incoming data
while True:
    if usb.isconnected():
        if usb.any(): # Check if any data is waiting to be read
            # Read all available data
            data = usb.read()

            # Decode the received bytes into a string
            command = data.decode().strip()

            print("Received command:", command)

            if command == "SNAPSHOT":
                # START OF TRY BLOCK
                try:
                    img = sensor.snapshot()
                    img.save("UART.jpg")
                    take()

                    time.sleep(1)

                    print("Image saved as UART.jpg") # Print a confirmation
                    usb.write("OK\r\n".encode()) # Send an acknowledgment back

                # END OF TRY BLOCK, START OF EXCEPT BLOCK
                except Exception as e:
                    # An error occurred (e.g., no space, file system issue)
                    error_message = f"SAVE FAILED: {e}"
                    print(error_message)
                    usb.write(f"ERROR: {e}\r\n".encode())

            elif command == "STOP":
                # Stop a process
                # ...
                usb.write("STOPPED\r\n".encode())

    time.sleep_ms(100)
