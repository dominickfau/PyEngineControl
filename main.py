import tkinter as tk
from tkinter import ttk
from tkinter import *
from tkinter import messagebox
from pymata4 import pymata4
from configStepper import CustomStepper
import configHelper, configLogging, folderGenerator, codeUtilitys


root = Tk()
folderGenerator.generateFolders()
configHelper.generateAllConfigs()


#========================================VARIABLES========================================
PROGRAM_COFIG_FILE_NAME = configHelper.PROGRAM_COFIG_FILE_NAME
STEPPER_COFIG_FILE_NAME = configHelper.STEPPER_COFIG_FILE_NAME

PROGRAM_LOG_FILE_NAME = configHelper.PROGRAM_LOG_FILE_NAME
PROGRAM_LOG_FILE_SIZE = codeUtilitys.getFileSize(PROGRAM_LOG_FILE_NAME)

LOGGING_CONFIG = configHelper.readConfigSection(PROGRAM_COFIG_FILE_NAME, 'Logging')
defaultLogVerbosity = 'WARNING'
try:
    ProgramLogger = configLogging.createLogger(__name__, PROGRAM_LOG_FILE_NAME, LOGGING_CONFIG['log_verbosity'])
except KeyError:
    ProgramLogger = configLogging.createLogger(__name__, PROGRAM_LOG_FILE_NAME, defaultLogVerbosity)
    ProgramLogger.warning(f"Config file: {PROGRAM_COFIG_FILE_NAME} missing key: log_verbosity. Defaulting to {defaultLogVerbosity}")
except ValueError:
    ProgramLogger = configLogging.createLogger(__name__, PROGRAM_LOG_FILE_NAME, defaultLogVerbosity)
    ProgramLogger.error(f"Config file: {PROGRAM_COFIG_FILE_NAME} has Key: log_verbosity, but Value: {LOGGING_CONFIG['log_verbosity']} is not supported. Defaulting to {defaultLogVerbosity}")

PROGAM_COFIGS = configHelper.readConfigFile(PROGRAM_COFIG_FILE_NAME)
STEPPER_COFIGS = configHelper.readConfigFile(STEPPER_COFIG_FILE_NAME)
STEPPERS = []

#==================================TK ROOT WINDOW SETTUP==================================
PROGRAM_NAME = "Pyduino"
SCREEN_WIDTH, SCREEN_HEIGHT = root.winfo_screenwidth(), root.winfo_screenheight()
ROOT_WIDTH, ROOT_HIGHT = 600, 400
x = (SCREEN_WIDTH/2) - (ROOT_WIDTH/2)
y = (SCREEN_HEIGHT/2) - (ROOT_HIGHT/2)
root.geometry("%dx%d+%d+%d" % (ROOT_WIDTH, ROOT_HIGHT, x, y))
root.resizable(True, True)


#========================================METHODS==========================================
def validateSpeedValue():
    try:
        speedValue = float(manualStepperSpeed.get())
    except ValueError:
        info = "Speed value must be a decimal value."
        ProgramLogger.error(info)
        messagebox.showerror(PROGRAM_NAME, info)
        manualStepperSpeed.delete(0, END)
        manualStepperSpeed.insert(END, "0")
        return
    CustomStepper.setStepperMovmentSpeed(speedValue)


def manualSlideChange(event=None):
    for stepper in stepperSliders:
        sliderValue = float(stepperSliders[stepper].get())




#=====================================INITIALIZATION=======================================
ProgramLogger.debug(f"[CONFIG] Stepper Config file contents: {STEPPER_COFIGS}")
ProgramLogger.debug(f"[CONFIG] Program Config file contents: {PROGAM_COFIGS}")

for stepper in STEPPER_COFIGS:
    ProgramLogger.debug(f"[CONFIG] Adding stepper Name: {stepper}\n\tOptions: {STEPPER_COFIGS[stepper]}")
    try:
        stepper = CustomStepper(stepper, STEPPER_COFIGS[stepper])
        STEPPERS.append(stepper)
    except KeyError as err:
        info = f"Stepper config file Error: {err} From Section: [{stepper}]. Please add option then reopen program."
        ProgramLogger.critical(info)
        messagebox.showerror(PROGRAM_NAME, info)
        exit()


#================================ROOT WINDOW INITIALIZATION=================================
rootNoteBook = ttk.Notebook(root)
rootNoteBook.pack(fill='both', expand=1, pady=15)

#===================MANUAL CONTROL TAB===========================
manualControlTab = Frame(rootNoteBook)
manualControlTab.pack(fill='both', expand=1)
rootNoteBook.add(manualControlTab, text="Manual Control")

manualStepperSpeed = Spinbox(manualControlTab, from_=0, to=100)
manualStepperSpeed.grid(row=0, column=0)

manualStepperSpeedSetButton = Button(manualControlTab, text="Set Stepper Speed", command=validateSpeedValue)
manualStepperSpeedSetButton.grid(row=0, column=1)

stepperSliders = {}
rowNum = 1
for stepper in STEPPERS:
    nameLabel = Label(manualControlTab, text=stepper.stepperName)
    nameLabel.grid(row=rowNum, column=0)
    horizontalSlider = Scale(manualControlTab, from_=0, to=100, orient=HORIZONTAL, command=manualSlideChange)
    horizontalSlider.grid(row=rowNum, column=1)
    stepperSliders[stepper] = horizontalSlider
    rowNum += 1
ProgramLogger.info(f"[CONFIG] Total stepper count: {str(len(STEPPERS))}")







root.mainloop()