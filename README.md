Overview:
    edit_net.py is a script that converts a single ended ECL netlist from Genus and modifies the netlist 
    to represent the differential inputs/outputs of the gates.
        - Adds port compliments to the cells
        - Adds ECL Reference Cells (Current and Voltage)
        - Connects every cell to their respective Reference Cell
        - Adds Tie-Hi/Lo cells to the netlist

Script Usage:
	** NEEDS ATLEAST PYTHON3.11 **
		- See "Creating Python Virtual Environment" Section
	Takes in gate-level verilog netlist (*.v)
    Takes in a json config file to change certain behaviors in the netlist
        - allows mapping of different cell names found in the verilog netlist

Creating Python Virtual Environment:
	1)  If you have a version of python already installed, check which version it is by running
		the following in the command line:
			"python3.11 --"
				-If this launches the python interpreter, you have python3.11 already installed, to exit simply type "exit() and move to step 3"	
	2)	If Python3.11 is not installed, go to python.org and install Python3.11 or higher, follow the instructions
		on the installer then move on to the next step.
	3)	While inside this repo's main folder (ECL_Synthesis_Tool), run the following line:
			"python3.11 -m venv .venv/"
				-This creates a virtual environment folder named .venv/ in the directory.
	4) Now, before running edit_net.py, you must first invoke the virtual environment with the following:
			"source .venv/bin/activate"

Running the script:
	1) Start the python3.11 virtual environment using the above command
	2) Type the following into the terminal:
		"python edit_net.py"
			
