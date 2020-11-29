import os, os.path, re

def getFileSize(fileName):
    """Gets file size in KB for the file specified.

    Args:
        fileName (string): Name of file to check, or full path to file.

    Returns:
        float: Size of file in KB.
    """
    st = os.stat(os.path.abspath(fileName))
    return float(st.st_size / 1000)


def amendSpacesToString(inputString):
    """Takes a CamalCase string and addes spaces just before each capital letter.

    Args:
        inputString (String): CamalCase string to add spaces to.

    Returns:
        String: Input string with spaces added just before each capital letter, then strips spaces from string ends..
    """
    words = re.findall('[A-Z][a-z]*', inputString)
    stringList = []
    for word in words:
        stringList.append(word)
    return ' '.join(stringList).strip()