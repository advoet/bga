#!/usr/bin/env python

import webbrowser
import requests
import re

# Parse the game into a list of "role blocks"
def getRoles(tableID):
    
    # Open webpage with browser to have logs 
    html = "http://en.boardgamearena.com/gamereview" + "?table=" + tableID
    webbrowser.open(html, autoraise = False)
    
    # Get game stats
    target_url = "http://en.boardgamearena.com/archive/archive/logs.html"
    params = {"table": str(tableID), "translated": "true"}
    req = requests.get(target_url, params = params)
    table = req.text
    print(table)
    
    # Index the location of role change
    index_role = []
    loc = 0
    while loc > -1:
        index_role.append(loc)
        new_loc = table.find("[\"rol_type_tr\"],\"player_name\"", loc + 1)
        loc = new_loc
    
    # Organize data into list of "role blocks"
    roleblock = []
    for i in range(0, len(index_role)):
        start = index_role[i]
        if(i == len(index_role) - 1):
            end = len(table) - 1     
        else:
            end = index_role[i + 1] - 1
        roleblock.append(table[start:end])
    
    # Remove first "role block" as a header
    return(roleblock[1::])

# Parse each "role block" into a list of move logs
def parseRole(role):
    
    def key2val(key, rolechunk):
        key_search = "\"" + key[1:-1] + "\"" + ":"
        key_loc = rolechunk.find(key_search)
        if rolechunk[key_loc + len(key_search)] == "\"": # get character value
            start = key_loc + len(key_search) + 1
            end = rolechunk.find("\"", start)
        else: # get integer value
            start = key_loc + len(key_search)
            end1 = rolechunk.find(",", start)
            end2 = rolechunk.find("}", start)
            end = min(end1, end2)
        return({ key:rolechunk[start:end] })
    
    # Retrieve important role information
    keys = ("{player_name}", "{rol_id}", "{rol_type}")
    role_summary = [key2val(key, role) for key in keys] 
    
    # Retrieve the role logs
    logs = []
    log_loc = 0
    while(log_loc > -1):
        
        # Locate each role log
        log_loc = role.find("\"log\":", log_loc + 1)
        if log_loc == -1:
            continue
        log_val = key2val("\"log\":", role[log_loc:])
        log_val = [str(val) for (i, val) in log_val.items()][0]
        if log_val == "${player_name} selected the ${rol_type_tr}":
            continue
        
        # Populate missing ${key} details in role log
        if len(log_val) > 0:
            args = re.findall("{\w*}", log_val)
            vals = [key2val(arg, role[log_loc:]) for arg in args]
            for dic in vals:
                log_val = [log_val.replace(k, v) for (k, v) in dic.items()][0]
            logs.append(log_val)
    
    # Return the role summary and role logs
    role_summary = role_summary + logs
    return(role_summary)
