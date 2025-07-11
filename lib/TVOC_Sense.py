# *****************************************************************************
# * | File        :   tvoc_sense.py
# * | Author      :   Waveshare team
# * | Function    :   TVOC sensor driver function
# * | Info        :
# *----------------
# * | This version:   V1.0
# * | Date        :   2025-03-13
# * | Info        :   
# ******************************************************************************

"""
This script provides a Python class to interface with TVOC sensors using UART communication.
It supports both active and query modes for data retrieval.
"""

import serial
from time import sleep
from gpiozero import LED, Button

# Create a list with 11 members to store received data from the TVOC sensor
TVOC_rx_buf = [0] * 11

# Command buffers for setting sensor modes and querying data
TVOC_active_buf = [0xFE, 0x00, 0x78, 0x40, 0x00, 0x00, 0x00, 0x00, 0xB8]  # Command to set active mode
TVOC_stop_active_buf = [0xFE, 0x00, 0x78, 0x41, 0x00, 0x00, 0x00, 0x00, 0xB9]  # Command to set query mode
TVOC_get_query_buf = [0xFE, 0x00, 0x86, 0x00, 0x00, 0x00, 0x00, 0x00, 0x86]  # Command to query data in query mode


class TVOC_Sense:
    """
    A class to interface with TVOC sensors using UART communication.
    This class supports both active and query modes for data retrieval.
    """

    def __init__(self, dev='/dev/ttyS0', baud=115200):
        """
        Initialize the TVOC sensor interface.

        :param dev: Serial port device path (default: /dev/ttyS0)
        :param baud: Baud rate for UART communication (default: 115200)
        """
        # Initialize reset and alarm pins
        self.alm = Button(17)  # Alarm pin as input

        self.count_i = 0  # Loop count variable
        self.check_sum = 0  # Checksum variable

        # Initialize UART communication
        self.ser = serial.Serial(dev, baud)
        self.ser.flushInput()  # Clear the serial port input register

    def CRC_Check(self, Data, Size):
        """
        Calculate the checksum of the received data.

        :param Data: List of received bytes
        :param Size: Number of bytes to include in checksum calculation
        :return: Calculated checksum
        """
        buf_crc = [0] * 8  # Buffer to store data for checksum calculation

        if Size == 6:
            for i in range(3, 9):
                buf_crc[i - 3] = Data[i]
        else:
            for i in range(1, 8):
                buf_crc[i - 1] = Data[i]

        CrC = 0
        for Count in range(Size):
            CrC += buf_crc[Count]

        return CrC

    def TVOC_Get_Active_Device_Data(self):
        """
        Retrieve data from the TVOC sensor in active mode.
        This function continuously reads data from the sensor and verifies its integrity using checksum.
        """
        if self.ser.inWaiting() > 0:  # Check if data is available in the serial buffer
            self.TOF_peek = ord(self.ser.read(1))  # Read a byte and convert it to an integer
            if self.TOF_peek == 0xFE:  # If it is a frame header, restart the loop count
                self.count_i = 0
                TVOC_rx_buf[self.count_i] = self.TOF_peek  # Store the read data into the buffer
            else:
                TVOC_rx_buf[self.count_i] = self.TOF_peek  # Store the read data into the buffer

            self.count_i += 1  # Increment loop count

            if self.count_i > 10:  # If the number of received data exceeds 10, perform decoding
                self.count_i = 0
                self.check_sum = self.CRC_Check(TVOC_rx_buf, 6) & 0xFF  # Calculate checksum

                # Verify checksum and extract sensor data
                if self.check_sum == TVOC_rx_buf[9]:
                    co2 = (TVOC_rx_buf[3] * 256) + TVOC_rx_buf[4]  # Combine two bytes to get CO2 value
                    ch2o = (TVOC_rx_buf[5] * 256) + TVOC_rx_buf[6]  # Combine two bytes to get formaldehyde (CH2O) value
                    tvoc = ((TVOC_rx_buf[7] * 256) + TVOC_rx_buf[8]) / 1000.0  # Combine two bytes and convert to TVOC value

                    # Check if the alarm pin is triggered (TVOC exceeds 2ppm)
                    if self.alm.is_pressed:
                        print("TVOC has exceeded 2ppm")

                    print("AIR = %d " % TVOC_rx_buf[1], "CO2 = %d ppm " % co2, "CH2O = %d ppb " % ch2o, "TVOC = %0.3f ppm" % tvoc)
                    self.ser.flushInput()  # Clear the serial port input register
                else:
                    print("Verification failed.")
                self.check_sum = 0  # Clear checksum

    def TVOC_Set_Device_Active_Mode(self):
        """
        Set the TVOC sensor to active mode.
        In active mode, the sensor continuously sends data without needing a query.
        """
        self.ser.write(bytearray(TVOC_active_buf))  # Send command to set active mode

    def TVOC_Set_Device_Query_Mode(self):
        """
        Set the TVOC sensor to query mode.
        In query mode, the sensor only sends data when explicitly requested.
        """
        self.ser.write(bytearray(TVOC_stop_active_buf))  # Send command to set query mode

    def TVOC_Get_Query_Device_Data(self):
        """
        Retrieve data from the TVOC sensor in query mode.
        This function sends a query command and reads the response from the sensor.
        """
        self.ser.flushInput()  # Clear the serial port buffer
        self.ser.write(bytearray(TVOC_get_query_buf))  # Send query command
        sleep(0.015)  # Wait for sensor response

        if self.ser.inWaiting() != 0:
            TVOC_rx_buf = list(self.ser.read(11))  # Read sensor data into buffer
            if len(TVOC_rx_buf) > 9:
                self.check_sum = self.CRC_Check(TVOC_rx_buf, 6) & 0xFF  # Calculate checksum

            # Verify checksum and extract sensor data
            if self.check_sum == TVOC_rx_buf[9]:
                tvoc = ((TVOC_rx_buf[5] * 256) + TVOC_rx_buf[6]) / 1000.0
                adc = (TVOC_rx_buf[7] * 256) + TVOC_rx_buf[8]

                # Check if the alarm pin is triggered (TVOC exceeds 2ppm)
                if self.alm.is_pressed:
                    print("TVOC has exceeded 2ppm")

                print("ADC =", adc, "TVOC = %0.3fppm" % tvoc)
            else:
                print("Verification failed.")
            self.check_sum = 0  # Clear checksum