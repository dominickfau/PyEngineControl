import tkinter as tk
from tkinter import ttk
from tkinter import *
from tkinter import messagebox
from tkinter.ttk import Progressbar
from tkinter import filedialog
from customStepper import CustomStepper
from pymata4 import pymata4
import pandas as pd

import configHelper, configLogging, folderGenerator, codeUtilitys, os.path, time, threading, csv, customExceptions, sys

root = Tk()
folderGenerator.generateFolders()
configHelper.generateAllConfigs()



#====================================THREAD VARIABLES=====================================
MOVMENT_QUEUE = []
SHUTDOWN_FLAG = False
WATCH_DOG_TUNING_TIME = 5
haltMotion = False



#========================================VARIABLES========================================
BOARD = None
STEPPER_OBJECTS =  []
VALID_RUN_FILE_HEADERS = ['Line']



PROGRAM_COFIG_FILE_NAME = configHelper.PROGRAM_COFIG_FILE_NAME
STEPPER_COFIG_FILE_NAME = configHelper.STEPPER_COFIG_FILE_NAME

PROGRAM_LOG_FILE_NAME = configHelper.PROGRAM_LOG_FILE_NAME
LOGGING_CONFIG = configHelper.readConfigSection(PROGRAM_COFIG_FILE_NAME, 'Logging')

defaultLogVerbosity = 'WARNING'
try:
    defaultLogVerbosity = LOGGING_CONFIG['log_verbosity']
    ProgramLogger = configLogging.createLogger(__name__, PROGRAM_LOG_FILE_NAME, defaultLogVerbosity)
except KeyError:
    ProgramLogger = configLogging.createLogger(__name__, PROGRAM_LOG_FILE_NAME, defaultLogVerbosity)
    ProgramLogger.warning(f"Config file: {PROGRAM_COFIG_FILE_NAME} missing key: log_verbosity. Defaulting to {defaultLogVerbosity}")
except ValueError:
    ProgramLogger = configLogging.createLogger(__name__, PROGRAM_LOG_FILE_NAME, defaultLogVerbosity)
    ProgramLogger.error(f"Config file: {PROGRAM_COFIG_FILE_NAME} has Key: log_verbosity, but Value: {LOGGING_CONFIG['log_verbosity']} is not supported. Defaulting to {defaultLogVerbosity}")

PROGRAM_LOG_FILE_SIZE = codeUtilitys.getFileSize(PROGRAM_LOG_FILE_NAME)
if int(LOGGING_CONFIG['log_file_size_limit']) < PROGRAM_LOG_FILE_SIZE:
    with open(PROGRAM_COFIG_FILE_NAME, 'w') as f:
        f.write("File cleared.\n\n")
    f.close()

PROGAM_COFIGS = configHelper.readConfigFile(PROGRAM_COFIG_FILE_NAME)
STEPPER_COFIGS = configHelper.readConfigFile(STEPPER_COFIG_FILE_NAME)

#==================================TK ROOT WINDOW SETTUP==================================
PROGRAM_NAME = codeUtilitys.amendSpacesToString("PyEngineControl")
PROGRAM_VERSION = "0.0.1-alpha.2"
SCREEN_WIDTH, SCREEN_HEIGHT = root.winfo_screenwidth(), root.winfo_screenheight()
ROOT_WIDTH, ROOT_HIGHT = 600, 400
x = (SCREEN_WIDTH/2) - (ROOT_WIDTH/2)
y = (SCREEN_HEIGHT/2) - (ROOT_HIGHT/2)
root.geometry("%dx%d+%d+%d" % (ROOT_WIDTH, ROOT_HIGHT, x, y))
root.resizable(True, True)
root.title(f"{PROGRAM_NAME} [{PROGRAM_VERSION}]")
ProgramLogger.setLevel('INFO')
ProgramLogger.info(f"Program Version: {PROGRAM_VERSION}")
ProgramLogger.setLevel(defaultLogVerbosity)


#========================================THREAD WORKERS====================================
def start_watchDog_tread():
    global the_watchDog_thread
    if the_watchDog_thread.is_alive() == False:
        ProgramLogger.info("[THREAD] Attempting to start WatchDog thread.")
        the_watchDog_thread.start()
    return


def start_movementQueue_tread():
    global the_movmentQueue_thread
    if the_movmentQueue_thread.is_alive() == False:
        ProgramLogger.info("[THREAD] Attempting to start MovmentQueue thread.")
        the_movmentQueue_thread.start()
    return


def _watchDog():
    """
    This thread continuously checks if stepper motors have reached or exceded the timeout time.
    When the set time has been reached or excered and the stepper is not in motion, calls disableStepper().
    """
    global SHUTDOWN_FLAG
    try:
        timeout = int(PROGAM_COFIGS['GlobalStepperParms']['inactivity_timeout'])
    except (KeyError, ValueError) as err:
        SHUTDOWN_FLAG = True
        info = f"[THREAD WatchDog] An error occurred while starting a critical thread! Please fix error and try again, The program will close after cliking OK.\nError: [{err}]"
        ProgramLogger.critical(info)
        messagebox.showerror(PROGRAM_NAME, info)
        Exit()
    ProgramLogger.info("[THREAD] WatchDog thread Running.")
    while SHUTDOWN_FLAG == False:
        time.sleep(WATCH_DOG_TUNING_TIME)
        currentTime = time.time()
        for stepperObject in STEPPER_OBJECTS:
            if stepperObject.stepperActive and stepperObject.isInMotion == False:
                if (currentTime - stepperObject.lastMovementTime) > timeout:
                    ProgramLogger.info(f"[WATCH DOG] Stepper: [{stepperObject.name}] timed out.")
                    stepperObject.disableStepper()
    ProgramLogger.critical("[WATCH DOG] Shutdown Flag  set to True. Thread will now stop.")


def _movementQueue():
    """
    This thread continuously checks for movement requestes in the movement queue.
    When a movement is in the queue, this commands the stepper to move to each.
    """
    ProgramLogger.info("[THREAD] MovmentQueue thread Running.")
    while SHUTDOWN_FLAG == False:
        if len(MOVMENT_QUEUE) != 0:
            nextMove = MOVMENT_QUEUE.pop(0)

            stepperObject = nextMove[0]
            newPosition = float(nextMove[1])
            holdTime = nextMove[2]

            movingLabel = stepperPositionMovingLables[stepperObject]
            movingLabel.config(text="Moving...")

            #TODO: Finish _movementQueue
            ProgramLogger.debug(f"[THREAD MovementQueue] Stepper: [{stepperObject.name}] new movement: {str(newPosition)}")
            moveStepper("MovementQueue", stepperObject, newPosition)
            
            if holdTime != None:
                waitTime = float(holdTime)
                ProgramLogger.info(f"[THREAD MovementQueue] Holding for: {str(waitTime)} seconds")
                time.sleep(waitTime)
            movingLabel.config(text="")
        elif haltMotion == True:
            MOVMENT_QUEUE.clear()
    ProgramLogger.critical("[THREAD MovementQueue] Shutdown Flag set to True. Thread will now stop.")



#========================================METHODS==========================================
def Exit():
    ProgramLogger.setLevel('INFO')
    ProgramLogger.info("Closing Program.")
    try:
        BOARD.shutdown()
    except:
        pass
    root.quit()


def enableStepper(stepperObject):
    stepperObject.lastMovementTime = time.time()
    stepperObject.stepperActive = True
    if stepperObject.invert_enable_pin:
        BOARD.digital_write(stepperObject.arduino_enable_pin, 0)
    else:
        BOARD.digital_write(stepperObject.arduino_enable_pin, 1)
    ProgramLogger.info(f"Stepper: [{stepperObject.name}] ENABELED.")


def disableStepper(stepperObject):
    stepperObject.stepperActive = False
    if stepperObject.invert_enable_pin:
        BOARD.digital_write(stepperObject.arduino_enable_pin, 1)
    else:
        BOARD.digital_write(stepperObject.arduino_enable_pin, 0)
    ProgramLogger.info(f"Stepper: [{stepperObject.name}] DISABLED.")


def rotateStepper(threadName, stepperObject, stepsToMove):
    if stepperObject.moveDirection == 0:
        ProgramLogger.debug(f"[THREAD {threadName}] Setting direction pin: {str(stepperObject.arduino_direction_pin)} LOW.")
        BOARD.digital_write(stepperObject.arduino_direction_pin, 0)
    elif stepperObject.moveDirection == 1:
        ProgramLogger.debug(f"[THREAD {threadName}] Setting direction pin: {str(stepperObject.arduino_direction_pin)} HIGH.")
        BOARD.digital_write(stepperObject.arduino_direction_pin, 1)
    else:
        raise ValueError("direction can only be 0 or 1.")
    
    if not stepperObject.stepperActive:
        enableStepper(stepperObject)
    ProgramLogger.debug(f"[THREAD {threadName}] Commanding Stepper: [{stepperObject.name}] to rotate {str(stepsToMove)} Steps.")
    timeStart = time.time()

    #FIXME: Find a better way to wait for serial transmition to finish.
    tuningTimeConstent = 1515.84615 # approximate max steppes per second.
    tuningTime = (1 / tuningTimeConstent) * stepsToMove
    for x in range(stepsToMove):
        BOARD.digital_pin_write(stepperObject.arduino_step_pin, 1)
        BOARD.digital_pin_write(stepperObject.arduino_step_pin, 0)
        stepperObject.lastMovementTime = time.time()
    timeEndLoop = time.time()
    time.sleep(tuningTime)
    timeEnd = time.time()

    if defaultLogVerbosity == 'DEBUG':
        stepperObject.lineCount += 1
        debugFileName = "Debug_Movement_Times.csv"
        fullDebugFilePath = folderGenerator.findFullPath('Logs') + debugFileName
        dataToWrite = [str(stepperObject.lineCount), threadName, str(stepsToMove), str(timeEnd - timeStart), str(timeEndLoop - timeStart), str(tuningTime), str(tuningTimeConstent)]
        with open(fullDebugFilePath, 'a', newline='') as f:
            csvwriter = csv.writer(f)
            csvwriter.writerow(dataToWrite)
        f.close()

    ProgramLogger.debug(f"[THREAD {threadName}] Stepper: [{stepperObject.name}] at commanded position.\n\tLoop Execution Time: {str(timeEndLoop - timeStart)} seconds. Total Execution Time: {str(timeEnd - timeStart)} seconds.\n\tTuning Time: {str(tuningTime)} Tuning Constent: {str(tuningTimeConstent)}")



def moveStepper(threadName, stepperObject, newPosition):
    ProgramLogger.info(f"[THREAD {threadName}] Moving Stepper: [{stepperObject.name}] to {str(newPosition)}")
    totalAvailableSteps = stepperObject.steps_per_rev * (stepperObject.range_of_motion * stepperObject.drive_ratio)
    stepsToMove = int(totalAvailableSteps * (abs(newPosition - stepperObject.currentPosition) / 100))
    
    if newPosition > stepperObject.currentPosition:
        ProgramLogger.debug(f"[THREAD {threadName}] Moving stepper [{stepperObject.name}] to a higher value.")
        if stepperObject.invert_direction:
            stepperObject.moveDirection = 1
        else:
            stepperObject.moveDirection = 0
    elif newPosition < stepperObject.currentPosition:
        ProgramLogger.debug(f"[THREAD {threadName}] Moving stepper [{stepperObject.name}] to a lower value.")
        if stepperObject.invert_direction:
            stepperObject.moveDirection = 0
        else:
            stepperObject.moveDirection = 1
    else:
        ProgramLogger.warning(f"[THREAD {threadName}] Stepper: [{stepperObject.name}] already at commanded position.")
        return
    rotateStepper(threadName, stepperObject, stepsToMove)
    stepperObject.currentPosition = newPosition


def LoadingBar(loadingText):
    global loading
    loading = Toplevel()
    loading.title("Loading")
    loading.focus()
    loading.wm_attributes("-topmost", 1)
    width = 300
    height = 60
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width/2) - (width/2)
    y = (screen_height/2) - (height/2)
    loading.resizable(0, 0)
    loading.geometry("%dx%d+%d+%d" % (width, height, x, y))
    progress = Progressbar(loading, orient = HORIZONTAL, length = 200, mode = 'indeterminate')
    label_loading = Label(loading, text=loadingText)
    label_loading.pack(pady=3)
    progress.pack()
    progress.start(interval=10)


def updateTemplateFile(fileName):
    if fileName == 'RunProgram.csv':
        fullFilePath = folderGenerator.findFullPath('Templates') + fileName
        with open(fullFilePath, 'w', newline='') as f:
            csvwriter = csv.writer(f)
            # Write Colunm names
            csvwriter.writerow(VALID_RUN_FILE_HEADERS)
        f.close()
        ProgramLogger.info(f"Updated template file [{fileName}]")
    else:
        ProgramLogger.warning(f"Could not update template file [{fileName}] do not know how to.")


def attatchSteppers():
    ProgramLogger.info("Attatching Stepper Motors.")
    global STEPPER_OBJECTS
    global manualControlTabRowNum
    global settupRunTabRowNum
    global stepperPositionSpinboxs
    global stepperPositionMovingLables
    global VALID_RUN_FILE_HEADERS
    # global rootMenubar
    # global rootStepperMenu

    #TODO: Code out global stepper menu drop down
    # rootStepperMenu = Menu(rootMenubar, tearoff=False)
    # rootMenubar.add_cascade(label="Steppers", menu=rootStepperMenu)
    # rootStepperMenu.add_command(label="Force Stop All Steppers", command=CustomStepper.forceStopAllMotion)
    # rootStepperMenu.add_command(label="Allow Motion All Steppers", command=CustomStepper.allowAllMotion)
    # rootStepperMenu.add_separator()
    # rootStepperMenu.add_command(label="Enable All Steppers", command=CustomStepper.enableAllSteppers)
    # rootStepperMenu.add_command(label="Disable All Steppers", command=CustomStepper.disableAllSteppers)

    for stepperSection in STEPPER_COFIGS:
        ProgramLogger.debug(f"[CONFIG] Adding stepper Name: [{stepperSection}]\n\tOptions: {STEPPER_COFIGS[stepperSection]}")
        try:
            stepperObject = CustomStepper(stepperName=stepperSection, options=STEPPER_COFIGS[stepperSection])

            #TODO: Code out per stepper menu drop down
            # rootPerStepperMenu = Menu(rootStepperMenu, tearoff=False)
            # rootStepperMenu.add_cascade(label=codeUtilitys.amendSpacesToString(stepperObject.stepperName), menu=rootPerStepperMenu)
            # rootPerStepperMenu.add_command(label="Force Stop Stepper", command=lambda x=stepperObject: x.forceStopMotion())
            # rootPerStepperMenu.add_command(label="Allow Stepper Motion", command=lambda x=stepperObject: x.allowMotion())
            # rootPerStepperMenu.add_separator()
            # rootPerStepperMenu.add_command(label="Enable Stepper", command=lambda x=stepperObject: x.enableStepper())
            # rootPerStepperMenu.add_command(label="Disable Stepper", command=lambda x=stepperObject: x.disableStepper())

            STEPPER_OBJECTS.append(stepperObject)
        except KeyError as err:
            loading.destroy()
            info = f"Stepper config file Error: {err} From Section: [{stepperSection}]. Please add option then reopen program."
            ProgramLogger.critical(info)
            messagebox.showerror(PROGRAM_NAME, info)
            exit()
        except ValueError as err:
            loading.destroy()
            info = f"Stepper config file Error: {err} From Section: [{stepperSection}]. Please fix option then reopen program."
            ProgramLogger.critical(info)
            messagebox.showerror(PROGRAM_NAME, info)
            exit()

        VALID_RUN_FILE_HEADERS.append(stepperObject.name)

        # Define items on Manual Control Tab
        manualControlTabNameLabel = Label(manualControlTab, text=codeUtilitys.amendSpacesToString(stepperObject.name))
        manualControlTabNameLabel.grid(row=manualControlTabRowNum, column=0)
        stepperPositionSpinbox = Spinbox(manualControlTab, from_=0, to=100)
        stepperPositionSpinbox.grid(row=manualControlTabRowNum, column=1)
        stepperPositionSpinbox.bind('<Return>', getStepperSpinboxValue_onEvent)
        stepperPositionSpinboxs[stepperPositionSpinbox] = stepperObject

        stepperPositionButton = Button(manualControlTab, text="Add Move To Queue", command=lambda x=stepperObject, y=stepperPositionSpinbox: getStepperSpinboxValue_onButtonClick(stepperObject=x, spinBoxObject=y))
        stepperPositionButton.grid(row=manualControlTabRowNum, column=2)

        stepperPositionMovingLabel = Label(manualControlTab, text="")
        stepperPositionMovingLabel.grid(row=manualControlTabRowNum, column=3, padx=5)
        stepperPositionMovingLables[stepperObject] = stepperPositionMovingLabel
        manualControlTabRowNum += 1

    # Define items on Settup Run Tab
    settupRunTabNameLabel = Label(settupRunTab, text="File To Run")
    settupRunTabNameLabel.grid(row=settupRunTabRowNum, column=0)

    global settupRunTabFileEntry
    settupRunTabFileEntry = Entry(settupRunTab, width=75, borderwidth=3)
    settupRunTabFileEntry.config(state=DISABLED)
    settupRunTabFileEntry.grid(row=settupRunTabRowNum, column=1)
    settupRunTabFileEntry.insert(END, "Select File")
    
    settupRunTapPickFileButton = Button(settupRunTab, text="Browse", command=getRunFileLocation)
    settupRunTapPickFileButton.grid(row=settupRunTabRowNum, column=2)
    settupRunTabRowNum += 1

    settupRunTabRunButton = Button(settupRunTab, text="Run Test", command=startRun)
    settupRunTabRunButton.grid(row=settupRunTabRowNum, column=0, columnspan=3)
    settupRunTabRowNum += 1

    VALID_RUN_FILE_HEADERS.append('HoldTime')
    updateTemplateFile('RunProgram.csv')

    ProgramLogger.info(f"Total stepper count: {str(len(STEPPER_OBJECTS))}")
    ProgramLogger.info(f"Total pins used: {str(len(CustomStepper.TOTAL_PINS_USED))}")
    ProgramLogger.info("Finished attatching stepper motors.")

    start_movementQueue_tread()
    start_watchDog_tread()

    loading.destroy()


def connectToBoard():
    #TODO: Add timeout if board does not connect in time.
    global BOARD
    ProgramLogger.info("Connecting to board.")
    try:
        BOARD = pymata4.Pymata4()
        ProgramLogger.info(f"Total Digital Pins: {str(len(BOARD.digital_pins))} Total Analog Pins: {str(len(BOARD.analog_pins))}")
    except AttributeError:
        loading.destroy()
        info = "Could not connect to arduino board. Is it pluged in? Reconnect the arduino USB cable, then try again. Or check that the arduino board is assigned a COM port in Device Manager."
        ProgramLogger.critical(info, exc_info=True)
        messagebox.showerror(PROGRAM_NAME, f"{info}\n\nCheck program log file for more info.")
        return
    except RuntimeError as err:
        loading.destroy()
        info = f"An error occurred during board communication. If this error has somthing to do with a timeout, close the program and reconnect the arduino USB cable.\n\n{err}"
        ProgramLogger.critical(info, exc_info=True)
        messagebox.showerror(PROGRAM_NAME, f"{info}\n\nCheck program log file for more info.")
        return
    attatchSteppers()


def askToConnect():
    if not checkBoardConnection():
        info = "Arduino board is not connected. Would you like to connect now?"
        ProgramLogger.warning(info)
        if messagebox.askyesno(PROGRAM_NAME, info):
            loadingThread = threading.Thread(target=LoadingBar, args=("Connecting...",))
            loadingThread.daemon = True
            loadingThread.name = "LoadingBarWindow"
            loadingThread.start()

            connectThread = threading.Thread(target=connectToBoard, daemon=True)
            connectThread.name = "ConnectingThread"
            connectThread.start()
        else:
            return
    else:
        messagebox.showerror(PROGRAM_NAME, "Arduino is already connected.")
        return


def checkBoardConnection():
    if CustomStepper.BOARD == None:
        return False
    else:
        return True


def getRunFileLocation():
    global settupRunTabFileEntry
    supportedFileTypes = (("CSV", "*.csv"), ("All Files", "*.*"))
    fileLocation = filedialog.askopenfilename(title="Open File", filetypes=supportedFileTypes)
    fileExtention = fileLocation.split('/')[-1].split('.')[-1].lower()
    if len(fileLocation) == 0:
        settupRunTabFileEntry.config(state=NORMAL)
        settupRunTabFileEntry.delete(0, END)
        settupRunTabFileEntry.insert(END, "")
        settupRunTabFileEntry.config(state=DISABLED)
        return
    if fileExtention != 'csv':
        info = f"File extention [{fileExtention}] is not supported. Extention MUST be .csv to continue."
        settupRunTabFileEntry.config(state=NORMAL)
        settupRunTabFileEntry.delete(0, END)
        settupRunTabFileEntry.insert(END, "")
        settupRunTabFileEntry.config(state=DISABLED)
        ProgramLogger.error(info)
        messagebox.showerror(PROGRAM_NAME, info)
        return

    settupRunTabFileEntry.config(state=NORMAL)
    settupRunTabFileEntry.delete(0, END)
    settupRunTabFileEntry.insert(END, fileLocation)
    settupRunTabFileEntry.config(state=DISABLED)
    #TODO: Populate settup run tab treeview after changing file.


def validatePositionValue(stepperObject, value):
    info = None
    try:
        newPosition = float(value)
    except ValueError:
        info = f"Position value for Stepper: {stepperObject.name} must be a decimal number."
        return info
    if newPosition < 0.0 or newPosition > 100.0:
        info = f"Position value for Stepper: {stepperObject.name} outside of allowed range 0-100."
        return info
    return None


def validateHoldTimeValue(stepperObject, value):
    info = None
    try:
        waitTime = float(value)
    except ValueError:
        info = f"Hold time for Stepper: {stepperObject.name} must be a decimal number."
        return info
    if waitTime < 0.0:
        info = f"Hold time for Stepper: {stepperObject.name} MUST be a positive value.."
        return info
    return None


def addMoveToQueue(stepperObject, newPosition, holdTime=None):
        positionError = validatePositionValue(stepperObject, newPosition)
        if positionError:
            ProgramLogger.error(positionError)
            messagebox.showerror(PROGRAM_NAME, positionError)
            return
        
        if holdTime:
            holdTimeError = validateHoldTimeValue(stepperObject, holdTime)
            if holdTimeError:
                ProgramLogger.error(holdTimeError)
                messagebox.showerror(PROGRAM_NAME, holdTimeError)
                return

        toAdd = [stepperObject, newPosition, holdTime]
        MOVMENT_QUEUE.append(toAdd)


#TODO: Code validateRunFile()
def validateRunFile(fileToOpen):
    filePath = fileToOpen
    fileName = fileToOpen.split('/')[-1]
    dataHeader = []
    dataRows = []
    with open(filePath, 'r') as csvfile:
        csvreader = csv.reader(csvfile)
        # extracting field names through first row
        dataHeader = next(csvreader)
        ProgramLogger.info(f"[RUN] Headers: {dataHeader}")
        # extracting each data row one by one
        for row in csvreader:
            if len(row) != 0:
                dataRows.append(row)
    csvfile.close()

    ProgramLogger.info(f"[RUN] Total rows to send: {str(len(dataRows) - 1)}. Checking data for non-supported types.")
    # Check all rows in file.
    errMsg = False
    errorRows = []
    line_num = 1
    for data in dataRows:
        try:
            lineNumber, moveToPos, timeToHold = int(data[dataHeader.index('Line')]), float(data[dataHeader.index('MoveTo')]), float(data[dataHeader.index('HoldFor')])
            if moveToPos < 0.0 or moveToPos > 100.0:
                raise customExceptions.OutOfRangeError(f"File: {fileName} Line: {str(line_num)} outside of allowed range 0-100.")
        except ValueError as err:
            errMsg = True
            msgShort = "Cell value not supported."
            msgDetail = f"File: [{fileName}] Could not convert cell on Line: {str(line_num)} Msg: {msgShort}"
            errorRows.append([str(line_num), msgShort])
            ProgramLogger.error(f"[THREAD {threadName}] [{msgDetail}] Error: {err}", exc_info=True)
        except customExceptions.OutOfRangeError as err:
            errMsg = True
            msgShort = "Cell value out of range 0-100."
            msgDetail = f"File: [{fileName}] Could not convert cell on Line: {str(line_num)} Msg: {msgShort}"
            errorRows.append([str(line_num), msgShort])
            ProgramLogger.error(f"[THREAD {threadName}] [{msgDetail}] Error: {err}", exc_info=True)
        line_num += 1

    if errMsg:
        for stepperObject in STEPPER_OBJECTS:
            stepperObject.forceStopMotion()
        totalErrors = len(errorRows)
        separator = ' '
        delimiter = '\n'
        msgToShow = f"File: [{fileName}] {str(totalErrors)} rows failed to convert. Check ProgramLog.txt under Data/Logs for more info.\n"
        s = ""
        for errorMsg in errorRows:
            s += separator.join(errorMsg) + delimiter

        ProgramLogger.critical(msgToShow + s.strip())
        messagebox.showerror(PROGRAM_NAME, msgToShow + s.strip())
        return


#TODO: Code startRun()
def startRun(fileToOpen):
    ProgramLogger.info(f"[RUN] Starting programed routine. Reading file: [{fileName}]")


#========================================EVENT METHODS=====================================
def getStepperSpinboxValue_onEvent(event):
    spinBoxValue = event.widget.get()
    stepperObject = stepperPositionSpinboxs[event.widget]
    addMoveToQueue(stepperObject=stepperObject, newPosition=spinBoxValue)


def getStepperSpinboxValue_onButtonClick(stepperObject, spinBoxObject):
    addMoveToQueue(stepperObject=stepperObject, newPosition=spinBoxObject.get())



#=====================================INITIALIZATION=======================================
the_movmentQueue_thread = threading.Thread(target=_movementQueue)
the_movmentQueue_thread.daemon = True
the_movmentQueue_thread.name = "MovementQueue"

the_watchDog_thread = threading.Thread(target=_watchDog)
the_watchDog_thread.daemon = True
the_watchDog_thread.name = "WatchDog"

ProgramLogger.debug(f"[CONFIG] Stepper Config file contents: {STEPPER_COFIGS}")
ProgramLogger.debug(f"[CONFIG] Program Config file contents: {PROGAM_COFIGS}")

# Create csv file for debugging stepper movement times.
if defaultLogVerbosity == 'DEBUG':
    headerLine = ['Line_Number', 'Thread_Name', 'Total_Steps_Moved', 'Total_Execution_Time', 'Total_Trasmition_Time', 'Tuning_Time', 'Tuning_Constent', 'Mesured_Pulse_Time']
    debugFileName = "Debug_Movement_Times.csv"
    fullDebugFilePath = folderGenerator.findFullPath('Logs') + debugFileName
    with open(fullDebugFilePath, 'w', newline='') as f:
        csvwriter = csv.writer(f)
        # Write Colunm names
        csvwriter.writerow(headerLine)
    f.close()

#================================ROOT WINDOW INITIALIZATION=================================
rootMenubar = Menu(root)
root.config(menu=rootMenubar)

rootFilemenu = Menu(rootMenubar, tearoff=False)
rootArduinoMenu = Menu(rootMenubar, tearoff=False)
rootMenubar.add_cascade(label="File", menu=rootFilemenu)
rootMenubar.add_cascade(label="Arduino", menu=rootArduinoMenu)

rootFilemenu.add_command(label="Exit", command=Exit)
rootArduinoMenu.add_command(label="Connect", command=askToConnect)

rootNoteBook = ttk.Notebook(root)
rootNoteBook.pack(fill='both', expand=1, pady=15)

#===================MANUAL CONTROL TAB===========================
manualControlTabRowNum = 0
manualControlTab = Frame(rootNoteBook)
manualControlTab.pack(fill='both', expand=1)
rootNoteBook.add(manualControlTab, text="Manual Control")

stepperPositionSpinboxs = {}
stepperPositionMovingLables = {}


#======================SETTUP RUN TAB=============================
settupRunTabRowNum = 0
settupRunTab = Frame(rootNoteBook)
settupRunTab.pack(fill='both', expand=1)
rootNoteBook.add(settupRunTab, text="Setup Run")
settupRunTabFileEntrys = {}
#TODO: Add tree view to settup run tab.


#=========================LOGGING TAB=============================
loggingTabRowNum = 0
loggingTab = Frame(rootNoteBook)
loggingTab.pack(fill='both', expand=1)
rootNoteBook.add(loggingTab, text="Logging")


logFileLabel = Label(loggingTab, text="Where To Save Run's")
logFileLabel.grid(row=loggingTabRowNum, column=0, padx=5)

currentLogFileEntry = Entry(loggingTab, width=35, borderwidth=3)
currentLogFileEntry.grid(row=loggingTabRowNum, column=1, padx=5)

# pickLogFileButton = Button(loggingTab, text="Browse", command=getLogFileLocation)
# pickLogFileButton.grid(row=loggingTabRowNum, column=2, padx=5)
loggingTabRowNum += 1

loggingIntervalLabel = Label(loggingTab, text="Logging Interval (seconds):")
loggingIntervalLabel.grid(row=loggingTabRowNum, column=0, padx=5)

loggingIntervalSpinbox = Spinbox(loggingTab)
loggingIntervalSpinbox.grid(row=loggingTabRowNum, column=1, padx=5)







root.protocol("WM_DELETE_WINDOW", Exit)
root.mainloop()