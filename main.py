#coding: UTF-8
import sys 
from time import sleep
from lib import TVOC_Sense

# Function to detect the Raspberry Pi model
def detect_model():
    """
    Detects the Raspberry Pi model by reading the device tree model file.
    
    Returns:
        str: The model string of the Raspberry Pi.
    """
    with open('/proc/device-tree/model') as f:  # Open the device tree model file
        model = f.read().strip()  # Read and strip the model string
    return model

# Detect the Raspberry Pi model and initialize the TOF_Sense object with the appropriate serial port
if "Raspberry Pi 5" in detect_model() or "Raspberry Pi Compute Module 5" in detect_model():  # Check if the model is Raspberry Pi 5
    tvoc = TVOC_Sense.TVOC_Sense('/dev/ttyAMA0', 115200)  # Initialize TOF_Sense with ttyAMA0 for Raspberry Pi 5
else:
    tvoc = TVOC_Sense.TVOC_Sense('/dev/ttyS0', 115200)  # Initialize TOF_Sense with ttyS0 for other models
  
def tvoc_active_print():
    """
    Function to print TVOC sensor data in active mode.
    In active mode, the sensor continuously sends data without needing a query.
    This function sets the sensor to active mode and continuously reads and prints the data.
    """
    tvoc.TVOC_Set_Device_Active_Mode()  # Set sensor to active mode
    while True:
        tvoc.TVOC_Get_Active_Device_Data()  # Retrieve and print data in active mode
        sleep(0.02)  # Short delay to handle incoming data (20ms)

def tvoc_query_print():
    """
    Function to print TVOC sensor data in query mode.
    In query mode, the sensor only sends data when explicitly requested.
    This function sets the sensor to query mode and periodically requests and prints the data.
    """
    tvoc.TVOC_Set_Device_Query_Mode()  # Set sensor to query mode
    while True:
        tvoc.TVOC_Get_Query_Device_Data()  # Request and print data in query mode
        sleep(1)  # Delay between queries (1 second)
try:
    # tvoc_active_print()  # Uncomment to use active mode
    tvoc_query_print()  # Uncomment to use query mode

except KeyboardInterrupt:
    print("Quit.")    
        
    





