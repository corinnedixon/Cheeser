import datetime
import math
import os
import PIL.Image
import PIL.ImageTk
import pyfireconnect
import RPi.GPIO as GPIO
import serial
import sys
import threading
import time
from tkinter import *
import tkinter.font as font
import urllib.request

#**************************************FIREBASE SET UP**************************************

#Check for internet connection
hasInternet = False

#def checkInternet():
#  internet = True
#  try:
#    urllib.request.urlopen('https://INSERT.firebaseio.com/')
#  except:
#    internet = False
#  return internet
#
#time.sleep(1)
#hasInternet = checkInternet()
#
##Set timezone
#os.environ['TZ'] = 'US/Eastern'
#time.tzset()
#
##pyfire set up if internet is connected
#if(hasInternet):
#  config = {
#    "apiKey" : "INSERT",
#    "authDomain" : "INSERT.firebaseapp.com",
#    "databaseURL" : "https://INSERT.firebaseio.com/",
#    "storageBucket" : "INSERT.appspot.com"
#  }
#
#  firebase = pyfireconnect.initialize(config)
#  db = firebase.database()

#***********************************VARIABLE DECLARATIONS***********************************

# Color variables for consistency
main_bg = "#FFFFFF" #switched from gray20
button_color = "#CCCDD0" #switched from gray20
donatos_path = "Saucer/donatos.png" #switched from white
main_fg = "#000000" #switched from FFFFFF

# Light, normal, extra sauce speeds
lt = 0.75
med = 1
ext = 1.25

# Size calibrations from file
with open('Saucer/diagnostics.txt', 'r') as reader:
        calibs = reader.read().splitlines()

global calibration
calibration = {7: int(calibs[7]), 10: int(calibs[8]), 12: int(calibs[9]), 14: int(calibs[10])}

# Motor speed
global s1_speed, s2_speed, s3_speed, s4_speed
global motor1speeds, motor2speeds, motor3speeds, motor4speeds

motor1speeds = {7:3500, 10:3500, 12:3500, 14:3600} # Sauce motor 1 speed
motor2speeds = {7:0, 10:3200, 12:3200, 14:2500} # Sauce motor 2 speed
motor3speeds = {7:0, 10:0, 12:1700, 14:1700} # Sauce motor 3 speed
motor4speeds = {7:0, 10:0, 12:0, 14:1700} # Sauce motor 4 speed

clean_prime_speed = 2000 # Sauce motor speed when cleaning and priming

# Size / Steps / Sauce Amount
global size
size = -1 # No default size
global cheese_spin_steps
sauce_spin_steps = 1000
global amount
amount = med # default amount at start is medium

# Variable for total machine time
global totalTime
totalTime = time.time()

# Variables for emergency stop
global shutdown
shutdown = False
global running
running = False

#***************************************MOTOR SET UP****************************************

#FIX THIS LATER !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

# Sauce stepper motor set up (pumps)
S1_DIR = 36   # Direction GPIO Pin
S1_STEP = 38  # Step GPIO Pin
S2_DIR = 31   # Direction GPIO Pin
S2_STEP = 33  # Step GPIO Pin
S3_DIR = 29   # Direction GPIO Pin
S3_STEP = 32  # Step GPIO Pin
S4_DIR = 21   # Direction GPIO Pin
S4_STEP = 23  # Step GPIO Pin

GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)
GPIO.setup(S1_DIR, GPIO.OUT)
GPIO.setup(S1_STEP, GPIO.OUT)
GPIO.setup(S2_DIR, GPIO.OUT)
GPIO.setup(S2_STEP, GPIO.OUT)
GPIO.setup(S3_DIR, GPIO.OUT)
GPIO.setup(S3_STEP, GPIO.OUT)
GPIO.setup(S4_DIR, GPIO.OUT)
GPIO.setup(S4_STEP, GPIO.OUT)

# Big stepper motor set up (spins)
T6_DIR = 13   # Direction GPIO Pin
T6_STEP = 15  # Step GPIO Pin

GPIO.setup(T6_DIR, GPIO.OUT)
GPIO.setup(T6_STEP, GPIO.OUT)

#*************************************BUTTON FUNCTIONS**************************************

# Function used for size double click
def setSize(button, new_size):
    global size
    size = new_size
    runCheeser(button)

# Function for stop button
def emergencyStop():
    global shutdown
    shutdown = True

#************************************CHEESER FUNCTIONS***************************************

#CHECK FUNCTIONALITY HERE !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

#Function for running saucer
def runCheeser():
    print("SPEED: " + str(amount*speed[size]))
    print("SIZE: " + str(size))
    print("RUNNING CHEESE\n")
    
    pizzaTime = time.time()
    
    # Run corresponding saucer pumps
    cheeseProgram(size)
    spinFunc(25, cheese_spin_steps)
    stopCheesing()
    stopSpinning()
    
    # Set amount to default
    setAmount(med)
    
    # Update diagnostics
    pizzaTime = time.time() - pizzaTime
    updateDiagnostics(pizzaTime)

#Functions for starting and stopping spin
def spinProgram(speed):
    # Create new thread
    spin = threading.Thread(target=spinFunc, args=(speed,1,))
    # Start new thread
    spin.start()

def spinFunc(speed, steps):
  global spinning  #create global
  spinning = True
  
  spin_delay = (100-speed)/50000
  while spinning and steps > 0:
    if spinning == False:
      break
    else:
      GPIO.output(T6_STEP, GPIO.HIGH)
      time.sleep(spin_delay)
      GPIO.output(T6_STEP, GPIO.LOW)
      time.sleep(spin_delay)
      steps = steps - 1

def stopSpinning():
  global spinning
  spinning = False
  GPIO.output(T6_STEP, GPIO.LOW)

#Functions for starting and stopping sauce
def cheeseProgram(size):
    global amount

    # Create new threads
    pump1 = threading.Thread(target=pumpFunc, args = (S1_STEP, amount*speed[size],))
    pump2 = threading.Thread(target=pumpFunc, args = (S2_STEP, amount*speed[size],))
    pump3 = threading.Thread(target=pumpFunc, args = (S3_STEP, amount*speed[size],))
    pump4 = threading.Thread(target=pumpFunc, args = (S4_STEP, amount*speed[size],))
    
    # Start new thread
    pump1.start()
    if size >= 10:
        pump2.start()
    if size >= 12:
        pump3.start()
    if size >= 14:
        pump4.start()
    
def cheeseFunc(motor_pin, speed):
  global cheesing  #create global
  cheesing = True
    
  while cheesing:
    if cheesing == False:
      break
    else:
      delay = (126-speed)/40000
      GPIO.output(motor_pin, GPIO.HIGH)
      time.sleep(delay)
      GPIO.output(motor_pin, GPIO.LOW)
      time.sleep(delay)

def stopCheesing():
  global cheesing
  cheesing = False

#**************************************CLEAN AND PRIME**************************************
   
# Function to clean
def clean(button):
    # Set shutdown variable to false since we are running
    global running
    global shutdown
    shutdown = False
    
    if(not running):
        # Start clean program thread
        c = threading.Thread(target=cleanProgram, args=(button,))
        c.start()

# Function used in clean thread
def cleanProgram(button):
    print("Cleaning\n")
    
    # Set running variable to true since we are cleaning
    global running
    running = True
    button['bg'] = "gray60"
    
    global shutdown, clean_prime_speed
    cleanTime = time.time()

    # Pump for 2 minutes
    pump1 = threading.Thread(target=pumpFunc, args = (S1_STEP, clean_prime_speed))
    pump2 = threading.Thread(target=pumpFunc, args = (S2_STEP, clean_prime_speed))
    pump3 = threading.Thread(target=pumpFunc, args = (S3_STEP, clean_prime_speed))
    pump4 = threading.Thread(target=pumpFunc, args = (S4_STEP, clean_prime_speed))
    
    # Start new thread
    pump1.start()
    pump2.start()
    pump3.start()
    pump4.start()
        
    while((not shutdown) and (time.time()-cleanTime < 120)):
        button['text'] = int(120-(time.time()-cleanTime))
    
    # Update running - cleaning is done
    running = False
    button['bg'] = button_color
    button['text'] = "CLEAN"

# Function to prime
def prime(button):
    # Set shutdown variable to false since we are running
    global running
    global shutdown
    shutdown = False
    
    if(not running):
        # Start clean program thread
        p = threading.Thread(target=primeProgram, args=(button,))
        p.start()
        
# Function used in prime thread
def primeProgram(button):
    print("Priming\n")
        
    # Set running variable to true since we are priming
    global running
    running = True
    button['bg'] = "gray60"
    
    global shutdown, clean_prime_speed
    primeTime = time.time()

    # Pump for 30 seconds
    pump1 = threading.Thread(target=pumpFunc, args = (S1_STEP, clean_prime_speed))
    pump2 = threading.Thread(target=pumpFunc, args = (S2_STEP, clean_prime_speed))
    pump3 = threading.Thread(target=pumpFunc, args = (S3_STEP, clean_prime_speed))
    pump4 = threading.Thread(target=pumpFunc, args = (S4_STEP, clean_prime_speed))
    
    # Start new thread
    pump1.start()
    pump2.start()
    pump3.start()
    pump4.start()
    
    while((not shutdown) and (time.time()-primeTime < 30)):
        button['text'] = int(30-(time.time()-primeTime))
    
    # Update running - priming is done
    running = False
    button['bg'] = button_color
    button['text'] = "PRIME"

#*************************************CHANGE CHEESE AMT**************************************

def setSpeeds(sz, amt):
    # Calculate calibration constant
    cal = math.sqrt((150 - calibration[sz])/100)
        
    # Assign speeds to each motor (corresponding speed x calibration percent x extra/normal/less)
    global s1_speed, s2_speed, s3_speed, s4_speed
    s1_speed = int(motor1speeds[sz]*cal*amt) # Sauce stepper motor 1 speed
    s2_speed = int(motor2speeds[sz]*cal*amt) # Sauce stepper motor 2 speed
    s3_speed = int(motor3speeds[sz]*cal*amt) # Sauce stepper motor 3 speed
    s4_speed = int(motor4speeds[sz]*cal*amt) # Sauce stepper motor 4 speed

# Functions for setting pump amount as percentage of speeds and colors of buttons
def setColor(color):
    fourteenButton["bg"] = color
    twelveButton["bg"] = color
    tenButton["bg"] = color
    sevenButton["bg"] = color

def setAmount(amt):
    global amount, speed
    if amt == amount or amt == med:
        amount = med
        setColor("lime green")
        light["bg"] = button_color
        extra["bg"] = button_color
    elif amt == lt:
        amount = lt
        setColor("orange")
        light["bg"] = "orange"
        extra["bg"] = button_color
    elif amt == ext:
        amount = ext
        setColor("DarkOrange2")
        light["bg"] = button_color
        extra["bg"] = "DarkOrange2"

#********************************CALIBRATION / DIAGNOSTICS**********************************

# Functions for adding and subtracting from saucer pump speed during calibration
def add(size, speedVar):
    if(speed[size] < 100):
        speed[size] = speed[size] + 5
        speedVar.set(speed[size])

def subtract(size, speedVar):
    if(speed[size] > 0):
        speed[size] = speed[size] - 5
        speedVar.set(speed[size])

# Function for updating diagnostics
def updateDiagnostics(pizzaTime):
    # Get current data
    with open('Cheeser/diagnostics.txt', 'r') as reader:
        diags = reader.read().splitlines()
        
    # Update data
    global totalTime
    diags[0] = str(int(diags[0]) + int((time.time() - totalTime)/60))
    diags[1] = str(int(diags[1]) + 1)
    if(int(diags[2]) == 0):
        diags[2] = str(int(pizzaTime))
    else:
        diags[2] = str(int((int(diags[2]) + pizzaTime)/2))
    
    # Set data in file
    with open('Cheeser/diagnostics.txt', 'w') as writer:
        for data in diags:
            writer.write("%s\n" % data)
        

#*****************************************HELP MENU*****************************************

# Function for changing button text based on answer
def change(button):
    if button['text'] == "NO":
        button['bg'] = "PaleGreen1"
        button['text'] = "YES"
    else:
        button['bg'] = "IndianRed2"
        button['text'] = "NO"

# Function for sending sos menu data to Firebase
def send(answers, menu):
    str = "Answers:"
    for button in answers:
        str = str + " " + button['text']
    if(hasInternet):
      db.push(str)
    print(str)
    print("Sending data to Firebase")
    
        # Pop up then exit
    msg = StringVar()
    msg.set("FORM SUBMITTED\nIn an emergency,\nplease call 614-226-4421.\n")
    smallFont = font.Font(family='Helvetica', size=20, weight='normal')
    text = Label(menu, font=smallFont, textvariable=msg, bg = "light green", bd=4, relief="groove", fg="black", height=7, width=35)
    text.place(x=130, y=120)
    menu.update()
    ok = Button(menu, text = "OK", font = smallFont, fg= main_fg, bg = button_color, command = menu.destroy)
    ok.place(x=365, y=278)

# Function for sos menu
def sos():
    # Create window for help menu
    sosMenu = Toplevel()
    sosMenu.title("Cheeser Help Menu")
    sosMenu.geometry('800x480')
    sosMenu.configure(bg=main_bg)
    sosMenu.overrideredirect(1)
    
    # Fonts
    otherFont = font.Font(family='Helvetica', size=24, weight='normal')
    questionFont = font.Font(family='Helvetica', size=14, weight='normal')
    
    # Questions
    q1 = Text(sosMenu, font=questionFont, bg = main_bg, fg = main_fg,  bd = -2, height=1, width=35)
    q1.insert(INSERT, "Is it cheesing the 14 Inch Pizza?")
    q1.place(x=25, y=20)
    
    b1  = Button(sosMenu, text = "NO", font = questionFont, fg="black", bg = "IndianRed2", command = lambda: change(b1), height = 1, width = 2)
    b1.place(x=400, y=20)
    
    q2 = Text(sosMenu, font=questionFont, bg = main_bg, fg = main_fg,  bd = -2, height=1, width=35)
    q2.insert(INSERT, "Is it cheesing the 12 Inch Pizza?")
    q2.place(x=25, y=60)
    
    b2  = Button(sosMenu, text = "NO", font = questionFont, fg="black", bg = "IndianRed2", command = lambda: change(b2), height = 1, width = 2)
    b2.place(x=400, y=60)
    
    q3 = Text(sosMenu, font=questionFont, bg = main_bg, fg = main_fg,  bd = -2, height=1, width=35)
    q3.insert(INSERT, "Is it cheesing the 10 Inch Pizza?")
    q3.place(x=25, y=100)
    
    b3 = Button(sosMenu, text = "NO", font = questionFont, fg="black", bg = "IndianRed2", command = lambda: change(b3), height = 1, width = 2)
    b3.place(x=400, y=100)
    
    q4 = Text(sosMenu, font=questionFont, bg = main_bg, fg = main_fg,  bd = -2, height=1, width=35)
    q4.insert(INSERT, "Is it cheesing the 7 Inch Pizza?")
    q4.place(x=25, y=140)
    
    b4  = Button(sosMenu, text = "NO", font = questionFont, fg="black", bg = "IndianRed2", command = lambda: change(b4), height = 1, width = 2)
    b4.place(x=400, y=140)
    
    q5 = Text(sosMenu, font=questionFont, bg = main_bg, fg = main_fg,  bd = -2, height=1, width=35)
    q5.insert(INSERT, "Are the cheese motors moving?")
    q5.place(x=25, y=180)
    
    b5  = Button(sosMenu, text = "NO", font = questionFont, fg="black", bg = "IndianRed2", command = lambda: change(b5), height = 1, width = 2)
    b5.place(x=400, y=180)
    
    q6 = Text(sosMenu, font=questionFont, bg = main_bg, fg = main_fg,  bd = -2, height=1, width=35)
    q6.insert(INSERT, "Is the turntable motor shaft spinning?")
    q6.place(x=25, y=220)
    
    b6  = Button(sosMenu, text = "NO", font = questionFont, fg="black", bg = "IndianRed2", command = lambda: change(b6), height = 1, width = 2)
    b6.place(x=400, y=220)
    
    q7 = Text(sosMenu, font=questionFont, bg = main_bg, fg = main_fg,  bd = -2, height=1, width=35)
    q7.insert(INSERT, "Is the screen functioning properly?")
    q7.place(x=25, y=260)
    
    b7  = Button(sosMenu, text = "NO", font = questionFont, fg="black", bg = "IndianRed2", command = lambda: change(b7), height = 1, width = 2)
    b7.place(x=400, y=260)
    
    q8 = Text(sosMenu, font=questionFont, bg = main_bg, fg = main_fg,  bd = -2, height=1, width=35)
    q8.insert(INSERT, "Can you hear any grinding noise?")
    q8.place(x=25, y=300)
    
    b8  = Button(sosMenu, text = "NO", font = questionFont, fg="black", bg = "IndianRed2", command = lambda: change(b8), height = 1, width = 2)
    b8.place(x=400, y=300)
    
    q9 = Text(sosMenu, font=questionFont, bg = main_bg, fg = main_fg,  bd = -2, height=1, width=35)
    q9.insert(INSERT, "Can you hear any high pitched noise?")
    q9.place(x=25, y=340)
    
    b9  = Button(sosMenu, text = "NO", font = questionFont, fg="black", bg = "IndianRed2", command = lambda: change(b9), height = 1, width = 2)
    b9.place(x=400, y=340)
    
    q10 = Text(sosMenu, font=questionFont, bg = main_bg, fg = main_fg,  bd = -2, height=1, width=35)
    q10.insert(INSERT, "Did this problem just start?")
    q10.place(x=25, y=380)
    
    b10  = Button(sosMenu, text = "NO", font = questionFont, fg="black", bg = "IndianRed2", command = lambda: change(b10), height = 1, width = 2)
    b10.place(x=400, y=380)
    
    answers = [b1,b2,b3,b4,b5,b6,b7,b8,b9,b10]
    
    # Back button
    done  = Button(sosMenu, text = "SUBMIT FORM", font = otherFont, bg = button_color, fg = main_fg, command = lambda: send(answers, sosMenu), height = 2, width = 12)
    done.place(x=540, y=50)
    back  = Button(sosMenu, text = "BACK", font = otherFont, bg = button_color, fg = main_fg, command = sosMenu.destroy, height = 2, width = 6)
    back.place(x=650, y=380)

    print("SOS\n")

#***********************************OTHER SCREEN SET UP*************************************

#STOPPED HERE !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

# Function setting up ... screen with various helpful features
def moreScreen():
    global speed
    
    # Create window for more menu
    other = Toplevel()
    other.title("Cheeser Other Screen")
    other.geometry('800x480')
    other.configure(bg=main_bg)
    other.overrideredirect(1)
    
    # Fonts for screen
    stopFont = font.Font(family='Helvetica', size=50, weight='bold')
    otherFont = font.Font(family='Helvetica', size=24, weight='normal')
    headingFont = font.Font(family='Helvetica', size=20, weight='normal')
    calibFont = font.Font(family='Helvetica', size=30, weight='normal')
    diagFont = font.Font(family='Helvetica', size=19, weight='normal')
    
    # Other screen buttons
    helpButton  = Button(other, text = "HELP", font = stopFont, bg = "red2", fg = "#FFFFFF", command = sos, height = 1, width = 8)
    helpButton.place(x=460, y=20)
    home  = Button(other, text = "HOME", font = otherFont, bg = button_color, fg = main_fg, command = other.destroy, height = 2, width = 10)
    home.place(x=575, y=380)
    
    #TEMPORARY QUIT
    quitButton  = Button(other, text = "QUIT", font = otherFont, bg = button_color, fg = main_fg, command = screen.destroy, height = 2, width = 10)
    quitButton.place(x=300, y=10)
    
    # Machine diagnostics
    diag = Text(other, font = headingFont, bd = -2, bg = button_color, fg = main_fg, height=1, width=21)
    diag.insert(INSERT, "MACHINE DIAGNOSTICS")
    diag.place(x=460,y=125)
    
    # Read data from file
    with open('Cheeser/diagnostics.txt', 'r') as reader:
        diags = reader.read().splitlines()
    
    hours = Text(other, font = diagFont, bd = -2, bg = "gray20", fg = "white", height=1, width=37)
    hours.insert(INSERT, "Total Machine Hours.........." + str(int(int(diags[0])/60)))
    hours.place(x=460,y=170)
    sauced = Text(other, font = diagFont, bd = -2, bg = "gray20", fg = "white", height=1, width=37)
    sauced.insert(INSERT, "Total Pizzas Cheesed.........." + diags[1])
    sauced.place(x=460,y=220)
    time = Text(other, font = diagFont, bd = -2, bg = "gray20", fg = "white", height=1, width=37)
    time.insert(INSERT, "Average Pizza Time..........." + diags[2])
    time.place(x=460,y=270)
    health = Text(other, font = diagFont, bd = -2, bg = "gray20", fg = "white", height=1, width=37)
    health.insert(INSERT, "Machine Health..........." + diags[3])
    health.place(x=460,y=320)
    
    # Calibration
    calib = Text(other, font = headingFont, bd = -2, bg = main_bg, fg = main_fg, height=1, width=27)
    calib.insert(INSERT, "CHEESE WEIGHT CALIBRATION")
    calib.place(x=10,y=10)
    
    text14 = Text(other, font=calibFont, bd = -2, bg = main_bg, fg = main_fg, height=1, width=3)
    text14.insert(INSERT, "14\"")
    text14.place(x=10,y=80)
    text12 = Text(other, font=calibFont, bd = -2, bg = main_bg, fg = main_fg, height=1, width=3)
    text12.insert(INSERT, "12\"")
    text12.place(x=10,y=170)
    text10 = Text(other, font=calibFont, bd = -2, bg = main_bg, fg = main_fg, height=1, width=3)
    text10.insert(INSERT, "10\"")
    text10.place(x=10,y=260)
    text7 = Text(other, font=calibFont, bd = -2, bg = main_bg, fg = main_fg, height=1, width=3)
    text7.insert(INSERT, "7\"")
    text7.place(x=10,y=350)
    
    speed14Var = DoubleVar()
    speed14Var.set(speed[14])
    speed14 = Label(other, font=calibFont, textvariable=speed14Var, bg = button_color, fg = main_fg, bd = -2, height=1, width=7)
    speed14.place(x=160,y=82)
    speed12Var = DoubleVar()
    speed12Var.set(speed[12])
    speed12 = Label(other, font=calibFont, textvariable=speed12Var, bg = button_color, fg = main_fg, bd = -2, height=1, width=7)
    speed12.place(x=160,y=172)
    speed10Var = DoubleVar()
    speed10Var.set(speed[10])
    speed10 = Label(other, font=calibFont, textvariable=speed10Var, bg = button_color, fg = main_fg, bd = -2, height=1, width=7)
    speed10.place(x=160,y=262)
    speed7Var = DoubleVar()
    speed7Var.set(speed[7])
    speed7 = Label(other, font=calibFont, textvariable=speed7Var, bg = button_color, fg = main_fg, bd = -2, height=1, width=7)
    speed7.place(x=160,y=352)
    
    sub14 = Button(other, text = "-", font = calibFont, bg = button_color, fg = main_fg, command = lambda: subtract(14, speed14Var), height = 1, width = 2)
    sub14.place(x=80,y=75)
    add14 = Button(other, text = "+", font = calibFont, bg = button_color, fg = main_fg, command = lambda: add(14, speed14Var), height = 1, width = 2)
    add14.place(x=325,y=75)
    sub12 = Button(other, text = "-", font = calibFont, bg = button_color, fg = main_fg, command = lambda: subtract(12, speed12Var), height = 1, width = 2)
    sub12.place(x=80,y=165)
    add12 = Button(other, text = "+", font = calibFont, bg = button_color, fg = main_fg, command = lambda: add(12, speed12Var), height = 1, width = 2)
    add12.place(x=325,y=165)
    sub10 = Button(other, text = "-", font = calibFont, bg = button_color, fg = main_fg, command = lambda: subtract(10, speed10Var), height = 1, width = 2)
    sub10.place(x=80,y=255)
    add10 = Button(other, text = "+", font = calibFont, bg = button_color, fg = main_fg, command = lambda: add(10, speed10Var), height = 1, width = 2)
    add10.place(x=325,y=255)
    sub7 = Button(other, text = "-", font = calibFont, bg = button_color, fg = main_fg, command = lambda: subtract(7, speed7Var), height = 1, width = 2)
    sub7.place(x=80,y=345)
    add7 = Button(other, text = "+", font = calibFont, bg = button_color, fg = main_fg, command = lambda: add(7, speed7Var), height = 1, width = 2)
    add7.place(x=325,y=345)

#**************************************TKINTER SET UP***************************************

# TK screen set up
screen = Tk()
screen.overrideredirect(1)
screen.geometry('800x480')
screen.configure(bg=main_bg)
screen.title("Sm^rt Cheeser")

# Fonts for screen
sizeFont = font.Font(family='Helvetica', size=52, weight='bold')
stopFont = font.Font(family='Helvetica', size=50, weight='bold')
otherFont = font.Font(family='Helvetica', size=24, weight='normal')

# Size buttons
fourteenButton  = Button(screen, text = "14\"", font = sizeFont, bg = "lime green", fg = "white", command = lambda: setSize(fourteenButton, 14), height = 2 , width = 3)
fourteenButton.place(x=640, y=15)

twelveButton  = Button(screen, text = "12\"", font = sizeFont, bg = "lime green", fg = "white", command = lambda: setSize(twelveButton, 12), height = 2 , width = 3)
twelveButton.place(x=430, y=15)

tenButton  = Button(screen, text = "10\"", font = sizeFont, bg = "lime green", fg = "white", command = lambda: setSize(tenButton, 10), height = 2 , width = 3)
tenButton.place(x=222, y=15)

sevenButton  = Button(screen, text = "7\"", font = sizeFont, bg = "lime green", fg = "white", command = lambda: setSize(sevenButton, 7), height = 2 , width = 3)
sevenButton.place(x=15, y=15)

# Donatos Image
img = PIL.ImageTk.PhotoImage(PIL.Image.open(donatos_path).resize((114,38), PIL.Image.ANTIALIAS))
logo = Label(screen, image = img, bg=main_bg)
logo.place(x=40, y=255)

# Function button
stopButton  = Button(screen, text = "STOP", font = stopFont, bg = button_color, fg = main_fg, command = stopPumping, height = 1, width = 9)
stopButton.place(x=220, y=235)

moreButton  = Button(screen, text = "...", font = stopFont, bg = button_color, fg = main_fg, command = moreScreen, height = 1, width = 3)
moreButton.place(x=640, y=235)

cleanButton  = Button(screen, text = "CLEAN", font = otherFont, bg = button_color, fg = main_fg, command = clean, height = 2, width = 10)
cleanButton.place(x=15, y=380)

primeButton  = Button(screen, text = "PRIME", font = otherFont, bg = button_color, fg = main_fg, command = prime, height = 2, width = 10)
primeButton.place(x=575, y=380)

light  = Button(screen, text = "LESS\nSAUCE", font = otherFont, activebackground = "orange", activeforeground = "white", bg = button_color, fg = main_fg, command = lambda: setAmount(lt), height = 2, width = 5)
light.place(x=260, y=380)

extra  = Button(screen, text = "EXTRA\nSAUCE", font = otherFont, activebackground = "DarkOrange2", activeforeground = "white", bg = button_color, fg = main_fg, command = lambda: setAmount(ext), height = 2, width = 5)
extra.place(x=420, y=380)

mainloop()

