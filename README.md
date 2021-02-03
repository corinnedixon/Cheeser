# Cheeser
Code for the Sm^rt Cheeser for EDGE X

Features
- Adds cheese and shake with varying pump speeds to 7, 10, 12, and 14 inch Donatos pizza.
- Settings and help window for ease of use
- Sends help requests to Firebase

Setup & Installation
1. Install Raspbian to Raspberry Pi (any version)
2. Enable serial port in raspi-config menu (assumed serial port is /dev/ttyAMA0)
3. Disable screen blanking in rasp-config menu
4. Clone this repository onto the Pi $ git clone https://github.com/corinnedixon/Cheeser
5. Run $ pip3 install pyfireconnect (for firebase connection in Python 3)
6. Run $ sudo apt-get install python3-pil.imagetk (for images in Python 3)

Usage & Details
Code runs with 3 Stepper Motors and 1 DC Motor. Ports can be adjusted in each code file. Timing and speeds can also be adjusted under variable declaration section of the files.
