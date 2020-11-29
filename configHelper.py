import customExceptions, configparser, folderGenerator, configHelper, os, os.path, errno

#========================================VARIABLES========================================
STEPPER_COFIG_FILE_NAME = folderGenerator.findFullPath('Configs') + "StepperConfig.ini"
PROGRAM_COFIG_FILE_NAME = folderGenerator.findFullPath('Configs') + "ProgramConfig.ini"

PROGRAM_LOG_FILE_NAME = folderGenerator.findFullPath('Logs') + "ProgramLog.txt"


def readConfigFile(cofigFilePath):
    """Reads entire config file, parses and returns a dictionary object.

    Args:
        cofigFileName (string): Full file path to config file to read from.
    
    Raises:
        FileNotFoundError: Raised if the specified file does not exist.

    Returns:
       dictionary : All sections, items, and values in a format like this
                    {sectionName: {item: value, ...}, ...}
    """
    if not os.path.isfile(cofigFilePath):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), cofigFilePath)
    configData = {}
    config = configparser.ConfigParser()
    config.read(cofigFilePath)
    for sect in config.sections():
        item = {}
        for k,v in config.items(sect):
            item[k] = v
        configData[sect] = item
    return configData


def readConfigSection(cofigFilePath, section):
    """Reads specific config file section, parses and returns a dictionary object.

    Args:
        cofigFilePath (string): Full file path to config file to read from.
        section (string): Name of section to return data from.

    Raises:
        FileNotFoundError: Raised if the specified file does not exist.
        customExceptions.NoSectionError: Raised if specified section does not exist.

    Returns:
        dictionary : item: value for each item in the section.
    """
    if not os.path.isfile(cofigFilePath):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), cofigFilePath)
    config = configparser.ConfigParser()
    config.read(cofigFilePath)
    sectionOptions= {}
    if config.has_section(section):
        items = config.items(section)
        for item in items:
            sectionOptions[item[0]] = item[1]
    else:
        raise customExceptions.NoSectionError('Section: [{0}] not found in Config File: [{1}]'.format(section, cofigFilePath))
    return sectionOptions


def updateConfigSection(cofigFilePath, section, key, value):
    """Updates the specific config file section.

    Args:
        cofigFilePath (string): Full file path to config file to read from.
        section (string): Name of section where key is found.
        key (string): Key name to update.
        value (string): New value for the key.

    Raises:
        FileNotFoundError: Raised if the specified file does not exist.
    """
    if not os.path.isfile(cofigFilePath):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), cofigFilePath)
    config = configparser.ConfigParser()
    config.read(cofigFilePath)
    config.set(section, key, value)
    with open(cofigFilePath, 'w') as configfile:
        config.write(configfile)
    configfile.close()
    return


def generateAllConfigs():
    """Call this method to check for and generate all config files needed.
    """
    generateStepperConfig()
    generateProgramConfig()


def generateStepperConfig():
    """Checks if stepper config file exists, if not create and fill with default data.
    """
    if not os.path.isfile(STEPPER_COFIG_FILE_NAME):
        config = configparser.ConfigParser()

        # Define sections with Key: Value pairs
        config['StepperOne'] = {'steps_per_rev': '200',
                            'range_of_motion': '1',
                            'invert_direction': 'False',
                            'arduino_step_pin': '5',
                            'arduino_direction_pin': '6',
                            'arduino_enable_pin': '7'
                            }

        config['StepperTwo'] = {'steps_per_rev': '200',
                            'range_of_motion': '1',
                            'drive_ratio': '0.5',
                            'invert_direction': 'False',
                            'arduino_step_pin': '8',
                            'arduino_direction_pin': '9',
                            'arduino_enable_pin': '10'
                            }


        with open(STEPPER_COFIG_FILE_NAME, 'w') as configfile:
            config.write(configfile)
        configfile.close()


def generateProgramConfig():
    """Checks if program config file exists, if not create and fill with default data.
    """
    if not os.path.isfile(PROGRAM_COFIG_FILE_NAME):
        config = configparser.ConfigParser()

        # Define sections with Key: Value pairs
        config['Logging'] = {'log_verbosity': 'WARNING',
                            'log_file_size_limit': '20000'
                            }

        config['GlobalStepperParms'] = {'inactivity_timeout': '200'
                            }


        with open(PROGRAM_COFIG_FILE_NAME, 'w') as configfile:
            config.write(configfile)
        configfile.close()

generateAllConfigs()