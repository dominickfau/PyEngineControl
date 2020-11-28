import  codeUtilitys, time, configHelper, configLogging, threading, customExceptions

PROGRAM_LOG_FILE_NAME = configHelper.PROGRAM_LOG_FILE_NAME
PROGRAM_COFIG_FILE_NAME = configHelper.PROGRAM_COFIG_FILE_NAME
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

        self.stepperName = stepperName
        self.currentPosition = 0.0
        self.stepperActive = False
        self.lastMovmentTime = None
        self.isInMotion = False
        self.movmentQueue = []
        self.startTime = time.time()

        # Start stepper movment thread.
        threadName = self.stepperName + '_Movment_Queue'
        self.the_movment_queue_thread = threading.Thread(target=self._movment_queue_thread, args=(threadName,))
        self.the_movment_queue_thread.daemon = True
        self.the_movment_queue_thread.name = threadName
        self.the_movment_queue_thread.start()

        pinsUsed = []
        try:
            self.steps_per_rev = int(options['steps_per_rev'])
            self.range_of_motion = float(options['range_of_motion'])
            self.invert_direction = bool(options['invert_direction'])

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
        self._stop_threads()



    def enableStepper(self):
        self.lastMovmentTime = time.time()
        self.stepperActive = True
        CustomStepper.BOARD.digital_write(self.arduino_enable_pin, 1)
        ProgramLogger.info(f"Stepper: [{self.stepperName}] ENABELED.")

    def disableStepper(self):
        self.stepperActive = False
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
        tStart = time.time()
        for x in range(numberOfSteps):
            CustomStepper.BOARD.digital_write(self.arduino_step_pin, 1)
            CustomStepper.BOARD.digital_write(self.arduino_step_pin, 0)
            self.lastMovmentTime = time.time()
        
        tEnd = time.time()
        ProgramLogger.debug(f"[THREAD {threadName}] Stepper: [{self.stepperName}] at commanded position. Execution Time: {str(tEnd - tStart)}")

    def moveToPosition(self, threadName, newPosition, waitTime):
        self.isInMotion = True
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
        if waitTime != None:
            ProgramLogger.info(f"[THREAD {threadName}] Holding for: {str(waitTime)} seconds")
            time.sleep(waitTime)
        self.isInMotion = False



    def addMoveToQueue(self, newPosition, holdTime=None):
        if newPosition < 0.0 or newPosition > 100.0:
            raise customExceptions.OutOfRangeError(f"Stepper: [{self.stepperName}] new position [{str(newPosition)}] outside of allowed range 0-100.")
        toAdd = [newPosition, holdTime]
        self.movmentQueue.append(toAdd)


    @staticmethod
    def setStepperMovmentSpeed(speed):
        if not isinstance(speed, float):
            raise TypeError("Stepper movment speed must be a float type object.")
        CustomStepper.MOVMENT_SPEED = speed

    @staticmethod
    def enableAllSteppers():
        for stepper in CustomStepper.STEPPER_OBJECT_LIST:
            CustomStepper.enableStepper(stepper)

    @staticmethod
    def disableAllSteppers():
        for stepper in CustomStepper.STEPPER_OBJECT_LIST:
            CustomStepper.disableStepper(stepper)





#======================================THREADS==================================
    def _movment_queue_thread(self, threadName):
        """
        This is a the thread to continuously check for movment requestes.
        """
        ProgramLogger.info(f"[THREAD START] Started thread: {threadName}")
        while self.shutdown_flag == False:
            if len(self.movmentQueue) != 0:
                self.isInMotion = True
                nextMove = self.movmentQueue.pop(0)
                ProgramLogger.debug(f"[THREAD {threadName}] New movment: {str(nextMove[0])} Hold Time: {nextMove[1]}")
                self.moveToPosition(threadName, newPosition=nextMove[0], waitTime=nextMove[1])
                while self.isInMotion:
                    time.sleep(0.0001)
            else:
                pass