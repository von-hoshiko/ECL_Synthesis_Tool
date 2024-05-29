import sys
import os
from pprint import pprint
import re

def group_statements(statement_list: list, tot_num_gates: int, num_or_gates: int) -> list:
    global total_gates
    global total_or_gates
    # checks if we have started the module
    module_start = False
    with open(open_file, "r") as orig_file_obj:
        #with open("script_" + open_file[:-2] + "_pnr" + open_file[-2:], "a") as new_file:
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
                if line.strip().startswith("ECL_"): 
                    tot_num_gates += 1 # counting number of gates on initial parse
                    print("increment total_gates", tot_num_gates)
                if line.strip().startswith("ECL_OR"): num_or_gates += 1 # counting number of ECL_OR gates on inital parse
                if line.strip().endswith(";"):
                    line_holder.append(line.strip())
                    statement_list.append(line_holder.copy())
                    line_holder.clear()
                else:
                    line_holder.append(line.strip())
                line.strip()    
    total_gates = tot_num_gates
    total_or_gates = num_or_gates
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
    arg_compliments = ["{}bar".format(arg) for arg in statement_args]
    #args_w_compliments +=  statement_args.copy()
    # final_arg_list consists of all the original io + compliments + SET and RESET pins
    final_arg_list = statement_args + arg_compliments + ["SET", "RESET"]
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

    compliment_list = ["{}bar".format(port) if '\\' not in port else "{}bar ".format(port) for port in statement_list[start_slice:]]
    
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





def main():
    global total_gates
    global total_or_gates
    global open_file
    global parsed_modules
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


    module_lines_list = []
    end_module_indexes = []
    previous_index = 0

    gate_counter = 1
    or_counter = 0

    if len(args) != 1:
        print("usage: python edit_net.py netlist_file.v")
        exit(1)

    open_file = args[0]

    if not os.path.isfile(open_file):
        print("Did not input a valid file")
        exit(1)
    else:
        print(open_file[-2:])
        if open_file[-2:] != ".v":
            print("Script expects a Verilog file (*.v)")
            exit(1)

    pnr_file = "script_{}_pnr{}".format(open_file[open_file.rfind('/')+1:-2], open_file[-2:])

#    with open(open_file, "r") as orig_file_obj:
        #with open("script_" + open_file[:-2] + "_pnr" + open_file[-2:], "a") as new_file:
#        line_holder = []
#        for line in orig_file_obj:
#            if "module" in line: module_start = True
#            if module_start:
#                if line.strip().endswith(";"):
#                    line_holder.append(line.strip())
#                    orig_lines_list.append(line_holder.copy())
                    #print(line_holder)
                    #print("BALLLLS")
#                    line_holder.clear()
                    #statement_finish = True
#                else:
#                    line_holder.append(line.strip())
#                line.strip() 
            #print(line.rstrip())
            #orig_lines_list.append(line.rstrip()) if line.strip().endswith(";") and module_start else "{} {}".format(orig_lines_list[-1], line.lstrip())
        #pprint(group_statements(orig_lines_list))
    orig_lines_list = group_statements(orig_lines_list, total_gates, total_or_gates)
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
    # for count, element in enumerate(orig_lines_list):
    #     #print(count, element)
    #     if "module" in element: 
    #         new_line = parse_module_params(element)
    #         #print(new_line)
    #         new_lines_list.append(new_line)
    #     elif "input" in element or "output" in element:
    #         #print("input", element)
    #         group_io.append(element)
    #         new_line = parse_io_and_wires(element)
    #         group_io.append(new_line)
    #         #print(parse_io(element))
    #     elif element.startswith("wire"):
    #         group_wire.append(element)
    #         group_wire.append(parse_io_and_wires(element))
    #     elif element.startswith("ECL_"):
    #         gate_counter += 1                
    #         # gate_type is the first index in element list once we split off of whitespace
    #         gate_type = element.split()[0]
    #         if gate_type == "ECL_OR": or_counter += 1
    #         if or_counter%100 == 0 and or_counter != 0: gate_counter += 1
    #         group_gates.append(parse_gates(element, gate_counter, or_counter))
    #         # uncomment below line if want to write out original gates for comparison
    #         simplified_gates.append(parse_gates(element, gate_counter, or_counter, True))

    # for num in range((int)(gate_counter/100)+1):
    #     ref_wires.append("CUR_{}".format(num))

    # for num in range((int)(or_counter/100)+1):
    #     ref_wires.append("REF_{}".format(num))

        
    # pprint(group_io)
    # pprint(group_wire)
    # pprint(group_gates)
    # print(total_gates, total_or_gates)

    # with open(pnr_file, 'w') as pnr:
    #     current_gate_num = 0
    #     or_gate_num = 0

    #     pnr.write(new_lines_list[0] + '\n')

    #     for line in group_io:
    #         pnr.write(line + '\n')
    #     for line in group_wire:
    #         pnr.write(line + '\n')

    #     pnr.write("wire {};\n".format(", ".join(ref_wires)))
    #     write_reference_circuits(pnr, 0, 0, "CUR")
    #     write_reference_circuits(pnr, 0, 0, "VREF")
    #     current_gate_num += 1

    #     for line in group_gates:
    #         current_gate_num += 1
    #         if line.startswith("ECL_OR"): or_gate_num += 1
    #         if current_gate_num%100 == 0: write_reference_circuits(pnr, current_gate_num, or_gate_num, "CUR")
    #         if or_gate_num%100 == 0 and or_gate_num != 0:
    #             current_gate_num += 1 
    #             if or_gate_num not in finished_voltage_ref: write_reference_circuits(pnr, current_gate_num, or_gate_num, "VREF") 
    #             finished_voltage_ref.append(or_gate_num)

    #         pnr.write(line + '\n')
    #     pnr.write("endmodule")

    # with open("tmp_simplified_orig.v", 'w') as file:
    #     current_gate_num = 0
    #     or_gate_num = 0
    #     for line in group_io:
    #         file.write(line + '\n')
    #     for line in group_wire:
    #         file.write(line + '\n')

    #     file.write("wire {};\n".format(", ".join(ref_wires)))
    #     write_reference_circuits(file, 0, 0, "CUR")
    #     write_reference_circuits(file, 0, 0, "VREF")
    #     current_gate_num += 1

    #     for line in simplified_gates:
    #         current_gate_num += 1
    #         if line.startswith("ECL_OR"): or_gate_num += 1
    #         if current_gate_num%100 == 0: write_reference_circuits(file, current_gate_num, or_gate_num, "CUR")
    #         if or_gate_num%100 == 0 and or_gate_num != 0:
    #             current_gate_num += 1 
    #             if or_gate_num not in finished_voltage_ref: write_reference_circuits(file, current_gate_num, or_gate_num, "VREF") 
    #             finished_voltage_ref.append(or_gate_num)

    #         file.write(line + '\n')
    #     file.write("endmodule")        
    

        




    

if __name__ == '__main__':
    main()

