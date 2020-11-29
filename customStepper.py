from folderGenerator import findFullPath
import  codeUtilitys, time, configHelper, configLogging, threading, customExceptions, csv

PROGRAM_LOG_FILE_NAME = configHelper.PROGRAM_LOG_FILE_NAME
PROGRAM_COFIG_FILE_NAME = configHelper.PROGRAM_COFIG_FILE_NAME
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

class CustomStepper(threading.Thread):
    MOVMENT_SPEED = None
    BOARD = None
    TOTAL_PINS_USED = []

    # Used for global enable/ disable.
    STEPPER_OBJECT_LIST = []

    def __init__(self, stepperName, options):
        if not isinstance(options, dict):
            raise TypeError("Stepper config options must be a dictionary type object.")
        CustomStepper.STEPPER_OBJECT_LIST.append(self)

        threading.Thread.__init__(self)
        self.run_event = threading.Event()

        # flag to indicate we are in shutdown mode
        self.shutdown_flag = False

        self.haltMotion = False

        self.stepperName = stepperName
        self.currentPosition = 0.0
        self.stepperActive = False
        self.lastMovementTime = None
        self.isInMotion = False
        self.movementQueue = []
        self.startTime = time.time()
        self.lineCount = 0

        # Start stepper movement thread.
        threadName = self.stepperName + '_Movement_Queue'
        self.the_movement_queue_thread = threading.Thread(target=self._movement_queue_thread, args=(threadName,))
        self.the_movement_queue_thread.daemon = True
        self.the_movement_queue_thread.name = threadName
        self.the_movement_queue_thread.start()

        pinsUsed = []
        try:
            self.steps_per_rev = int(options['steps_per_rev'])
            self.range_of_motion = float(options['range_of_motion'])
            self.invert_direction = bool(options['invert_direction'])
            self.invert_enable_pin = bool(options['invert_enable_pin'])

            self.arduino_step_pin = int(options['arduino_step_pin'])
            CustomStepper.BOARD.set_pin_mode_digital_output(self.arduino_step_pin)
            pinsUsed.append(self.arduino_step_pin)

            self.arduino_direction_pin = int(options['arduino_direction_pin'])
            CustomStepper.BOARD.set_pin_mode_digital_output(self.arduino_direction_pin)
            pinsUsed.append(self.arduino_direction_pin)

            self.arduino_enable_pin = int(options['arduino_enable_pin'])
            CustomStepper.BOARD.set_pin_mode_digital_output(self.arduino_enable_pin)
            pinsUsed.append(self.arduino_enable_pin)
        except KeyError as err:
            raise KeyError(f"Missing required config option Key: {err}")
        if 'drive_ratio' in options:
            self.drive_ratio = float(options['drive_ratio'])
        else:
            self.drive_ratio = 1.0
        
        if len(CustomStepper.BOARD.digital_pins) + len(CustomStepper.BOARD.analog_pins) < len(CustomStepper.TOTAL_PINS_USED) + len(pinsUsed):
            raise ValueError("Too many pins are being used.")
        for x in pinsUsed:
            if x in CustomStepper.TOTAL_PINS_USED:
                raise ValueError(f"Pin {x} has already been used.")
            CustomStepper.TOTAL_PINS_USED.append(x)

        self.disableStepper()

    def _run_threads(self):
        self.run_event.set()

    def _is_running(self):
        return self.run_event.is_set()

    def _stop_threads(self):
        self.run_event.clear()

    def shutdown(self):
        """
        This method attempts an orderly shutdown

        """
        self.shutdown_flag = True
        self.haltMotion = True
        self._stop_threads()

    def forceStopMotion(self):
        self.haltMotion = True
        ProgramLogger.info(f"Stepper: [{self.stepperName}] FORCED STOP.")
        self.disableStepper()

    def allowMotion(self):
        self.haltMotion = False
        ProgramLogger.info(f"Stepper: [{self.stepperName}] Allowed to move.")

    def enableStepper(self):
        self.lastMovementTime = time.time()
        self.stepperActive = True
        if self.invert_enable_pin:
            CustomStepper.BOARD.digital_write(self.arduino_enable_pin, 0)
        else:
            CustomStepper.BOARD.digital_write(self.arduino_enable_pin, 1)
        ProgramLogger.info(f"Stepper: [{self.stepperName}] ENABELED.")

    def disableStepper(self):
        self.stepperActive = False
        if self.invert_enable_pin:
            CustomStepper.BOARD.digital_write(self.arduino_enable_pin, 1)
        else:
            CustomStepper.BOARD.digital_write(self.arduino_enable_pin, 0)
        ProgramLogger.info(f"Stepper: [{self.stepperName}] DISABLED.")

    def rotateStepper(self, threadName, direction, numberOfSteps):
        if direction == 0:
            ProgramLogger.debug(f"[THREAD {threadName}] Setting direction pin: {str(self.arduino_direction_pin)} LOW.")
            CustomStepper.BOARD.digital_write(self.arduino_direction_pin, 0)
        elif direction == 1:
            ProgramLogger.debug(f"[THREAD {threadName}] Setting direction pin: {str(self.arduino_direction_pin)} HIGH.")
            CustomStepper.BOARD.digital_write(self.arduino_direction_pin, 1)
        else:
            raise ValueError("direction can only be 0 or 1.")
        
        if not self.stepperActive:
            self.enableStepper()
        ProgramLogger.debug(f"[THREAD {threadName}] Commanding Stepper: [{self.stepperName}] to rotate {str(numberOfSteps)} Steps.")
        timeStart = time.time()

        #FIXME: Find a better way to wait for serial transmition to finish.
        tuningTimeConstent = 1515.84615 # approximate max steppes per second.
        tuningTime = (1 / tuningTimeConstent) * numberOfSteps
        for x in range(numberOfSteps):
            CustomStepper.BOARD.digital_pin_write(self.arduino_step_pin, 1)
            CustomStepper.BOARD.digital_pin_write(self.arduino_step_pin, 0)
            self.lastMovementTime = time.time()
        timeEndLoop = time.time()
        time.sleep(tuningTime)
        timeEnd = time.time()

        if defaultLogVerbosity == 'DEBUG':
            self.lineCount += 1
            debugFileName = "Debug_Movement_Times.csv"
            fullDebugFilePath = findFullPath('Logs') + debugFileName
            dataToWrite = [str(self.lineCount), threadName, str(numberOfSteps), str(timeEnd - timeStart), str(timeEndLoop - timeStart), str(tuningTime), str(tuningTimeConstent)]
            with open(fullDebugFilePath, 'a', newline='') as f:
                csvwriter = csv.writer(f)
                csvwriter.writerow(dataToWrite)
            f.close()

        ProgramLogger.debug(f"[THREAD {threadName}] Stepper: [{self.stepperName}] at commanded position.\n\tLoop Execution Time: {str(timeEndLoop - timeStart)} seconds. Total Execution Time: {str(timeEnd - timeStart)} seconds.\n\tTuning Time: {str(tuningTime)} Tuning Constent: {str(tuningTimeConstent)}")

    def moveToPosition(self, threadName, newPosition):
        ProgramLogger.info(f"[THREAD {threadName}] Moving Stepper: [{self.stepperName}] to {str(newPosition)}")
        totalAvailableSteps = self.steps_per_rev * (self.range_of_motion * self.drive_ratio)
        stepsToMove = int(totalAvailableSteps * (abs(newPosition - self.currentPosition) / 100))
        
        if newPosition > self.currentPosition:
            ProgramLogger.debug(f"[THREAD {threadName}] Moving stepper to a higher value.")
            if self.invert_direction:
                direction = 1
            else:
                direction = 0
        elif newPosition < self.currentPosition:
            ProgramLogger.debug(f"[THREAD {threadName}] Moving stepper to a lower value.")
            if self.invert_direction:
                direction = 0
            else:
                direction = 1
        else:
            return
        self.rotateStepper(threadName, direction, stepsToMove)
        self.currentPosition = newPosition



    def addMoveToQueue(self, newPosition, holdTime=None):
        if self.haltMotion == True:
            raise customExceptions.MotionNotAllowedError(f"Stepper: [{self.stepperName}] is not allowed to move.")
        if newPosition < 0.0 or newPosition > 100.0:
            raise customExceptions.OutOfRangeError(f"Stepper: [{self.stepperName}] new position [{str(newPosition)}] outside of allowed range 0-100.")
        toAdd = [newPosition, holdTime]
        self.movementQueue.append(toAdd)


    @staticmethod
    def setStepperMovementSpeed(speed):
        if not isinstance(speed, float):
            raise TypeError("Stepper movement speed must be a float type object.")
        CustomStepper.MOVMENT_SPEED = speed

    @staticmethod
    def enableAllSteppers():
        for stepper in CustomStepper.STEPPER_OBJECT_LIST:
            CustomStepper.enableStepper(stepper)

    @staticmethod
    def disableAllSteppers():
        for stepper in CustomStepper.STEPPER_OBJECT_LIST:
            CustomStepper.disableStepper(stepper)


    @staticmethod
    def forceStopAllMotion():
        for stepper in CustomStepper.STEPPER_OBJECT_LIST:
            CustomStepper.forceStopMotion(stepper)
    
    @staticmethod
    def allowAllMotion():
        for stepper in CustomStepper.STEPPER_OBJECT_LIST:
            CustomStepper.allowMotion(stepper)



#======================================THREADS==================================
    def _movement_queue_thread(self, threadName):
        """
        This is a the thread to continuously check for movement requestes.
        When a movement is in the queue, this commands the stepper to move to each.
        """
        ProgramLogger.info(f"[THREAD START] Started thread: {threadName}")
        while self.shutdown_flag == False:
            if len(self.movementQueue) != 0 and self.isInMotion == False and self.haltMotion == False:
                self.isInMotion = True
                nextMove = self.movementQueue.pop(0)
                waitTime = nextMove[1]
                nextPosition = nextMove[0]
                ProgramLogger.debug(f"[THREAD {threadName}] New movement: {str(nextPosition)} Hold Time: {waitTime}")
                self.moveToPosition(threadName, newPosition=nextPosition)
                if waitTime != None:
                    ProgramLogger.info(f"[THREAD {threadName}] Holding for: {str(waitTime)} seconds")
                    time.sleep(waitTime)
                    self.isInMotion = False
                else:
                    self.isInMotion = False
            elif self.haltMotion == True:
                self.movementQueue.clear()