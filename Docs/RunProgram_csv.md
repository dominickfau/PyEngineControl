# Run program csv file settup

Below is a template and explenation of how to run programed routines from a .csv file. 
    The order of the columns is not important, as long as all of the required columns are present.

Column Names | Value Type | Description
------------ | ---------- | -----------
Line (Required) | Hole Number | This is a running total of all lines in the file.
MoveTo (Required) | Decimal | Next position to move to. Percentage of object's total range of motion.
HoldFor (Required) | Decimal | Time in seconds to hold each position for before moving to the next.

File naming doen't matter, but the file type MUST be .csv.

Here is a sample file to test with.
```csv
Line,MoveTo,HoldFor
1,5,0.1
2,2,0.1
3,20,0.1
4,50,0.1
5,15,0.1
6,30,0.1
7,22,0.1
8,40,0.1
9,80,0.1
10,60,0.1
11,28,0.1
12,0,0.1
13,55,0.1
14,25,0.1
15,0,0.1
16,100,0.1
17,3,0.1
18,26,0.1
19,90,0.1
20,0,0.1

```