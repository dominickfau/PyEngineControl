import logging

def createLogger(moduleName, logFileName, logVerbosity, logFormat='%(asctime)s  %(name)s - %(levelname)s: %(message)s'):
    """Create a logging instance and return it.

    Args:
        moduleName (string): __name__ variable from the calling file.
        logFileName (string): Full file path to the log file to write to.
        logVerbosity (string): Valid options are DEBUG, INFO, WARNING, ERROR, CRITICAL
        logFormat (string, optional): Format string for each line writen to log file. Defaults to '%(asctime)s  %(name)s - %(levelname)s: %(message)s'.

    Returns:
        object: logging.getLogger() instance.
    """
    startMessage = "[START] Program started."
    if moduleName == '__main__':
        with open(logFileName, 'a') as logFile:
            logFile.write(f'\n{startMessage}\n')
        logFile.close()
    #Create and configure logger
    logging.basicConfig(filename=logFileName, format=logFormat, filemode='a', datefmt='%m/%d/%Y %I:%M:%S %p')
    #Create a logging object
    logger = logging.getLogger(moduleName)
    #Setting the threshold of logger
    logger.setLevel(logVerbosity)
    return logger