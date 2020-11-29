import tkinter as tk
from tkinter import ttk
from tkinter import *
from tkinter import messagebox
from tkinter.ttk import Progressbar
from tkinter import filedialog
from customStepper import CustomStepper
from pymata4 import pymata4
import pandas as pd

import configHelper, configLogging, folderGenerator, codeUtilitys, os.path, time, threading, csv, customExceptions

root = Tk()
folderGenerator.generateFolders()
configHelper.generateAllConfigs()

#========================================VARIABLES========================================
BOARD = None
STEPPER_OBJECT =  None
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
STEPPER_OBJECTS = []

#==================================TK ROOT WINDOW SETTUP==================================
PROGRAM_NAME = codeUtilitys.amendSpacesToString("PyEngineControl")
PROGRAM_VERSION = "0.0.1-alpha.1"
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


#========================================METHODS==========================================
def watchDag():
    ProgramLogger.info("[WATCH DOG] Starting.")
    timeout = int(PROGAM_COFIGS['GlobalStepperParms']['inactivity_timeout'])
    while STEPPER_OBJECT.shutdown_flag == False:
        time.sleep(5)
        currentTime = time.time()
        for stepperObject in CustomStepper.STEPPER_OBJECT_LIST:
            if stepperObject.stepperActive and stepperObject.isInMotion == False:
                if (currentTime - stepperObject.lastMovmentTime) > timeout:
                    ProgramLogger.info(f"[WATCH DOG] Stepper: [{stepperObject.stepperName}] timed out.")
                    stepperObject.disableStepper()


def Exit():
    ProgramLogger.setLevel('INFO')
    ProgramLogger.info("Closing Program.")
    try:
        BOARD.shutdown()
        STEPPER_OBJECT.shutdown()
    except:
        pass
    root.destroy()


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


def attatchSteppers():
    ProgramLogger.info("Attatching Stepper Motors.")
    global STEPPER_OBJECTS
    global STEPPER_OBJECT
    global manualControlTabRowNum
    global settupRunTabRowNum
    global settupRunTabFileEntrys
    global rootMenubar
    global rootStepperMenu
    global stepperPositionSpinboxs

    rootStepperMenu = Menu(rootMenubar, tearoff=False)
    rootMenubar.add_cascade(label="Steppers", menu=rootStepperMenu)
    rootStepperMenu.add_command(label="Enable All Steppers", command=CustomStepper.enableAllSteppers)
    rootStepperMenu.add_command(label="Disable All Steppers", command=CustomStepper.disableAllSteppers)

    for stepperSection in STEPPER_COFIGS:
        ProgramLogger.debug(f"[CONFIG] Adding stepper Name: [{stepperSection}]\n\tOptions: {STEPPER_COFIGS[stepperSection]}")
        try:
            stepperObject = CustomStepper(stepperSection, STEPPER_COFIGS[stepperSection])
            STEPPER_OBJECT = stepperObject
            rootPerStepperMenu = Menu(rootStepperMenu, tearoff=False)
            rootStepperMenu.add_cascade(label=codeUtilitys.amendSpacesToString(stepperObject.stepperName), menu=rootPerStepperMenu)
            rootPerStepperMenu.add_command(label="Enable Stepper", command=lambda x=stepperObject: x.enableStepper())
            rootPerStepperMenu.add_command(label="Disable Stepper", command=lambda x=stepperObject: x.disableStepper())
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

    for stepperObject in STEPPER_OBJECTS:
        manualControlTabNameLabel = Label(manualControlTab, text=codeUtilitys.amendSpacesToString(stepperObject.stepperName))
        manualControlTabNameLabel.grid(row=manualControlTabRowNum, column=0)
        stepperPositionSpinbox = Spinbox(manualControlTab, from_=0, to=100)
        stepperPositionSpinbox.grid(row=manualControlTabRowNum, column=1)
        stepperPositionSpinbox.bind('<Return>', validatePositionValue)
        stepperPositionSpinboxs[stepperObject] = stepperPositionSpinbox
        manualControlTabRowNum += 1

        settupRunTabNameLabel = Label(settupRunTab, text=codeUtilitys.amendSpacesToString(stepperObject.stepperName))
        settupRunTabNameLabel.grid(row=settupRunTabRowNum, column=0)

        settupRunTabFileEntry = Entry(settupRunTab, width=35, borderwidth=3)
        settupRunTabFileEntry.grid(row=settupRunTabRowNum, column=1)
        settupRunTabFileEntry.insert(END, "Select File")
        settupRunTabFileEntrys[stepperObject] = settupRunTabFileEntry

        settupRunTapPickFileButton = Button(settupRunTab, text="Browse", command=lambda x=settupRunTabFileEntry: getRunFileLocation(x))
        settupRunTapPickFileButton.grid(row=settupRunTabRowNum, column=2, columnspan=2)
        settupRunTabRowNum += 1


    settupRunTabRunButton = Button(settupRunTab, text="Run Test", command=validateSettupTab)
    settupRunTabRunButton.grid(row=settupRunTabRowNum, column=0, columnspan=3)
    settupRunTabRowNum += 1


    ProgramLogger.info(f"Total stepper count: {str(len(STEPPER_OBJECTS))}")
    ProgramLogger.info(f"Total pins used: {str(len(CustomStepper.TOTAL_PINS_USED))}")
    manualStepperSetPositionButton = Button(manualControlTab, text="Update Stepper Positions", command=validatePositionValue)
    manualStepperSetPositionButton.grid(row=manualControlTabRowNum, column=0, columnspan=2)
    loading.destroy()
    the_watchDog_thread = threading.Thread(target=watchDag, daemon=True)
    the_watchDog_thread.name = "WatchDog"
    the_watchDog_thread.start()


def connectToBoard():
    global BOARD
    ProgramLogger.info("Connecting to board.")
    try:
        BOARD = pymata4.Pymata4()
        totalDigitalPins = len(BOARD.digital_pins)
        totalDAnalogPins = len(BOARD.analog_pins)
        ProgramLogger.info(f"Total Digital Pins: {str(totalDigitalPins)} Total Analog Pins: {str(totalDAnalogPins)}")
        CustomStepper.BOARD = BOARD
    except AttributeError:
        loading.destroy()
        info = "Could not connect to arduino board. Is it pluged in? Reconnect the arduino USB cable, then try again. Or check that the arduino board is assigned a COM port in Device Manager."
        ProgramLogger.critical(info, exc_info=True)
        messagebox.showerror(PROGRAM_NAME, f"{info}\n\nCheck program log file for more info.")
        return
    attatchSteppers()


def askToConnect():
    if not checkBoardConnection():
        info = "Arduino is not connected. Would you like to connect now?"
        ProgramLogger.warning(info)
        if messagebox.askyesno(PROGRAM_NAME, info):
            global loadingThread
            loadingThread = threading.Thread(target=LoadingBar, args=("Connecting...",), daemon=True)
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


def validatePositionValue(event=None):
    try:
        for stepperObject in stepperPositionSpinboxs:
            float(stepperPositionSpinboxs[stepperObject].get())
    except ValueError:
        info = f"Position value for Stepper: {stepperObject.stepperName} must be a decimal number."
        ProgramLogger.error(info)
        messagebox.showerror(PROGRAM_NAME, info)
        return
    getNewPosition()
    return


def getNewPosition():
    for stepperObject in stepperPositionSpinboxs:
        positionValue = float(stepperPositionSpinboxs[stepperObject].get())
        try:
            # threading.Thread(target=stepperObject.moveToPosition, args=(positionValue,), daemon=True).start()
            stepperObject.addMoveToQueue(newPosition=positionValue)
        except IndexError:
            info = f"Stepper: [{stepperObject.stepperName}] is assigned a pin number that doesn't exsist."
            ProgramLogger.critical(info, exc_info=True)
            messagebox.showerror(PROGRAM_NAME, info)
            return
        except customExceptions.OutOfRangeError as err:
            ProgramLogger.error(err, exc_info=True)
            messagebox.showerror(PROGRAM_NAME, err)
            return
    return


def getLogFileLocation():
    supportedFileTypes = (("CSV", "*.csv"), ("All Files", "*.*"))
    fileLocation = filedialog.asksaveasfilename(title="Save As", filetypes=supportedFileTypes)
    currentLogFileEntry.delete(0, END)
    currentLogFileEntry.insert(END, fileLocation)


def getRunFileLocation(entryBox):
    supportedFileTypes = (("CSV", "*.csv"), ("All Files", "*.*"))
    fileLocation = filedialog.askopenfilename(title="Open File", filetypes=supportedFileTypes)
    entryBox.delete(0, END)
    entryBox.insert(END, fileLocation)


def validateSettupTab():
    for stepperObject in settupRunTabFileEntrys:
        fileName = settupRunTabFileEntrys[stepperObject].get()
        if not os.path.isfile(fileName):
            info = "Please select a valid program file for each stepper motor."
            ProgramLogger.error(f"{info}\n\tFile Path is not valid: {fileName}")
            messagebox.showerror(PROGRAM_NAME, info)
            settupRunTabFileEntrys[stepperObject].focus()
            settupRunTabFileEntrys[stepperObject].icursor("end")
            settupRunTabFileEntrys[stepperObject].selection_range(0, END)
            return
        threadName = stepperObject.stepperName + "_Run_Test"
        runTestThread = threading.Thread(target=runTest, args=(threadName, stepperObject, fileName), daemon=True)
        runTestThread.name = threadName
        runTestThread.start()


def runTest(threadName, stepperObject, fileToOpen):
    filePath = fileToOpen
    fileName = fileToOpen.split('/')[-1]
    ProgramLogger.info(f"[THREAD {threadName}] Starting programed routine. Reading file: [{fileName}]")
    dataHeader = []
    dataRows = []
    with open(filePath, 'r') as csvfile:
        csvreader = csv.reader(csvfile)
        # extracting field names through first row
        dataHeader = next(csvreader)
        ProgramLogger.debug(f"[FILE {threadName}] Headers: {dataHeader}")
        # extracting each data row one by one
        for row in csvreader:
            if len(row) != 0:
                dataRows.append(row)

    csvfile.close()
    ProgramLogger.info(f"[THREAD {threadName}] Total rows to send: {str(len(dataRows) - 1)}")
    for data in dataRows:
        try:
            # lineNumber = int(data[dataHeader.index('Line')])
            moveToPos = float(data[dataHeader.index('MoveTo')])
            timeToHold = float(data[dataHeader.index('HoldFor')])
            stepperObject.addMoveToQueue(newPosition=moveToPos, holdTime=timeToHold)
        except ValueError as err:
            info = f"[FILE] Could not convert some cells in file: [{fileName}]. Please check that each column value type is on the supported types list."
            ProgramLogger.error(f"[{info}] Error: {err}", exc_info=True)
            messagebox.showerror(PROGRAM_NAME, info)
            return
        except customExceptions.OutOfRangeError as err:
            ProgramLogger.error(err, exc_info=True)
            messagebox.showerror(PROGRAM_NAME, err)
            return


#=====================================INITIALIZATION=======================================
ProgramLogger.debug(f"[CONFIG] Stepper Config file contents: {STEPPER_COFIGS}")
ProgramLogger.debug(f"[CONFIG] Program Config file contents: {PROGAM_COFIGS}")

# Create csv file for debugging stepper movment times.
if defaultLogVerbosity == 'DEBUG':
    headerLine = ['Total_Execution_Time', 'Loop_Execution_Time', 'Tuning_Time', 'Tuning_Constent']
    debugFileName = "Debug_Movment_Times.csv"
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
rootMenubar.add_cascade(label="File", menu=rootFilemenu)
rootFilemenu.add_command(label="Connect To Arduino", command=askToConnect)

rootNoteBook = ttk.Notebook(root)
rootNoteBook.pack(fill='both', expand=1, pady=15)

#===================MANUAL CONTROL TAB===========================
manualControlTabRowNum = 0
manualControlTab = Frame(rootNoteBook)
manualControlTab.pack(fill='both', expand=1)
rootNoteBook.add(manualControlTab, text="Manual Control")

stepperPositionSpinboxs = {}


#======================SETTUP RUN TAB=============================
settupRunTabRowNum = 0
settupRunTab = Frame(rootNoteBook)
settupRunTab.pack(fill='both', expand=1)
rootNoteBook.add(settupRunTab, text="Setup Run")
settupRunTabFileEntrys = {}


#=========================LOGGING TAB=============================
loggingTabRowNum = 0
loggingTab = Frame(rootNoteBook)
loggingTab.pack(fill='both', expand=1)
rootNoteBook.add(loggingTab, text="Logging")


logFileLabel = Label(loggingTab, text="Where To Save Run's")
logFileLabel.grid(row=loggingTabRowNum, column=0, padx=5)

currentLogFileEntry = Entry(loggingTab, width=35, borderwidth=3)
currentLogFileEntry.grid(row=loggingTabRowNum, column=1, padx=5)

pickLogFileButton = Button(loggingTab, text="Browse", command=getLogFileLocation)
pickLogFileButton.grid(row=loggingTabRowNum, column=2, padx=5)
loggingTabRowNum += 1

loggingIntervalLabel = Label(loggingTab, text="Logging Interval (seconds):")
loggingIntervalLabel.grid(row=loggingTabRowNum, column=0, padx=5)

loggingIntervalSpinbox = Spinbox(loggingTab)
loggingIntervalSpinbox.grid(row=loggingTabRowNum, column=1, padx=5)

root.protocol("WM_DELETE_WINDOW", Exit)
root.mainloop()