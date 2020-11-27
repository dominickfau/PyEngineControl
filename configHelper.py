import customExceptions, configparser, folderGenerator, configHelper, os, os.path

#========================================VARIABLES========================================
STEPPER_COFIG_FILE_NAME = folderGenerator.findFullPath('Configs') + "StepperConfig.ini"
PROGRAM_COFIG_FILE_NAME = folderGenerator.findFullPath('Configs') + "ProgramConfig.ini"

PROGRAM_LOG_FILE_NAME = folderGenerator.findFullPath('Logs') + "ProgramLog.txt"



def readConfigFile(cofigFileName):
    configData = {}
    config = configparser.ConfigParser()
    config.read(cofigFileName)
    for sect in config.sections():
        item = {}
        for k,v in config.items(sect):
            item[k] = v
        configData[sect] = item
    return configData


def readConfigSection(cofigFileName, section):
    config = configparser.ConfigParser()
    config.read(cofigFileName)
    sectionOptions= {}
    if config.has_section(section):
        items = config.items(section)
        for item in items:
            sectionOptions[item[0]] = item[1]
    else:
        raise customExceptions.NoSectionError('Section: [{0}] not found in Config File: [{1}]'.format(section, cofigFileName))
    return sectionOptions # Return a dictionary of the section options


def updateConfigSection(cofigFileName, section, key, value):
    config = configparser.ConfigParser()
    config.read(cofigFileName)
    config.set(section, key, value)
    with open(cofigFileName, 'w') as configfile:
        config.write(configfile)
    configfile.close()
    return


def generateAllConfigs():
    generateStepperConfig()
    generateProgramConfig()


def generateStepperConfig():
    if not os.path.isfile(STEPPER_COFIG_FILE_NAME):
        config = configparser.ConfigParser()

        # Define sections with Key: Value pairs
        config['Stepper1'] = {'steps_per_rev': '200',
                            'range_of_motion': '1',
                            'invert_direction': 'False',
                            'arduino_step_pin': '5',
                            'arduino_direction_pin': '6',
                            'arduino_enable_pin': '7'
                            }

        config['Stepper2'] = {'steps_per_rev': '200',
                            'range_of_motion': '1',
                            'drive_reduction': '0.5',
                            'invert_direction': 'False',
                            'arduino_step_pin': '8',
                            'arduino_direction_pin': '9',
                            'arduino_enable_pin': '10'
                            }


        with open(STEPPER_COFIG_FILE_NAME, 'w') as configfile:
            config.write(configfile)
        configfile.close()


def generateProgramConfig():
    if not os.path.isfile(PROGRAM_COFIG_FILE_NAME):
        config = configparser.ConfigParser()

        # Define sections with Key: Value pairs
        config['Logging'] = {'log_verbosity': 'DEBUG',
                            'log_file_size_limit': '20000'
                            }


        with open(PROGRAM_COFIG_FILE_NAME, 'w') as configfile:
            config.write(configfile)
        configfile.close()