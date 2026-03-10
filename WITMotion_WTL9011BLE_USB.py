#!/usr/bin/env python3
# Description: A flexible, long-term logging script that saves data in hourly CSV files,
#              organized into daily subdirectories.

import serial
import struct
import csv
import time
import os
from datetime import datetime

# --- Configuration ---
PORT = '/dev/ttyACM0' 
BAUDRATE = 115200

# --- Logging Mode Configuration ---
# Set to True for continuous logging (runs until you press Ctrl+C).
# Set to False for a timed run.
CONTINUOUS_LOGGING = True 

# Duration in seconds for a timed run (only used if CONTINUOUS_LOGGING is False).
LOGGING_DURATION_SECONDS = 7250 # e.g., 2 hours + 50 seconds

# --- Data Rate Configuration ---
RETURN_RATE_HZ = 200 # Options: 0.1, 0.5, 1, 2, 5, 10, 20, 50, 100, 200
BANDWIDTH_HZ = 256   # Options: 256, 188, 98, 42, 20, 10, 5

# --- Protocol Commands and Maps (Do not change) ---
CMD_UNLOCK = bytearray([0xFF, 0xAA, 0x69, 0x88, 0xB5])
CMD_SAVE_CONFIG = bytearray([0xFF, 0xAA, 0x00, 0x00, 0x00])
RATE_MAP = { 0.1:0x01, 0.5:0x02, 1:0x03, 2:0x04, 5:0x05, 10:0x06, 20:0x07, 50:0x08, 100:0x09, 200:0x0B }
BANDWIDTH_MAP = { 256:0x00, 188:0x01, 98:0x02, 42:0x03, 20:0x04, 10:0x05, 5:0x06 }
serial_buffer = bytearray()

def send_config_command(ser, command, description):
    """Sends a 3-step (Unlock, Command, Save) configuration sequence."""
    print(f"Configuring sensor: {description}...")
    try:
        ser.write(CMD_UNLOCK)
        time.sleep(0.1)
        ser.write(command)
        time.sleep(0.1)
        ser.write(CMD_SAVE_CONFIG)
        time.sleep(0.1)
        print(f"✅ {description} configured successfully.")
    except Exception as e:
        print(f"❌ Failed to configure {description}: {e}")

def main():
    """Main function to connect, log data, and rotate log files hourly."""
    global serial_buffer
    
    current_log_file = None
    csv_writer = None
    current_file_hour = -1
    
    ser = None
    try:
        ser = serial.Serial(PORT, BAUDRATE, timeout=0.01)
        
        if RETURN_RATE_HZ in RATE_MAP:
            cmd_set_rate = bytearray([0xFF, 0xAA, 0x03, RATE_MAP[RETURN_RATE_HZ], 0x00])
            send_config_command(ser, cmd_set_rate, f"Set Return Rate to {RETURN_RATE_HZ}Hz")
        
        if BANDWIDTH_HZ in BANDWIDTH_MAP:
            cmd_set_bw = bytearray([0xFF, 0xAA, 0x1F, BANDWIDTH_MAP[BANDWIDTH_HZ], 0x00])
            send_config_command(ser, cmd_set_bw, f"Set Bandwidth to {BANDWIDTH_HZ}Hz")

        if CONTINUOUS_LOGGING:
            print("\n✅ Starting continuous logging. Press Ctrl+C to stop.")
        else:
            print(f"\n✅ Starting timed logging for {LOGGING_DURATION_SECONDS} seconds.")
        
        ser.reset_input_buffer()
        start_time = time.time()
        
        while True:
            # Check stop condition for timed logging
            if not CONTINUOUS_LOGGING:
                if time.time() - start_time >= LOGGING_DURATION_SECONDS:
                    print("\n--- Logging duration complete. ---")
                    break # Exit the loop
            
            now = datetime.now()
            
            # This block now creates daily folders and hourly files
            if now.hour != current_file_hour:
                if current_log_file and not current_log_file.closed:
                    current_log_file.close()
                    print(f"Closed log file for hour {current_file_hour}.")

                # --- MODIFIED SECTION START ---
                # 1. Create a formatted date string for the daily folder name (e.g., "2025-10-13")
                date_str = now.strftime('%Y-%m-%d-WTDCL')
                
                # 2. Define the path for the new daily directory
                log_dir = os.path.join("WitMotionSensor_Logs", date_str)
                
                # 3. Create the directory (and the parent "sensor_logs" if needed).
                #    The 'exist_ok=True' prevents errors if the folder already exists.
                os.makedirs(log_dir, exist_ok=True)
                
                # 4. Create the full path for the new hourly CSV file inside the daily folder.
                filename = os.path.join(log_dir, f"usb_log_{now.strftime('%Y-%m-%d_%H')}.csv")
                # --- MODIFIED SECTION END ---
                
                current_log_file = open(filename, 'w', newline='')
                csv_writer = csv.writer(current_log_file)
                header = ["Timestamp", "Roll", "Pitch", "Yaw", "AccelX", "AccelY", "AccelZ", "GyroX", "GyroY", "GyroZ"]
                csv_writer.writerow(header)
                
                current_file_hour = now.hour
                print(f"Opened new log file for hour {current_file_hour}: {filename}")
            
            bytes_waiting = ser.in_waiting
            if bytes_waiting > 0:
                serial_buffer.extend(ser.read(bytes_waiting))

            while True:
                start_index = serial_buffer.find(b'\x55\x61')
                if start_index == -1 or len(serial_buffer) < start_index + 20:
                    break
                
                packet = serial_buffer[start_index : start_index + 20]
                try:
                    ax_r, ay_r, az_r, wx_r, wy_r, wz_r, roll_r, pitch_r, yaw_r = struct.unpack_from('<hhhhhhhhh', packet, 2)
                    
                    angle_scale, accel_scale, gyro_scale = 180.0/32768.0, 16.0/32768.0, 2000.0/32768.0
                    r,p,y = roll_r*angle_scale, pitch_r*angle_scale, yaw_r*angle_scale
                    ax,ay,az = ax_r*accel_scale, ay_r*accel_scale, az_r*accel_scale
                    wx,wy,wz = wx_r*gyro_scale, wy_r*gyro_scale, wz_r*gyro_scale
                    
                    timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                    csv_writer.writerow([timestamp_str, f"{r:.3f}",f"{p:.3f}",f"{y:.3f}",f"{ax:.4f}",f"{ay:.4f}",f"{az:.4f}",f"{wx:.4f}",f"{wy:.4f}",f"{wz:.4f}"])
                except (struct.error, TypeError):
                    pass
                
                serial_buffer = serial_buffer[start_index + 20:]
            
            # A small sleep helps prevent the loop from consuming 100% CPU
            # if no data is available. Adjust as needed.
            time.sleep(0.001)

    except serial.SerialException as e:
        print(f"❌ ERROR: Could not open port {PORT}. {e}")
    except KeyboardInterrupt:
        print("\n--- Program stopped by user. ---")
    finally:
        if ser and ser.is_open:
            ser.close()
        if current_log_file and not current_log_file.closed:
            current_log_file.close()
            print("Final log file closed.")

if __name__ == "__main__":
    main()