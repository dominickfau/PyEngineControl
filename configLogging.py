import logging


#TODO: Add doc string.
def createLogger(moduleName, logFileName, logVerbosity, logFormat='%(asctime)s  %(name)s - %(levelname)s: %(message)s'):
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