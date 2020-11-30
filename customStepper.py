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
    # Used for global enable/ disable.
    STEPPER_OBJECT_LIST = []
    MOVMENT_SPEED = None
    BOARD = None
    TOTAL_PINS_USED = []

    def __init__(self, stepperName, options):
        if not isinstance(options, dict):
            raise TypeError("Stepper config options must be a dictionary type object.")
        CustomStepper.STEPPER_OBJECT_LIST.append(self)

        threading.Thread.__init__(self)
        self.run_event = threading.Event()

        # flag to indicate we are in shutdown mode
        self.shutdown_flag = False

        self.haltMotion = False

        self.name = stepperName
        self.currentPosition = 0.0
        self.stepperActive = False
        self.lastMovementTime = None
        self.isInMotion = False
        self.moveDirection = 0
        self.startTime = time.time()

        # flag used for debuging
        self.lineCount = 0


        self.pinNumbersUsed = []
        try:
            self.steps_per_rev = int(options['steps_per_rev'])
            self.range_of_motion = float(options['range_of_motion'])
            self.invert_direction = bool(options['invert_direction'])
            self.invert_enable_pin = bool(options['invert_enable_pin'])
            self.arduino_step_pin = int(options['arduino_step_pin'])
            self.arduino_direction_pin = int(options['arduino_direction_pin'])
            self.arduino_enable_pin = int(options['arduino_enable_pin'])

            self.pinNumbersUsed.append(self.arduino_step_pin)
            self.pinNumbersUsed.append(self.arduino_direction_pin)
            self.pinNumbersUsed.append(self.arduino_enable_pin)
        except KeyError as err:
            raise KeyError(f"Missing required config option Key: {err}")

        if 'drive_ratio' in options:
            self.drive_ratio = float(options['drive_ratio'])
        else:
            self.drive_ratio = 1.0

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
        ProgramLogger.info(f"Stepper: [{self.name}] FORCED STOP.")
        self.disableStepper()

    def allowMotion(self):
        self.haltMotion = False
        ProgramLogger.info(f"Stepper: [{self.name}] Allowed to move.")

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