# Please Note
Connect the sensor via USB and the dongle to a windows PC. Use the Witmotion software to bind the dongle to the sensor then follow the steps below!

# Raspberry Pi Setup

1.	Connect the USB Dongle and sensor to the Pi using the provided USB-c to USB-A cable
 
2.	Update the system

sudo apt update
sudo apt upgrade -y

3.	Install system dependencies

sudo apt install pyserial

4.	Create an environment if one doesn’t exist

# Navigate to project directory
cd path/to/project
# Create Virtual environment (replace name below with env name)
python3 -m venv name
# Activate the environment
source name/bin/activate

5.	Identify the serial port

Before connecting the USB
ls /dev/tty*
output: list of all serial devices recognized by the system
After connecting the USB run the same command again
ls /dev/tty*
output: /dev/ttyACM0 or /dev/ttyUSB0
Change the port in the code if needed 
#From this:
PORT = ‘/dev/ttyACM0’
#To this:
PORT = ‘/dev/ttyUSB0’


6.	Save the code inside the project directory

7.	Run the script from the command line


# Make sure you are inside the correct project directory and environment
python log_all_witsensor_data_USB_V4.py
