================================================================================
 OFFLINE TRANSPORT DELAY ATTRIBUTION SYSTEM
 README — Version 1.0
================================================================================


1. PROJECT OVERVIEW
-------------------
The Offline Transport Delay Attribution System reads raw transit schedule and
arrival data from local CSV files, classifies each delay record by its most
likely cause, and produces a human-readable attribution report. It exists to
give transport authority engineers and planners a fast, repeatable way to
identify where and why delays are occurring — without relying on any external
service. The system runs entirely on a local machine: no internet connection
is required, no API calls are made, no database is needed, and no machine
learning or AI is involved. All decisions are made by a fixed set of
rule-based heuristics (plain if/then logic) applied in a defined priority
order. This makes the system fully auditable — every classification can be
traced back to a specific threshold or condition in the code.


2. INPUT DATA
-------------
The system reads a single input file: transport_data_processed.csv
Place this file in the same folder as the scripts before running.

Required fields
---------------
Field                    Type      Description                  Example
------------------------ --------- ---------------------------- ----------------
Scheduled_Arrival        Datetime  Timetabled stop arrival      2024-03-15 08:30
Actual_Arrival           Datetime  Observed stop arrival        2024-03-15 08:42
Dwell_Time_Sec           Integer   Seconds spent at stop        245
Distance_to_Prev_Stop    Float     Km from previous stop        3.7
Route_ID                 String    Route identifier             R-101
Stop_ID                  String    Stop identifier              S-14
Prev_Stop_Departure_Time Datetime  Departure from prior stop    2024-03-15 08:15

Optional fields
---------------
Any additional columns present in the CSV are preserved in the output but
are not used by the classification logic. They will not cause errors.

Note on datetime format: all datetime fields must follow the format
YYYY-MM-DD HH:MM:SS. Rows with unparseable datetime values will be
skipped with a warning printed to the console.


3. DELAY CAUSE CLASSIFICATION
------------------------------
Each record is assessed against the rules below, in the order listed.
The first rule that matches is applied (first match wins). If no rule
matches, the record is labelled "Normal".

  a) Normal
     Trigger : Delay is less than 5 minutes
                 (Actual_Arrival - Scheduled_Arrival < 5 min)
     Meaning : Arrival is within acceptable operational tolerance.
               No action required.

  b) Excessive Stop Dwell Time
     Trigger : Dwell_Time_Sec is greater than 180 seconds (3 minutes)
     Meaning : The vehicle idled at the stop longer than expected.
               Possible causes include high passenger boardings,
               accessibility ramp use, or a minor mechanical issue.

  c) Vehicle Turnaround Delay
     Trigger : The delay occurs at the first stop of the route
                 (Stop_ID equals "S-1")
     Meaning : The vehicle was late leaving the depot or terminal.
               This points to an operational or scheduling issue at
               the origin point, not along the route itself.

  d) Route Congestion Pattern
     Trigger : More than 3 records at the same Stop_ID each show a
               delay greater than 10 minutes
     Meaning : Multiple vehicles are delayed at the same location,
               which suggests systemic road congestion rather than
               a one-off incident.

  e) Unrealistic Timetable
     Trigger : The scheduled travel time between two consecutive stops
               implies a speed faster than 1 km per 2 minutes
                 (i.e., scheduled rate < 2 min/km)
     Meaning : The timetable requires the vehicle to travel faster
               than is physically achievable in normal conditions.
               The schedule itself is the root cause of the delay.


4. PIPELINE / HOW TO RUN
--------------------------
Run the scripts in the order listed below. Each script produces output
that the next script depends on. Open a terminal (or VS Code integrated
terminal) in the project folder before running any command.

  Step 1 — Prepare input data
    Ensure transport_data_processed.csv is in the project folder.
    No script is needed for this step.

  Step 2 — Apply classification rules
    Script  : 2_process_logic.py
    Command : python 2_process_logic.py
    What it does : Reads the input CSV, applies the delay cause rules,
                   and writes the results to analyzed_delays.csv.

  Step 3 — Generate the attribution report
    Script  : 3_generate_report.py
    Command : python 3_generate_report.py
    What it does : Reads analyzed_delays.csv and writes the
                   human-readable summary to Final_Attribution_Report.txt.

Each script prints a confirmation message to the console when it
finishes. If an error occurs, an [ERROR] message will describe the
problem and the script will stop without producing output.


5. OUTPUT FILES
---------------
Two files are produced after a successful run:

  analyzed_delays.csv
    The original input data with one additional column: Delay_Cause.
    Each row contains the classification label assigned by Step 2.
    This file can be opened in Excel or any CSV viewer for further
    analysis.

  Final_Attribution_Report.txt
    A plain-text summary report intended for stakeholder review.
    Includes an executive summary (total delays, most common cause)
    and a route-by-route breakdown showing problem stops and their
    associated delay causes. Routes are sorted from most delayed to
    least delayed.


6. REQUIREMENTS
---------------
  - Python 3.7 or later
      Check your version: python --version

  - pandas (the only external library required)
      Install with: pip install pandas

No other libraries, tools, or network access are required.
The scripts use only pandas and Python's built-in standard library.


7. LIMITATIONS AND ASSUMPTIONS
--------------------------------
  - Rule priority : Rules are applied in the fixed order shown in
    Section 3. If a record qualifies for more than one cause, only
    the first matching rule is applied. To change priority, edit the
    rule order in 2_process_logic.py.

  - Hardcoded thresholds : The values below are defined as constants
    near the top of 2_process_logic.py. Edit them there if the
    transport authority's operational standards differ.
      - 5 minutes    : maximum delay classed as Normal
      - 180 seconds  : dwell time threshold for Excessive Dwell
      - 10 minutes   : per-stop delay threshold for Congestion Pattern
      - 3 records    : minimum occurrences to confirm Congestion Pattern
      - 2 min/km     : minimum scheduled rate for Unrealistic Timetable
      - "S-1"        : Stop_ID used to identify the first stop

  - No real-time data : The system processes static CSV snapshots only.
    It is not designed to ingest live feeds or streaming data.

  - Clean input assumed : The scripts do not repair corrupt rows,
    duplicate records, or inconsistent ID formats. Ensure input data
    has been cleaned before running Step 2.

  - Single-file input : The system expects one consolidated CSV file.
    It does not merge data from multiple source files automatically.


================================================================================
 END OF README
================================================================================
