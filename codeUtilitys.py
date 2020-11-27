import os, os.path, re


def getFileSize(fileName):
    """Gets file size in KB for the file specified.

    Args:
        fileName (str): Name of file to check, or full path to file.

    Returns:
        float: Size of file in KB.
    """
    st = os.stat(os.path.abspath(fileName))
    return float(st.st_size / 1000)

#TODO: Add doc string.
def amendSpacesToString(inputString):
    words = re.findall('[A-Z][a-z]*', inputString)
    stringList = []
    for word in words:
        stringList.append(word)
    return ' '.join(stringList)