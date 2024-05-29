Overview:
    edit_net.py is a script that converts a single ended ECL netlist from Genus and modifies the netlist 
    to represent the differential inputs/outputs of the gates.
        - Adds port compliments to the cells
        - Adds ECL Reference Cells (Current and Voltage)
        - Connects every cell to their respective Reference Cell
        - Adds Tie-Hi/Lo cells to the netlist

Script Usage:
    Takes in gate-level verilog netlist (*.v)
    Takes in a json config file to change certain behaviors in the netlist
        - allows mapping of different cell names found in the verilog netlist

