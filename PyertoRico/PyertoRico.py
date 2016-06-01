#!/usr/bin/env python

# Import dependencies
import webbrowser
import requests
import re

class Game:
    
    # Initialize a Game object from the html "logs" of a BGA game
    def __init__(self, tableID):
        self.tableID = tableID
        self.roles = Game.get(tableID)
        
    # Parse the game into a list of "role blocks"
    def get(tableID):
        
        # Open webpage with browser to instance a game "log"
        # User must log into Board Game Arena on browser
        html = "http://en.boardgamearena.com/gamereview" + "?table=" + tableID
        webbrowser.open(html, autoraise = False)
        
        # Get the html "log" for a single game
        target_url = "http://en.boardgamearena.com/archive/archive/logs.html"
        params = {"table": str(tableID), "translated": "true"}
        req = requests.get(target_url, params = params)
        log = req.text
        
        # Index all role changes
        index_role = []
        loc = 0
        while loc > -1:
            index_role.append(loc)
            loc = log.find("[\"rol_type_tr\"],\"player_name\"", loc + 1)
        
        # Ignore the first "role block" as a superfluous header
        # Organize remaining data into list of Role objects
        roles = []
        for i in range(1, len(index_role)):
            start = index_role[i]
            if(i == len(index_role) - 1):
                end = len(log) - 1     
            else:
                end = index_role[i + 1] - 1
            role_new = Role(log[start:end])
            roles.append(role_new)
        
        # Return a list of Role objects
        return(roles)
        
class Role:
    
    # Initialize a Role object by parsing a "role block"
    def __init__(self, roleblock):
      self.roleblock = roleblock
      role_summary = Role.parse(roleblock)
      self.player_name = role_summary[0]["{player_name}"]
      self.rol_type = role_summary[1]["{rol_type}"]
      self.role = role_summary[2::]
    
    # Parse each "role block" into a list of move logs
    def parse(roleblock):
        
        # Find the first 'val' that corresponds to the supplied "{key}"
        def key2val(key, rolechunk):
            key_search = "\"" + key[1:-1] + "\"" + ":"
            key_loc = rolechunk.find(key_search)
            if rolechunk[key_loc + len(key_search)] == "\"":
                start = key_loc + len(key_search) + 1
                end = rolechunk.find("\"", start)
            else:
                start = key_loc + len(key_search)
                end1 = rolechunk.find(",", start)
                end2 = rolechunk.find("}", start)
                end = min(end1, end2)
            return({ key:rolechunk[start:end] })
        
        # Retrieve important role information
        keys = ("{player_name}", "{rol_type}")
        role_summary = [key2val(key, roleblock) for key in keys] 
        
        # Retrieve the role logs
        logs = []
        log_loc = 0
        while(log_loc > -1):
            
            # Locate each role log
            log_loc = roleblock.find("\"log\":", log_loc + 1)
            if log_loc == -1:
                continue
            log_val = key2val("\"log\":", roleblock[log_loc:])
            log_val = [str(val) for (i, val) in log_val.items()][0]
            if log_val == "${player_name} selected the ${rol_type_tr}":
                continue
            
            # Populate missing "${key}" details in role log
            if len(log_val) > 0:
                args = re.findall("{\w*}", log_val)
                vals = [key2val(arg, roleblock[log_loc:]) for arg in args]
                for d in vals:
                    log_val = [log_val.replace(k,v) for (k,v) in d.items()][0]
                logs.append(log_val)
        
        # Return the role summary and role logs
        role_summary = role_summary + logs
        return(role_summary)
