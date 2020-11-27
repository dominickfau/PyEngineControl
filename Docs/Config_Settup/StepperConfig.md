# Stepper config file settup

### Valid config sections.
Below is the structure requiered for each stepper connected to the arduino. The parameter order does not matter.
    NOTE: Replace 'NameOfSection' with what the stepper motors name should be.
    The name must be in [CamelCase,](https://en.wikipedia.org/wiki/Camel_case) format.
    When this name is shown on screen, spaces will be added just before the capitalized letters.

* **NameOfSection**
    * **steps_per_rev: (integer), Stepper motors steps per revolution. If microstepping is being used, the equivalent pulse\rev number.**
    * **range_of_motion: (decimal), Defines the number of rotaions the object being moved can rotate.**
    * **invert_direction: (boolean), Inverts motor direction when Ture.**
    * **arduino_step_pin: (integer), The arduino pin used for the step signal on the stepper motor driver.**
    * **arduino_direction_pin: (integer), The arduino pin used for the direction signal on the stepper motor driver.**
    * **arduino_enable_pin: (integer), The arduino pin used for the enable signal on the stepper motor driver.**
    * **drive_reduction: (decimal), Optional parameter, defaults to 1. If declared, the range_of_motion value is multiplyed by this number. IE. 2:1 reduction = 2, 1:2 = 0.5**


Here is what the default StepperConfig.ini looks like.
'''ini
[Stepper1]
steps_per_rev = 200
range_of_motion = 1
invert_direction = False
arduino_step_pin = 5
arduino_direction_pin = 6
arduino_enable_pin = 7

[Stepper2]
steps_per_rev = 200
range_of_motion = 1
drive_reduction = 0.5
invert_direction = False
arduino_step_pin = 8
arduino_direction_pin = 9
arduino_enable_pin = 10
'''