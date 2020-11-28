import os, csv

PARENT_DIR = os.getcwd()
CSV_FILES = {'RunProgram': ['Line', 'MoveTo', 'HoldFor']
            }

CHILD_DIRS = {'Data': ['Logs', 'Configs', 'Templates']
            }


def generateFolders():
    """
        Generates full folder structure.
    """
    for key in CHILD_DIRS:
        mainPath = os.path.join(PARENT_DIR, key)
        try:
            os.mkdir(mainPath)
        except FileExistsError:
            pass
        if CHILD_DIRS[key] != None:
            for folder in CHILD_DIRS[key]:
                childPath = os.path.join(mainPath, folder)
                try:
                    os.mkdir(childPath)
                except FileExistsError:
                    pass
                if key == 'Data':
                    for csvKey in CSV_FILES:
                        csvFile = csvKey + ".csv"
                        fileToMake = os.path.join(childPath, csvFile)
                        if folder == 'Templates':
                            with open(fileToMake, 'w') as csvfile:
                                csvwriter = csv.writer(csvfile)
                                # Write Colunm names
                                csvwriter.writerow(CSV_FILES[csvKey])


def getParentDir():
    """
        Returns the full path the current working dir.
    """
    return PARENT_DIR + '\\'


def getFullPath(folder):
    """
        Returns full path (from the current working dir) to the folder name provided.
    """
    return os.path.join(PARENT_DIR, folder)


def findFullPath(folderToFind):
    """
        Returns full path to the folder name provided.
        Raises FileNotFoundError if folder not found.
    """
    generateFolders()
    folderFound = False
    for key in CHILD_DIRS:
            mainPath = os.path.join(PARENT_DIR, key)
            if CHILD_DIRS[key] != None:
                for folder in CHILD_DIRS[key]:
                    childPath = os.path.join(mainPath, folder, "")
                    if folder == folderToFind:
                        folderFound = True
                        fullPath = childPath
    if folderFound:
        return fullPath
    else:
        raise FileNotFoundError(f"Could not find folder: {folderToFind}")