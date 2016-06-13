<!-- README.md is generated from README.Rmd. Please edit that file -->
Quick start
-----------

Welcome to the `bga` GitHub page!

This module provides object classes and methods to facilitate access to board game data from the website *Board Game Arena*. Although most of the tools included within this module apply specifically the analysis of board game data from the board game *Puerto Rico*, some of these methods could apply more broadly to other *Board Game Arena* games. In either case, you will need an account e-mail and password to retrieve the data. To begin, save the `bga.py` script to your *Python* working directory and import the module.

``` python
import bga
```

Class structure
---------------

This module contains three principal classes which serve to organize the board game data. A `GameSeries` object contains a list of `Game` objects which each contains a list of `Role` objects. These `Role` objects contain all events that occurred during a complete turn. Ultimately, the extent and type of information stored within a single `Role` object depends on how *Board Game Arena* defines the `Role` bounds within their cached log files.

Specific sub-classes -- e.g., `PuertoRico` (a sub-class of `Game`) and `PRSeries` (a sub-class of `GameSeries`) -- provide analytical methods specific to a board game. At the time of writing, *Puerto Rico* is the only board game supported in this way.

In any case, the user can import data directly from *Board Game Arena* using a class constructor along with one or more unique table IDs. In the example below, we import a series of *Puerto Rico* games played between myself and two other players.

``` python
tableIDs = [21730862, 21036898, 21036338, 20903484, 20660296, 20213069]
series = bga.PRSeries(tableIDs, your_email, your_password)
```

Puerto Rico
-----------

At the time of writing, the `PRSeries` sub-class includes two kinds of methods to aid in analyzing *Puerto Rico* game data. The first method tabulates the average board game setup held by the winning and losing players between turns `start` and `end`. In the example below, we calculate the average frequency of ownership for the "Factory" game piece by the winning and losing players. Note that by excluding the arguments `start` and `end`, we perform these averages using the endgame board.

``` python
series.winnerHeld("factory")
```

The wrapper method `.winnerHeldAll()` replicates this calculation for every recorded board game variable. Another wrapper method, `.winnerHeldAllT()`, replicates this calculation for every recorded variable at every turn.

``` python
series.winnerHeldAll(start = 4, end = 7)
```

Another argument, `playerPos`, performs the respective analysis using only data from players belonging to the specified turn order position. For example, `playerPos = 0` retrieves data for the first player only.

``` python
series.winnerHeldAllT(playerPos = 0)
```

The second method simply returns the board game scenarios for all winning and losing players, without simplifying the data through the use of summary statistics. These long-form data may provide useful input for machine learning applications or other custom analyses. This method, `.winnerCumsums`, also accepts the arguments `start`, `end`, and `playerPos`.

``` python
series.winnerCumsums()
```

Other methods unique to the `PuertoRico` sub-class include `.tabulate()`, `.cumsum()`, and `.winner()` which calculate the per-turn events, cumulative sum of the per-turn events, and the game winner, respectively.
