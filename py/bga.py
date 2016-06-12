#!/usr/bin/env python

# Import dependencies
import copy
import numpy as np
import pandas as pd
import requests
import re
import time

###########################################################
### Define generic classes for Board Game Arena data

class GameSeries:
    
    # Initialize a list of Game objects from a list of table IDs
    def __init__(self, tableIDs, email, password):
        games = []
        for i, tableID in enumerate(tableIDs):
            print("(" + str(i) + "): Fetching tableID " + str(tableID))
            games.append(Game(tableID, email, password))
            time.sleep(30)
        self.games = games
        
    # Filter GameSeries to include only games with n players
    def playerFilter(self, n):
        games_subset = []
        for game in self.games:
            if(len(set(game.turnorder)) is n):
                games_subset.append(game)
        series_new = copy.copy(self)
        series_new.games = games_subset
        return(series_new)
        
class Game:
    
    # Initialize a Game object from the html "logs" of a BGA game
    def __init__(self, tableID, email, password):
        self.tableID = str(tableID)
        self.get(tableID, email, password)
        self.turnorder = [role.player_name for role in self.roles]
        self.roleorder = [role.rol_type for role in self.roles]
        
    # Parse the game into a list of "role blocks"
    def get(self, tableID, email, password):
        
        tableID = str(tableID)
        
        # Define parameters to access to Board Game Arena
        url_login = "http://en.boardgamearena.com/account/account/login.html"
        prm_login = {'email': email, 'password': password, 'rememberme': 'on',
                     'redirect': 'join', 'form_id': 'loginform'}
        url_game = "http://en.boardgamearena.com/gamereview?table=" + tableID
        url_log = "http://en.boardgamearena.com/archive/archive/logs.html"
        prm_log = {"table": tableID, "translated": "true"}
        
        with requests.session() as c:
            
            # Login to Board Game Arena
            r = c.post(url_login, params = prm_login)
            if r.status_code != 200:
                print("Error trying to login!")
            
            # Generate the log files
            r = c.get(url_game)
            if r.status_code != 200:
                print("Error trying to load the gamereview page!")
            
            # Retrieve the log files
            r = c.get(url_log, params = prm_log)
            if r.status_code != 200:
                print("Error trying to load the log file!")
            log = r.text
            
        # Save the requested log file
        self.request = log
            
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
        
        # Save the partitioned roles
        self.roles = roles
        
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
            return({key: rolechunk[start:end]})
        
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
        return(role_summary + logs)
        
###########################################################
### Define specific sub-classes for Puerto Rico game data

class PRSeries(GameSeries):
    
    # Initialize a PRSeries object by importing multiple Game objects
    def __init__(self, tableIDs, email, password):
        games = []
        for tableID in tableIDs:
            games.append(PuertoRico(tableID, email, password))
        self.games = games
        
    # Tally the number of times each winner chose each item in a turn range
    def winnerCumsums(self, start = 0, end = None):
        
        board_winner = []
        board_loser = []
        for game in self.games:
            
            # Calculate the game winner
            winner = game.winner()
            if winner is None:
                continue
            
            # Temporarily set "tabulate_val" as part of a full game
            if end is not None and end < len(game.turnorder):
                tabulate_val_backup = game.tabulate_val
                cumsum_val_backup = game.cumsum_val
                game.tabulate_val = {plyr: game.tabulate_val[plyr][start:end]
                                        for plyr in game.tabulate_val}
                game.cumsum_val = None
                
            # Calculate the cumsum for turn range using "tabulate_val"
            if game.cumsum_val is None:
                tboard = game.cumsum()
            else:
                tboard = game.cumsum_val
                
            if winner is not None:
                board_winner.append(tboard[winner])
                lsrs = [lsr for lsr in set(game.turnorder) if lsr != winner]
                for plyr in lsrs:
                    board_loser.append(tboard[plyr])
                                    
            # Return "tabulate_val" to full game values
            if end is not None and end < len(game.turnorder):
                game.tabulate_val = tabulate_val_backup
                game.cumsum_val = cumsum_val_backup
                
        # Return cumsum data for winning and losing players
        return({"winners": pd.DataFrame(board_winner),
                "losers": pd.DataFrame(board_loser)})
                
    # Calculate frequency that winner held piece "item" in a turn range
    def winnerHeld(self, item, start = 0, end = None):
        
        # Retrieve game cumsums between a range of turns
        boards = self.winnerCumsums(start = start, end = end)
        
        # Average data for the time-stamped boards
        mean_winner = np.mean(boards["winners"][item])
        mean_loser = np.mean(boards["losers"][item])
        return({"winners": mean_winner,
                "losers": mean_loser})
                
    # Calculate frequency that winner held each piece in a turn range
    def winnerHeldAll(self, start = 0, end = None):
        
        # Retrieve game cumsums between a range of turns
        boards = self.winnerCumsums(start = start, end = end)
        
        items = self.games[0].cumsum_val.index
        output = []
        for item in items:
            output.append({"winners": np.mean(boards["winners"][item]),
                           "losers": np.mean(boards["losers"][item])})
            
        all_winner = [entry["winners"] for entry in output]
        all_loser = [entry["losers"] for entry in output]
        final = pd.DataFrame({"winners": all_winner, "losers": all_loser},
                              index = items)
        return(final)
        
    # Calculate frequency that winner held a piece at each turn
    def winnerHeldT(self, item):
        
        game_max = max([len(game.turnorder) for game in self.games])
        output = []
        for t in range(0, game_max):
            output.append(self.winnerHeld(item, start = 0, end = t))
            
        all_winner = [entry["winners"] for entry in output]
        all_loser = [entry["losers"] for entry in output]
        final = pd.DataFrame({"winners": all_winner, "losers": all_loser},
                              index = range(0, game_max))
        return(final)
        
    # Compare the average winning and losing boards at every turn
    def winnerHeldAllT(self):
        
        # Calculate per-turn averages for each item
        items = self.games[0].cumsum_val.index
        output = []
        for item in items:
            print("Calculating per-turn average for item: " + item)
            output.append(self.winnerHeldT(item))
            
        # Compile per-turn averages for each item
        held_winner = []
        held_loser = []
        for i, item in enumerate(items):
            held_winner.append(pd.Series(output[i]["winners"]))
            held_loser.append(pd.Series(output[i]["losers"]))
        df_winner = pd.DataFrame(held_winner, index = items).T
        df_loser = pd.DataFrame(held_loser, index = items).T
        return({"winners": df_winner,
                "losers": df_loser})
                
# Define PuertoRico as a sub-class of Game
# While the Game object includes methods general to (all of?) BGA,
#  this object includes methods specific to Puerto Rico.
class PuertoRico(Game):
    
    tabulate_val = None
    cumsum_val = None
    
    def __init__(self, tableID, email, password):
        Game.__init__(self, tableID, email, password)
        
    def tabulate(self):
        
        blds = pd.Series(
        [int(i) for i in "1" * 6] +
        [int(i) for i in "2" * 6] +
        [int(i) for i in "3" * 6] +
        [int(i) for i in "4" * 5],
        index =
        ["small indigo plant", "small sugar mill",
         "small market", "hacienda", "construction hut",
         "small warehouse"] +
        ["indigo plant", "sugar mill", "hospice", "office",
         "large market", "large warehouse"] +
        ["tobacco storage", "coffee roaster", "factory",
         "university", "harbor", "wharf"] +
        ["guild hall", "customs house", "residence",
         "city hall", "fortress"]
         )
        
        # Build a template that tabulates the game progress for each player
        etc_template = pd.DataFrame({
        "builder": 0, "mayor": 0, "captain": 0, "craftsman": 0,
        "trader": 0, "settler": 0, "prospector": 0,
        "vp_bld": 0, "vp_bonus": 0, "vp_harbor": 0, "vp_ship": 0,
        "colonists": 0, "dblns": 0,
        "plant_corn": 0, "plant_indigo": 0, "plant_sugar": 0,
        "plant_tobacco": 0, "plant_coffee": 0,
        "plant_quarry": 0, "plant_rand": 0
        },
        index = [i for i in range(0, len(self.roles))]
        )
        
        # Build a template that tabulates buildings acquired
        blds_template = pd.DataFrame(blds).copy().T
        for i in range(0, len(self.roles)):
            blds_template.loc[i] = 0
        
        # Merge etc_template with blds_template
        game_template = pd.concat([etc_template, blds_template], axis = 1)
        
        # Give each player a game_template
        rawdata = {plyr: game_template.copy() for plyr in set(self.turnorder)}
        
        for i, role in enumerate(self.roles):
            
            # Tally the role choice for the respective role chooser
            rawdata[self.turnorder[i]][self.roleorder[i]][i] += 1
            
            # Find how a player benefited from each event in the role
            for event in role.role:
                
                if any([(name in event) for name in set(self.turnorder)]):
                    doer = [name for name in set(self.turnorder)
                            if ("$"+name in event)][0]
                else:
                    continue 
                
                if "doubloon from the role card" in event:
                    dblns = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    rawdata[doer]["dblns"][i] += dblns
                
                # settler phase
                if "got a new plantation" in event:
                    if "got a new plantation from the deck" in event:
                        rawdata[doer]["plant_rand"][i] += 1
                    else:
                        plants = ["corn", "indigo", "sugar",
                                  "tobacco", "coffee"]
                        new = [plt for plt in plants if ("$"+plt) in event][0]
                        rawdata[doer]["plant_"+new][i] += 1
                
                if "got a new quarry" in event:
                    rawdata[doer]["plant_quarry"][i] += 1
                
                # builder phase
                if "bought a new building for" in event:
                    new = [bld for bld in blds.index if ("$"+bld in event)][0]
                    cost = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    rawdata[doer][new][i] += 1
                    rawdata[doer]["vp_bld"][i] += blds[new]
                    rawdata[doer]["dblns"][i] -= cost
                
                # captain phase
                if "victory point for shipping" in event:
                    if "for shipping during the game" not in event:
                        total = int(re.findall("\$[0-9]+\s", event)[0][1:])
                        rawdata[doer]["vp_ship"][i] += total
                
                if "victory points for shipping" in event:
                    if "for shipping during the game" not in event:
                        total = int(re.findall("\$[0-9]+\s", event)[0][1:])
                        rawdata[doer]["vp_ship"][i] += total
                
                if "victory point from his harbor" in event:
                    total = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    rawdata[doer]["vp_harbor"][i] += total
                
                if "victory point as his privilege" in event:
                    total = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    rawdata[doer]["vp_ship"][i] += total
                
                # mayor phase
                if "colonist from the ship" in event:
                    total = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    rawdata[doer]["colonists"][i] += total
                
                if "colonists from the ship" in event:
                    total = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    rawdata[doer]["colonists"][i] += total
                
                if "colonist from the supply as his privilege" in event:
                    rawdata[doer]["colonists"][i] += 1
                
                # craftsman phase
                if "doubloon from his factory" in event:
                    dblns = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    rawdata[doer]["dblns"][i] += dblns              
                
                if "doubloons from his factory" in event:
                    dblns = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    rawdata[doer]["dblns"][i] += dblns    
                
                # trader phase
                if "from the sale" in event:
                    dblns = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    rawdata[doer]["dblns"][i] += dblns
                
                if len(re.findall("from his \w* markets?", event)) > 0:
                    dblns = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    rawdata[doer]["dblns"][i] += dblns
                
                if "doubloon as his privilege" in event:
                    dblns = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    rawdata[doer]["dblns"][i] += dblns
                
                # prospector phase
                if len(re.findall("doubloon$", event)) > 0:
                    dblns = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    rawdata[doer]["dblns"][i] += dblns
                
                # tally bonus points
                if "bonus points" in event:
                    vp = int(re.findall("\$[0-9]+\s", event)[0][1:])
                    rawdata[doer]["vp_bonus"][i] += vp
                
        # Update self.tabulate then return rawdata
        self.tabulate_val = rawdata
        return(self.tabulate_val)
        
    def cumsum(self):
        
        if self.tabulate_val is None:
            tabs = self.tabulate()
        else:
            tabs = self.tabulate_val
        cs = {}
        for plyr in set(self.turnorder):
            colSums = [sum(tabs[plyr][col]) for col in tabs[plyr].columns]
            cs.update({plyr: pd.Series(colSums, index = tabs[plyr].columns)})
            
        # Update self.cumsum then return cumsum
        self.cumsum_val = pd.DataFrame(cs)
        return(self.cumsum_val)
        
    def winner(self):
        
        if self.cumsum_val is None:
            cs = self.cumsum()
        else:
            cs = self.cumsum_val
        vps = ["vp_ship", "vp_bld", "vp_bonus", "vp_harbor"]
        final = {plyr: sum(cs[plyr][vps]) for plyr in set(self.turnorder)}
        best_score = max([final[plyr] for plyr in final])
        best_plyr = [plyr for plyr in final if (final[plyr] == best_score)]
        
        # Return name of best player
        if len(best_plyr) == 1:
            return(best_plyr[0])
        else:
            return(None)
