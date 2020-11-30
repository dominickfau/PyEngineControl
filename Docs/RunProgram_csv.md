# Run program csv file settup

Below is a template and explanation of how to run programed routines from a .csv file. 
    The order of the columns is not important, as long as all of the required columns are present.
    Under Data/Templates is a file named RunProgram.csv, this file is generated after successfully connecting to the arduino. It's recommended to add/ change the StepperConfig.ini file, then have the software regenerate this .csv file instead of adding/ changing the column headers. If needed, after regenerating copy and paste the new header line to the appreciate file.
    
**Side Note** When a file is processed. Rows are read line by line from left to right, each move value is then added to movement queue in the same order as the file. Moves in the movement queue are then sent in the order they where added. So if one stepper need to more before another, put that stepper before the other.
    
**DO NOT save any files under Data/Templates**, this folder is purged and new updated template files made every time the program is started.

Column Name | Value Type | Description
------------ | ---------- | -----------
Line (Required) | Hole Number | This is a running total of all lines in the file.
Stepper Name (Auto Gen, Required) | Decimal | This column name MUST match the section names used in [StepperConfig.ini,](https://github.com/dominickfau/PyEngineControl/blob/master/Docs/Config_Settup/StepperConfig.md), this is to show what column is for what stepper. Next position to move to, percentage of object's total range of motion.
HoldTime (Required) | Decimal | Time in seconds to hold each position for before moving to the next line. If a 0 HoldTime is needed, Use the value *None* in place of 0.


Here is a sample file to test with.
```csv
Line,StepperOne,StepperTwo,HoldTime
1,0,0,None
2,50,45,1
3,23,75,1
4,60,62,1
5,10,10,1
6,25,45,1
7,75,65,1
8,0,36,1
9,100,100,1
10,66,58,1
11,34,37,1
12,85,10,1
13,42,25,1
14,14,90,1
15,0,0,1
16,8,5,1
17,0,55,1
18,0,4,1
19,100,100,None
20,0,0,None

```