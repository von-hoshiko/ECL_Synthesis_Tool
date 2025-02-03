import sys
import os
from pprint import pprint
import re
import json
from math import ceil
import glob

# invert_affix = "_bar"
invert_affix = "_bar"


class cell:
    global total_gates
    global total_or_gates
    global num_tie

    def __init__(self):
        self.cell_type = ""
        self.cell_name = ""
        self.cell_ports = {}
        self.cell_id = ""
        self.tied_ports = {"Ti_Hi": [], "Ti_Lo": []}

    def __str__(self):
        return "{} {}{};".format(config["custom_cell_map"][self.cell_type], self.cell_name, self.create_param_str())
    
    def fill_cell(self, gate_def: str):
        global total_gates
        global total_or_gates
        # self.cell_type = config[gate_def.split()[0]]
        self.cell_type = cell_map.get(gate_def.split()[0])
        if self.cell_type == None:
            print("Unrecognized cell: {}\nPlease make sure you have properly mapped this cell in the config.json file under custom_cell_map".format(gate_def.split()[0]))
            exit(1)
        
        #keeps track of how many Reference Circuits to place down
        total_gates = total_gates + 1;
        if self.cell_type == "ECL_OR": total_or_gates += 1

        self.cell_name = gate_def.split()[1][:gate_def.split()[1].find("(")] if (gate_def.split()[1].find("(") != -1) else (gate_def.split()[1] + " ")
        params = gate_def[gate_def.find("(") + 1:gate_def.rfind(")")].split(',')
        params = [strip_pair.strip() for strip_pair in params]
        # print(params);
        self.parse_ports(params)
        
    def parse_ports(self, params: list):
        global num_tie
        q_net = None
        qbar_net = None

        if(self.cell_type == "ECL_DFFSR"):
            ports = [None] * len(params)
            nets = [None] * len(params)
            for index, pair in enumerate(params):
                ports[index] = pair.split()[0][1:]
                nets[index] = pair.split()[1].strip("()")                
            self.cell_ports = {key:val for (key,val) in zip(ports, nets)}

            # if "UNCONNECTED" in self.cell_ports["Q"]: 
            #     self.cell_ports["Q"] = invert_net(self.cell_ports["QBAR"])
            # elif "UNCONNECTED" in self.cell_ports["QBAR"]: 
            #     self.cell_ports["QBAR"] = invert_net(self.cell_ports["Q"])
            if "UNCONNECTED" not in self.cell_ports["Q"]:
                self.cell_ports["QBAR"] = invert_net(self.cell_ports["Q"])
            else:
                self.cell_ports["Q"] = invert_net(self.cell_ports["QBAR"])

            self.cell_ports["DBAR"] = invert_net(self.cell_ports["D"])
            if "'b" in self.cell_ports["D"]:
                num_tie += 2
                if self.cell_ports["D"][-1] == "0": self.tied_ports["Ti_Lo"].append("D")
                if self.cell_ports["D"][-1] == "1": self.tied_ports["Ti_Hi"].append("D")
                if self.cell_ports["DBAR"][-1] == "0": self.tied_ports["Ti_Lo"].append("DBAR")
                if self.cell_ports["DBAR"][-1] == "1": self.tied_ports["Ti_Hi"].append("DBAR")
            

            self.cell_ports["CLKBAR"] = invert_net(self.cell_ports["CLK"])
            if "'b" in self.cell_ports["SET"]: 
                num_tie += 1
                if self.cell_ports["SET"][-1] == "0": self.tied_ports["Ti_Lo"].append("SET")
                if self.cell_ports["SET"][-1] == "1": self.tied_ports["Ti_Hi"].append("SET")
            if "'b" in self.cell_ports["RESET"]: 
                num_tie += 1
                if self.cell_ports["RESET"][-1] == "0": self.tied_ports["Ti_Lo"].append("RESET")
                if self.cell_ports["RESET"][-1] == "1": self.tied_ports["Ti_Hi"].append("RESET")
            # self.cell_ports["CUR"] = ""
            pprint(self.cell_ports)
        else:
            for pair in params:
                port = pair.split()[0][1:]
                net = pair.split()[1].strip("()")

                if self.cell_ports.get(port) != None : continue # This ensures we don't overwrite a port we have already parsed into the cell

                if "'b" in net: 
                    num_tie += 1
                    if net[-1] == "0": self.tied_ports["Ti_Lo"].append(port)
                    if net[-1] == "1": self.tied_ports["Ti_Hi"].append(port)
                self.cell_ports[port] = net
                
                port_complement = config["port_compliments"][self.cell_type].get(port)
                # print(port_complement)
                if port_complement != None:
                    # print("comp {}\n".format(port_complement))
                    # netbar = self.invert_net(net)
                    netbar = invert_net(net)
                    # print("Inverting net: {}    netbar: {}\n".format(net, netbar))
                    self.cell_ports[port_complement] = netbar
                    if "'b" in netbar: 
                        num_tie += 1
                        if netbar[-1] == "0": self.tied_ports["Ti_Lo"].append(port_complement)
                        if netbar[-1] == "1": self.tied_ports["Ti_Hi"].append(port_complement)                    
        
        self.cell_ports["CUR"] = ""
        if self.cell_type == "ECL_OR": self.cell_ports["REF"] = ""
        

    def create_param_str(self):
        p_str = []
        for port, net in self.cell_ports.items():
            #space added before ")" for cases where a net is of the case "\net_name[0] "
            pair = ".{} ({} )".format(port, net)
            p_str.append(pair)
            
        return "({})".format(", ".join(p_str))
    
def invert_net(net: str) -> str: # We need to be able to go from (net -> net_bar) forwards and also from (net_bar->net) reversed
    global invert_affix
    reverse = 0 # handles if we want to chop off invert_affix
    if "'b" in net:
        netbar = "{}{}".format(net[:-1], abs(int(net[-1]) - 1))
        # num_tie += 1
    else:
        net_bit_width = ""

        if "[" in net and net.endswith("]"): #checking if net has a specfied bitwidth
            net_bit_width = net[net.find("["):net.rfind("]")+1] #parsing the associated bitwidth for the current net
            net = net[:net.find("[")] #gets net name without bitwidth

        if net[-1*len(invert_affix):] == invert_affix: reverse = 1


        if net_bit_width != "":
            netbar = "{}{}{}".format(net, invert_affix, net_bit_width) if reverse == 0 else "{}{}".format(net[:-1*len(invert_affix)], net_bit_width)
        else:
            netbar = "{}{}".format(net, invert_affix) if reverse == 0 else net[:-1*len(invert_affix)]
    return netbar

def replace_assigns(assign_list: list) -> list: 
    # This will replace an assign with an ECL_INV acting as a buffer
    # assign_list is a list of tuples
    # Return a list of single ended ECL_INV cell string that will be fed into the cell.fill_cells() function
    # Ex: (assign net1 = net2;) => (ECL_INV ecl_buf_assign_x(.IN (net2), .INV(net1_bar));) 
    buffers = []

    for i, assign_tuple in enumerate(assign_list):
        cell_str = "ECL_INV ecl_buf_assign_{}(.IN ({}), .INV ({}));".format(i, assign_tuple[1], invert_net(assign_tuple[0]))
        buffers.append(cell_str)

    return buffers

def create_special_cells() -> list:
    global total_gates
    special_list = []
    special_net_list = []

    num_tie_cells = ceil(num_tie/config["tie_cell_fanout"]) * 2 
    num_voltage_ref = ceil((total_or_gates+num_tie_cells/2)/config["reference_cell_fanout"])
    
    total_gates += num_voltage_ref
    total_gates += num_tie_cells
    total_cur_ref = ceil(total_gates/config["reference_cell_fanout"])

    for i in range(ceil(total_gates/config["reference_cell_fanout"])):
        special_list.append("{} current_ref_{} (.current_mirror (CUR_{}));".format(config["custom_cell_map"]["ECL_Reference"], i, i))

    special_list.append("\n")
        
    for i in range(ceil(total_or_gates/config["reference_cell_fanout"])):
        special_list.append("{} voltage_ref_{} (.CUR (CUR_{}), .REF (REF_{}));".format(config["custom_cell_map"]["ECL_Voltage_Reference"], i, int(i/config["reference_cell_fanout"]), i))

    special_list.append("\n")

    for i in range(ceil(num_tie/config["tie_cell_fanout"])):
        special_list.append("{} Tie_Hi_{} (.CUR (CUR_{}), .OUT_HI (Hi_{}));".format(config["custom_cell_map"]["ECL_TIE_HI"], i, int(((2*i)+int(num_voltage_ref/config["reference_cell_fanout"]))/(config["reference_cell_fanout"] - (num_voltage_ref % config["reference_cell_fanout"]))), i))
        # special_list.append("{} Tie_Hi_{} (.CUR (CUR_0), .OUT_HI (Hi_{}));".format(config["custom_cell_map"]["ECL_Tie_Hi"], i, i))
    for i in range(ceil(num_tie/config["tie_cell_fanout"])):
        special_list.append("{} Tie_Lo_{} (.CUR (CUR_{}), .REF(REF_{}), .OUT_LO (Lo_{}));".format(config["custom_cell_map"]["ECL_TIE_LO"], i, int(((2*i)+int(num_voltage_ref/config["reference_cell_fanout"]))/(config["reference_cell_fanout"] - (num_voltage_ref % config["reference_cell_fanout"]))), int(i/config["reference_cell_fanout"]), i))        


    for i in range(total_cur_ref): special_net_list.append("CUR_{}".format(i))
    for i in range(num_voltage_ref) : special_net_list.append("REF_{}".format(i))

    return [special_list, num_voltage_ref + num_tie_cells, special_net_list]

def parse_assign(line: str) -> tuple: 
    # When given a line with format "assign net1 = net2;"
    # returns a tuple (net1,net2)
    split_str = line.split()
    return (split_str[1], split_str[3][:-1])
    pass

def get_assign_compliments(group_assign: list) -> list:
    # creates a list of tuples containing assigned nets
    # Ex: [(net1, net2), (net1_bar, net2_bar), ... , (net(N), net(N+1)), (net(N)_bar, net(N+1)_bar)]
    global num_tie
    assign_list = []
    for pair in group_assign:
        # assign_list.append("assign {} = {}".format(pair[0], pair[1]))
        # assign_list.append("assign {} = {}".format(invert_net(pair[0]), invert_net(pair[1])))
        assign_list.append((pair[0], pair[1]))
        assign_list.append((invert_net(pair[0]), invert_net(pair[1])))
        if "'b" in pair[1]: num_tie += 2 #increments number of tied nets 
    
    # for i in assign_list: print(i)
    # exit()
    return assign_list
            

def get_default_config():
    default_config = {
        "reference_cell_fanout" : 100, 
        "tie_cell_fanout" : 10,
        "reference_cells" : ["ECL_Reference", "ECL_Voltage_Reference"],
        "tie_cells"       : ["ECL_Tie_Hi", "ECL_Tie_Lo"],        
        "custom_cell_map" :{
            "ECL_AND" : "ECL_AND",
            "ECL_OR"  : "ECL_OR",
            "ECL_XOR" : "ECL_XOR",
            "ECL_INV" : "ECL_INV",
            "ECL_DFFSR" : "ECL_DFFSR",
            "ECL_MUX21" : "ECL_MUX21",
            "ECL_Reference" : "ECL_Reference",
            "ECL_Voltage_Reference" : "ECL_Voltage_Reference",
            "ECL_TIE_HI" : "ECL_TIE_HI",
            "ECL_TIE_LO" : "ECL_TIE_LO"
        },
        "port_compliments" : {
            "ECL_AND" : {
                "A" :  "NOTA",
                "B" :   "NOTB",
                "AND" : "NAND"
            },
            "ECL_OR" : {
                "OR" : "NOR"
            },
            "ECL_XOR" : {
                "A" :  "NOTA",
                "B" :  "NOTB",
                "XOR" : "XNOR"
            },
            "ECL_INV" : {
                "IN" : "REF",
                "INV" : "BUF"
            },
            "ECL_DFFSR" : {
                "CLK" : "CLKBAR",
                "D"   : "DBAR",
                "Q"   : "QBAR"
            },
            "ECL_MUX21" : {
                "A" : "NOTA",
                "B" : "NOTB",
                "OUT" : "OUTBAR",
                "S" : "SBAR"
            }
        }        
    }
    return default_config   

def group_statements(file_name: str,statement_list: list, tot_num_gates: int, num_or_gates: int) -> list:
    # global total_gates
    # global total_or_gates
    # checks if we have started the module
    module_start = False
    with open(file_name, "r") as orig_file_obj:
        line_holder = []
        for line in orig_file_obj:
            if "module" in line: 
                module_start = True
                if line.strip() == 'endmodule': 
                    statement_list.append(line.strip())
                    module_start = False
                else:
                    parsed_modules.append(line.split()[1][:line.split()[1].find('(')])
                    print("parsed_modules ", parsed_modules)
            if module_start:
                # if line.strip().startswith("ECL_"): 
                    # tot_num_gates += 1 # counting number of gates on initial parse
                    # print("increment total_gates", tot_num_gates)
                # if line.strip().startswith("ECL_OR"): num_or_gates += 1 # counting number of ECL_OR gates on inital parse
                if line.strip().endswith(";"):
                    line_holder.append(line.strip())
                    statement_list.append(line_holder.copy())
                    line_holder.clear()
                else:
                    line_holder.append(line.strip())
                line.strip()    
    # total_gates = tot_num_gates
    # total_or_gates = num_or_gates
    return statement_list

def join_statements(statement_list: list) -> list:
    new_list = [' '.join(element) if element != "endmodule" else element for element in statement_list]
    #for element in statement_list:
    return new_list

def parse_module_params(statement: str) -> str:
    args_w_compliments = []
    arg_str = statement[statement.find("(")+1:statement.find(")")]
    statement_args = arg_str.split(", ")
    #print(statement_args)
    arg_compliments = ["{}_bar".format(arg) for arg in statement_args]
    #args_w_compliments +=  statement_args.copy()
    # final_arg_list consists of all the original io + compliments + SET and RESET pins
    # final_arg_list = statement_args + arg_compliments + ["SET", "RESET"]
    final_arg_list = statement_args + arg_compliments
    #print(final_arg_list)
    return statement.replace(arg_str, ", ".join(final_arg_list)) if statement != 'endmodule' else statement

def parse_io_and_wires(statement: str) -> str:
    start_list = []
    compliment_list = []
    start_slice = 1
    statement = statement.rstrip(";").replace(',', '')
    statement_list = statement.split()
    if "[" in statement_list[1]:
        start_list = statement_list[:2]
        start_slice = 2
        if '\\' in statement_list[1]:
            start_list = statement_list[:1]
            start_slice = 1
    else:
        start_list = statement_list[:1]

    compliment_list = ["{}_bar".format(port) if '\\' not in port else "{}_bar ".format(port) for port in statement_list[start_slice:]]
    
    return "{} {};".format(' '.join(start_list) , ', '.join(compliment_list))

def parse_gates(statement: str, gate_num: int, or_gate_num: int, want_original: bool = False) -> str:
    gate_type = statement.split()[0]
    #len(statement.split()) will never equal 2
    #gate_name = statement.split()[1][:statement.split()[1].find("(")] if len(statement.split()) == 2 else statement.split()[1] + " "
    gate_name = statement.split()[1][:statement.split()[1].find("(")] if (statement.split()[1].find("(") != -1) else (statement.split()[1] + " ")
    param_additions = []
    final_params = []
    
    vref_num = (int) (or_gate_num / 100)
    cur_num = (int) (gate_num / (100))
    orig_params = statement[statement.find("(")+1:statement.rfind(")")].split(',')
    # orig_params = statement[statement.find("(")+1:statement.rfind(")")].split('),')

    edited_statement = ""

    if(want_original): return "{} {}({});".format(gate_type, gate_name, ', '.join(orig_params))
    
    if gate_type in parsed_modules: #This handles submodule instantiations
        #pass # we are writing new module declarations to add complemented ports 
        orig_params = statement[statement.find("(")+1:statement.rfind(")")].split('),')
        find_submodule_compliments(orig_params, param_additions)
        print('parsing submodule inst\n')
    else:
        match gate_type:
            case "ECL_OR":
                find_complements = ['.OR']
                print("OR GATE")
                
                print(orig_params)
    #            for argument in orig_params:
    #                port = argument[:argument.find("(")].strip()
    #                net = argument[argument.find("(")+1:argument.find(")")]
    #                net_bit_width = ""
    #                if "[" in net and net.endswith("]"): #checking if net has a specfied bitwidth
    #                    net_bit_width = net[net.find("["):net.rfind("]")+1] #parsing the associated bitwidth for the current net
    #                    net = net[:net.find("[")]
    #                if port == ".OR":
    #                    not_port = ".{}".format(port_complement(port[1:]))
    #                    net_bar = "{}bar{}".format(net, net_bit_width)
    #                    new_param = "{} ({})".format(not_port, net_bar)
    #                    print(new_param)
    #                    param_additions.append(new_param)
    #                print(port,net)

                find_all_complements(orig_params, find_complements, param_additions)           
                cur_param = ".CUR (CUR_{})".format(cur_num)
                ref_param = ".REF (REF_{})".format(vref_num)
                param_additions.append(cur_param)
                param_additions.append(ref_param)


            case "ECL_AND":
                find_complements = [".A", ".B", ".AND"]
                print("AND GATE")
                #orig_params = statement[statement.find("(")+1:statement.rfind(")")].split(',')
                print(orig_params)
    #            for argument in orig_params:
    #                port = argument[:argument.find("(")].strip()
    #                net = argument[argument.find("(")+1:argument.find(")")]
    #                net_bit_width = ""
    #                if "[" in net and net.endswith("]"): #checking if net has a specfied bitwidth
    #                    net_bit_width = net[net.find("["):net.rfind("]")+1] #parsing the associated bitwidth for the current net
    #                    net = net[:net.find("[")]
    #                if port in find_complements:
    #                    not_port = ".{}".format(port_complement(port[1:]))
    #                    net_bar = "{}bar{}".format(net, net_bit_width)
    #                    new_param = "{} ({})".format(not_port, net_bar)
    #                    param_additions.append(new_param)
                find_all_complements(orig_params, find_complements, param_additions)
                cur_param = ".CUR (CUR_{})".format(cur_num)
                param_additions.append(cur_param)
                                    
            case "ECL_XOR":
                print("XOR GATE")
                find_complements = [".A", ".B", ".XOR"]
                print(orig_params)
                find_all_complements(orig_params, find_complements, param_additions)
                cur_param = ".CUR (CUR_{})".format(cur_num)
                param_additions.append(cur_param)
            case "ECL_INV":
                print("INVERTER")
                find_complements = [".IN", ".INV"]
                find_all_complements(orig_params, find_complements, param_additions)
                cur_param = ".CUR (CUR_{})".format(cur_num)
                param_additions.append(cur_param)
            case "ECL_DFFSR":
                print("D FLIPFLOP")
                find_complements = [".CLK"]
                Q_net = orig_params[len(orig_params) - 2]
                Q_bar_net = orig_params[len(orig_params) - 1]
                D_net = orig_params[len(orig_params) - 4]
                # D_bar_net = orig_params[len(orig_params) - 3]
                UnCon_Q = "UNCONNECTED" in Q_net
                UnCon_QBAR = "UNCONNECTED" in Q_bar_net 
                D_gnd = "1'b" in D_net # Checking if the D input is grounded, we don't find complemented net for DBAR

                if not D_gnd: find_complements.append(".D")

                if UnCon_QBAR:
                    # find_complements = [".CLK", ".D", ".Q"]
                    find_complements.append(".Q")
                elif UnCon_Q:
                    # find_complements = [".CLK", ".D", ".QBAR"]
                    find_complements.append(".QBAR")
                # else:
                #     find_complements = [".CLK", ".D"]

                # find_complements = [".CLK", ".D", ".Q"]
                find_all_complements(orig_params, find_complements, param_additions)
                cur_param = ".CUR (CUR_{})".format(cur_num)
                param_additions.append(cur_param)            
            case "ECL_MUX21": #idk exact name for mux yet
                find_complements = [".A", ".B", ".OUT", ".S"]
                find_all_complements(orig_params, find_complements, param_additions)
                cur_param = ".CUR (CUR_{})".format(cur_num)
                param_additions.append(cur_param)
                print("MUX")
            case default:
                print("NOT A GATE")
    

    print(gate_num, or_gate_num)
    #final_params = orig_params + param_additions
    final_params = param_additions

    edited_statement = "{} {}({});".format(gate_type, gate_name, ', '.join(final_params))
    print(edited_statement)
    return edited_statement
    

def port_complement(port: str) -> str:
    LUT = {
        "OR": "NOR",
        "AND": "NAND",
        "XOR": "XNOR",
        "A": "NOTA",
        "B": "NOTB",
        "IN": "REF",
        "INV": "BUF", #I think BUF is the iniverse of output inv
        "CLK": "CLKBAR",
        "D": "DBAR",
        "Q": "QBAR",
        "QBAR": "Q",
        "S": "SBAR",
        "OUT": "OUTBAR"
    }
    return LUT[port]

def find_all_complements(orig_params: list, find_complements: list, param_additions: list) -> list:
    special_ports = [".RESET", ".SET"]
    port_dict = {}

    for argument in orig_params:
        port = argument[:argument.find("(")].strip()
        net = argument[argument.find("(")+1:argument.find(")")]

        if port not in port_dict.keys():
            port_dict[port] = net

        net_bit_width = ""

        if "[" in net and net.endswith("]"): #checking if net has a specfied bitwidth
            net_bit_width = net[net.find("["):net.rfind("]")+1] #parsing the associated bitwidth for the current net
            net = net[:net.find("[")]

        if port in special_ports and net == '1\'b0':
            port_dict[port] = port[1:]
        
        if port in find_complements:
            not_port = ".{}".format(port_complement(port[1:]))
            # net_bar = "{}bar{}".format(net, net_bit_width)
            net_bar = "{}bar{}".format(net.strip(), net_bit_width) if "\\" not in net else "{}bar{} ".format(net.strip(), net_bit_width)
            new_param = "{} ({})".format(not_port, net_bar)
            port_dict[not_port] = net_bar
            #param_additions.append(new_param)    

    for port_key in port_dict.keys():
        new_param = "{} ({})".format(port_key, port_dict[port_key])
        param_additions.append(new_param)
    
    print("FINAL: ", param_additions)

def find_submodule_compliments(orig_params: list, param_additions: list) -> list:
    sr_params = [".SET (SET)", ".RESET (RESET)"]
    port_dict = {}
    net_list_compliments = []

    for argument in orig_params:
        port = argument[:argument.find("(")].strip()
        not_port = ".{}bar".format(port[1:])
        net = argument[argument.find("(")+1:] if argument.rfind(")") == -1 else argument[argument.find("(")+1:argument.rfind(")")]
        print("subnet: ", net)
        if '{' in net:
            port_dict[port] = net.strip("{}").split(', ')
            # print('sub_nets: ', port_dict[port])
        else:
            port_dict[port] = [net]

        
        port_dict[not_port] = []

        for sub_net in port_dict[port]:
            net_bit_width = ""

            if "[" in sub_net and sub_net.endswith("]"): #checking if net has a specfied bitwidth
                net_bit_width = sub_net[sub_net.find("["):sub_net.rfind("]")+1] #parsing the associated bitwidth for the current net
                sub_net = sub_net[:sub_net.find("[")]

                # not_port = ".{}bar".format(port[1:])
                # net_bar = "{}bar{}".format(net, net_bit_width)
            if "\'b" in sub_net:
                sub_net_bar = sub_net
            else:
                sub_net_bar = "{}bar{}".format(sub_net.strip(), net_bit_width) if "\\" not in sub_net else "{}bar{} ".format(sub_net.strip(), net_bit_width)
            # new_param = "{} ({})".format(not_port, sub_net_bar)
            port_dict[not_port].append(sub_net_bar)
        
        # net_str = "{{}}".format(', '.join(port_dict[not_port])) if len(port_dict[not_port]) != 1 else port_dict[not_port][0]
        intermediate_st = ', '.join(port_dict[not_port]) #if len(port_dict[not_port]) != 1 else port_dict[not_port][0]
        net_str = f"{{{intermediate_st}}}" if len(port_dict[not_port]) != 1 else port_dict[not_port][0]
        new_param = "{} ({})".format(not_port, net_str)
        orig_param = "{} ({})".format(port, net)
        param_additions.append(orig_param)
        param_additions.append(new_param)

    # param_additions = param_additions + sr_params #adding SET and RESET ports to submodule
    param_additions.append(sr_params[0])
    param_additions.append(sr_params[1])
    
    print('submodule parmas: ', param_additions)




def write_reference_circuits(file_obj, gate_count: int, or_count: int, mode: str):
    vref_num = (int) (or_count/100) 
    ref_num = (int) (gate_count/100) 
    match mode:
        case "VREF":
            print("VREF")
            file_obj.write("\n\tECL_Voltage_Reference voltage_ref_{}(.VCC(VCC), .CUR(CUR_{}), .REF(REF_{}), .GND(GND));\n".format(vref_num, ref_num, vref_num))
            pass
        case "CUR":
            print("CUR")
            file_obj.write("\n\tECL_Reference current_ref_{}(.VCC(VCC), .current_mirror(CUR_{}), .GND(GND));\n".format(ref_num, ref_num))
            pass
        case default:
            # do nothing
            print("Did not create a reference circuit for gate number: " + gate_count)
            pass
    file_obj.write("\n")

def write_module(file_name, module_lines: list, gate_count: int, or_count: int, module_num: int):
    new_lines_list = []
    group_io = []
    group_wire = []
    group_assign = []
    group_gates = []
    simplified_gates = []
    ref_wires = ["VCC", "GND"]
    finished_voltage_ref = []

    gate_counter = 1
    or_counter = 0

    if module_num == len(module_lines):
        print("Loop: {}, Gate_count: {}, Or_count: {}".format(module_num, gate_count, or_count))
        return

    pnr_file = file_name
    orig_lines_list = module_lines[module_num]

    for count, element in enumerate(orig_lines_list):
        #print(count, element)
        if "module" in element: 
            new_line = parse_module_params(element)
            #print(new_line)
            new_lines_list.append(new_line)
        elif "input" in element or "output" in element:
            #print("input", element)
            group_io.append(element)
            new_line = parse_io_and_wires(element)
            group_io.append(new_line)
            #print(parse_io(element))
        elif element.startswith("wire"):
            group_wire.append(element)
            group_wire.append(parse_io_and_wires(element))
        elif element.startswith("ECL_") or element.split()[0] in parsed_modules:
            gate_counter += 1                
            # gate_type is the first index in element list once we split off of whitespace
            gate_type = element.split()[0]
            if gate_type == "ECL_OR": or_counter += 1
            if or_counter%100 == 0 and or_counter != 0: gate_counter += 1
            group_gates.append(parse_gates(element, gate_counter + gate_count, or_counter + or_count))
            # uncomment below line if want to write out original gates for comparison
            simplified_gates.append(parse_gates(element, gate_counter, or_counter, True))
        elif element.startswith("assign"):
            group_assign.append(element)

    group_io.append("input SET, RESET;")

    for num in range((int)(gate_counter/100)+1):
        ref_wires.append("CUR_{}".format(num))

    for num in range((int)(or_counter/100)+1):
        ref_wires.append("REF_{}".format(num))

        
    pprint(group_io)
    pprint(group_wire)
    pprint(group_gates)
    print(total_gates, total_or_gates)
    print(new_lines_list)

    with open(pnr_file, 'a') as pnr:
        current_gate_num = 0
        or_gate_num = 0

        pnr.write(new_lines_list[0] + '\n')

        for line in group_io:
            pnr.write('\t' + line + '\n')
        for line in group_wire:
            pnr.write('\t' + line + '\n')
            
        pnr.write("\twire {};\n".format(", ".join(ref_wires)))

        for line in group_assign:
            pnr.write('\t' + line + '\n')  

        write_reference_circuits(pnr, gate_count, or_count, "CUR")
        write_reference_circuits(pnr, gate_count, or_count, "VREF")
        current_gate_num += 1

        for line in group_gates:
            current_gate_num += 1
            if line.startswith("ECL_OR"): or_gate_num += 1
            if current_gate_num%100 == 0: write_reference_circuits(pnr, gate_count + current_gate_num, or_count + or_gate_num, "CUR")
            if or_gate_num%100 == 0 and or_gate_num != 0:
                current_gate_num += 1 
                if or_gate_num not in finished_voltage_ref: write_reference_circuits(pnr, gate_count + current_gate_num, or_count + or_gate_num, "VREF") 
                finished_voltage_ref.append(or_gate_num)

            print(line + '\n')
            pnr.write('\t' + line + '\n')
        pnr.write(new_lines_list[1] + '\n\n')
        # pnr.write("endmodule")
    write_module(file_name, module_lines, (gate_count + current_gate_num + (100 - current_gate_num%100)),(or_count + or_gate_num + (100 - or_gate_num%100)), module_num+1)

def write_module_2(file_name, lines: list):
    global num_tie
    global total_gates
    global total_or_gates
    new_lines_list = []
    group_io = []
    group_wire = []
    group_assign = []
    assign_list = []
    assign_lines = []
    cell_list = []

    or_cnt = 0
    ti_lo_cnt = 0
    ti_hi_cnt = 0
    # str_list = join_statements(lines)
    # for i in str_list: print(i)
    # exit()
    # str_list = [" ".join()]

    for element in join_statements(lines):
        # print(element)
        if element.startswith("module"):
            module_dec = parse_module_params(element)
            new_lines_list.append(module_dec)            
        elif element.startswith("input") or element.startswith("output"):
            group_io.append(element)
            new_line = parse_io_and_wires(element)
            group_io.append(new_line)            
        elif element.startswith("assign"):
            #group_assign.append((element))
            group_assign.append(parse_assign(element))
            pass
        elif element.startswith("wire"):
            group_wire.append(element)
            group_wire.append(parse_io_and_wires(element))
        elif element.split()[0] in (cell_map.keys()): # handles cells 
            c1 = cell()
            # print(line)
            c1.fill_cell(element)
            cell_list.append(c1)            
            
        else: #we found another cell instance?
            pass
    
    #assign_list = get_assign_compliments(group_assign) # need to run get_assign_compliments before creating the special cells
    assign_list = replace_assigns(group_assign)
    for cell_inst in assign_list:
        print(cell_inst)
        c1 = cell()
        c1.fill_cell(cell_inst)
        cell_list.append(c1)

    special_cells = create_special_cells()

    group_wire.append("wire {};".format(", ".join(special_cells[2])))
    
    # for pair in assign_list:
    #     if pair[1].endswith("'b0"):
    #         # pair[1] = "Lo_{}".format(int(ti_lo_cnt/config["tie_cell_fanout"]))
    #         # pair = (pair[0], "Lo_{}".format(int(ti_lo_cnt/config["tie_cell_fanout"])))
    #         # assign_list.append("assign {} = {}".format(pair[0], pair[1]))
    #         # assign_list.append("assign {} = {}".format(invert_net(pair[0]), invert_net(pair[1])))            
    #         assign_lines.append("assign {} = Lo_{};".format(pair[0], int(ti_lo_cnt/config["tie_cell_fanout"])))
    #         ti_lo_cnt += 1
    #     elif pair[1].endswith("'b1"):
    #         # pair[1] = "Hi_{}".format(int(ti_hi_cnt/config["tie_cell_fanout"]))
    #         # pair = (pair[0], "Hi_{}".format(int(ti_hi_cnt/config["tie_cell_fanout"])))
    #         assign_lines.append("assign {} = Hi_{};".format(pair[0], int(ti_hi_cnt/config["tie_cell_fanout"])))
    #         ti_hi_cnt += 1
    #     else:
    #         assign_lines.append("assign {} = {};".format(pair[0], pair[1]))

    for i, inst in enumerate(cell_list):
        inst.cell_ports["CUR"] = "CUR_{}".format(int((i+special_cells[1])/config["reference_cell_fanout"]))
        if inst.cell_type == "ECL_OR": 
            inst.cell_ports["REF"] = "REF_{}".format(int(or_cnt/config["reference_cell_fanout"]))
            or_cnt += 1
        # print(inst)
        if inst.tied_ports["Ti_Hi"]:
            for port in inst.tied_ports["Ti_Hi"]:
                inst.cell_ports[port] = "Hi_{}".format(int(ti_hi_cnt/config["tie_cell_fanout"]))
                ti_hi_cnt += 1
        if inst.tied_ports["Ti_Lo"]:
            for port in inst.tied_ports["Ti_Lo"]:
                inst.cell_ports[port] = "Lo_{}".format(int(ti_lo_cnt/config["tie_cell_fanout"]))    
                ti_lo_cnt += 1

        # print(ti_lo_cnt, ti_hi_cnt, inst)
    new_lines_list = group_io + ["\n"] + group_wire + ["\n"] + special_cells[0] + ["\n"] + assign_lines + ["\n"] + cell_list
    new_lines_list = [("\t" + str(line)) for line in new_lines_list]
    new_line_str = "\n".join(new_lines_list)
    # new_lines_list = new_lines_list + group_io + group_wire + special_cells[0] + assign_lines + cell_list

    with open(file_name, 'w') as file:
        file.write(module_dec + "\n")
        file.write(new_line_str + "\n")
        file.write("endmodule")

    total_gates = 0
    total_or_gates = 0
    num_tie = 0
    # for i in new_lines_list: print(i)ls
    

def write_sdc(file_name: str, output_path: str):
    orig_sdc_lines = []
    output_file = "{}/script_{}_pnr{}".format(output_path, file_name[file_name.rfind('/')+1:-4], file_name[-4:])
    with open(file_name, "r") as file:
        orig_sdc_lines = file.readlines()
    print(orig_sdc_lines)

    net_pattern = re.compile(r'(\[get_ports\s*|get_clocks\s*|\"-name\s*\"|\-name\s*)({?[\w\[\]]+}?)')

    with open(output_file, "w") as output_file:
        for line in orig_sdc_lines:
            # Write the original line first
            output_file.write(line)
            
            # Check if the line contains a net, port, or clock command (e.g., get_ports, get_clocks, -name)
            if "get_ports" in line or "get_clocks" in line or "-name" in line:
                # Split the line into parts
                parts = line.split()
                modified_parts = parts[:]  # Make a copy of the original parts for modification

                for i, part in enumerate(parts):
                    if "get_ports" in part or "get_clocks" in part:
                        # Modify the net/port/clock name after get_ports or get_clocks
                        net_name_index = i + 1
                        net_name = parts[net_name_index]

                        # Check if the net has a bracket (e.g., i_ADDR[1])
                        if "[" in net_name:
                            # Insert _bar before the bracket
                            modified_parts[net_name_index] = re.sub(r'(.*?)(\[.*\])', r'\1_bar\2', net_name)
                        else:
                            # Append _bar if no bracket is present
                            modified_parts[net_name_index] = net_name[:-1] + "_bar" + ']'
                    
                    elif "-name" in part:
                        # Modify the net/port/clock name after -name
                        net_name_index = i + 1
                        net_name = parts[net_name_index].strip('"')  # Remove quotes if present

                        # Check if the net has a bracket (e.g., i_ADDR[1])
                        if "[" in net_name:
                            # Insert _bar before the bracket
                            modified_parts[net_name_index] = '"' + re.sub(r'(.*?)(\[.*\])', r'\1_bar\2', net_name) + '"'
                        else:
                            # Append _bar if no bracket is present
                            modified_parts[net_name_index] = '"' + net_name + "_bar" + '"'

                # Reconstruct the modified line
                modified_line = " ".join(modified_parts) + "\n"
                
                # Write the modified line after the original one
                output_file.write(modified_line)
    pass
    

            

def main():
    global total_gates
    global total_or_gates
    global open_file
    global parsed_modules
    global config
    global cell_map
    # These handle adding Tie-Cells to the netlist
    # global num_b0 #counts number of nets/ports tied low
    # global num_b1 # counts number of nets/ports tied high
    global num_tie # counts number of tie-hi/lo pairs
    args = sys.argv[1:]
    #module_start = False
    statement_finish = False
    orig_lines_list = []
    group_io = []
    group_wire = []
    new_lines_list = []
    group_gates = []
    total_gates = 0 
    total_or_gates = 0
    pnr_file = ""
    ref_wires = ["VCC", "GND"]
    finished_voltage_ref = [] #holds the or_gate_num when a voltage ref is initialized
    tracked_or_gates = []
    simplified_gates = []
    parsed_modules = []
    config = {}


    module_lines_list = []
    end_module_indexes = []
    previous_index = 0
    cell_list = []

    gate_counter = 0
    or_counter = 0
    # total_gates = 0
    # total_or_gates = 0
    num_tie = 0


    if len(args) < 1:
        print("usage: python edit_net.py <netlist_file.v> [config.json]")
        exit(1)

    open_file = args[0]

    # if not os.path.isfile(open_file):
    #     print("Did not input a valid file")
    #     exit(1)
    # else:
    #     print(open_file[-2:])
    #     if open_file[-2:] != ".v":
    #         print("Script expects a Verilog file (*.v)")
    #         exit(1)

    if len(args) == 2: #checking if we have a config file input
        json_file = args[1]

        if not os.path.isfile(json_file):
            print("Did not input a valid file")
            exit(1)
        else:
            print(json_file[-5:])
            if json_file[-5:] != ".json":
                print("Script expects a config file")
                exit(1)
            
            with open(json_file) as json_config:
                config = json.load(json_config)
    else:
        config = get_default_config()

    # creating a map to handle custom cell names in the netlist which correspond to our normal ECL cells
    cell_map = {custom_cell : default_cell for default_cell, custom_cell in config["custom_cell_map"].items()} 

    pwd_dir = os.getcwd()
    netlist_path = os.path.join(pwd_dir,"outputs/netlist")
    sdc_path = os.path.join(pwd_dir,"outputs/sdc")
    os.makedirs(netlist_path, exist_ok= True)
    os.makedirs(sdc_path, exist_ok= True)

    print(open_file)
    for file_name in glob.iglob(os.path.join(open_file, '**/*.v'), recursive=True):
        if os.path.isfile(file_name):
            print(file_name)
            pnr_file = "{}/script_{}_pnr{}".format(netlist_path, file_name[file_name.rfind('/')+1:-2], file_name[-2:])
            print(pnr_file)
            orig_lines_list = group_statements(file_name, orig_lines_list, total_gates, total_or_gates)

            write_module_2(pnr_file ,orig_lines_list)
            orig_lines_list = [] # clears previous files original lines

    for file_name in glob.iglob(os.path.join(open_file, '**/*.sdc'), recursive=True):
        if os.path.isfile(file_name):
            write_sdc(file_name, sdc_path)

            print(file_name)    

    exit()
    

    exit()
    
    for line in join_statements(orig_lines_list):
        if line.startswith("ECL_"):
            c1 = cell()
            # print(line)
            c1.fill_cell(line)
            cell_list.append(c1)
            # print(c1)
    # total_gates += num_tie;
    
    special_cells = create_special_cells()

    for c in special_cells[0]:
        print(c)

    or_cnt = 0
    ti_lo_cnt = 0
    ti_hi_cnt = 0
    for i, inst in enumerate(cell_list):
        inst.cell_ports["CUR"] = "CUR_{}".format(int((i+special_cells[1])/config["reference_cell_fanout"]))
        if inst.cell_type == "ECL_OR": 
            inst.cell_ports["REF"] = "REF_{}".format(int((or_cnt+special_cells[1])/config["reference_cell_fanout"]))
            or_cnt += 1
        # print(inst)
        if inst.tied_ports["Ti_Hi"]:
            for port in inst.tied_ports["Ti_Hi"]:
                inst.cell_ports[port] = "Hi_{}".format(int(ti_hi_cnt/config["tie_cell_fanout"]))
                ti_hi_cnt += 1
        if inst.tied_ports["Ti_Lo"]:
            for port in inst.tied_ports["Ti_Lo"]:
                inst.cell_ports[port] = "Lo_{}".format(int(ti_lo_cnt/config["tie_cell_fanout"]))    
                ti_lo_cnt += 1

        print(ti_lo_cnt, ti_hi_cnt, inst)

    print("Total: %d\nOr: %d\nTied: %d" % (total_gates, total_or_gates, num_tie))
    
    exit(1)
    

    print("BALLS")
    #pprint(join_statements(orig_lines_list))
    orig_lines_list = join_statements(orig_lines_list)
    pprint(orig_lines_list)
    end_module_indexes = [index for index, val in enumerate(orig_lines_list) if val == 'endmodule']
    print(len(end_module_indexes))

    for index in end_module_indexes:
        module_lines_list.append(orig_lines_list[previous_index:index+1])
        print(orig_lines_list[previous_index:index+1])
        print(len(module_lines_list))
        previous_index = index+1
    
    with open(pnr_file, 'w') as pnr:
        pass

    write_module(pnr_file, module_lines_list, 0, 0, 0)    

        




    

if __name__ == '__main__':
    main()

