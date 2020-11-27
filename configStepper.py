class CustomStepper:
    MOVMENT_SPEED = None

    @staticmethod
    def setStepperMovmentSpeed(speed):
        if not isinstance(speed, float):
            raise TypeError("Stepper movment speed must be a float type object.")
        CustomStepper.MOVMENT_SPEED = speed


    def __init__(self, stepperName, options):
        if not isinstance(options, dict):
            raise TypeError("Stepper config options must be a dictionary type object.")
        
        self.stepperName = stepperName
        try:
            self.steps_per_rev = options['steps_per_rev']
            self.invert_direction = options['invert_direction']
            self.arduino_step_pin = options['arduino_step_pin']
            self.arduino_direction_pin = options['arduino_direction_pin']
            self.arduino_enable_pin = options['arduino_enable_pin']
        except KeyError as err:
            raise KeyError(f"Missing required config option Key: {err}")