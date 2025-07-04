"""summary."""

from pathlib import Path

import pyretrosheet
from pyretrosheet.models.player import Player
from pyretrosheet.models.team import TeamLocation

players = {}
positions = [{}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}]
order = [{}, {}, {}, {}, {}, {}, {}, {}, {}, {}]
for game in pyretrosheet.load_games(2024, Path(Path(__file__).parent) / ".." / ".data" / "events"):
    team_location = TeamLocation.VISITING
    if game.home_team_id == "NYA":
        team_location = TeamLocation.HOME
    elif game.visiting_team_id != "NYA":
        continue
    for event in game.chronological_events:
        if isinstance(event, Player) and event.team_location == team_location and event.is_sub == False:
            if event.id not in players:
                players[event.id] = {"name": event.name, "position": [0] * 11, "order": [0] * 10}
            players[event.id]["position"][event.fielding_position] += 1
            players[event.id]["order"][event.batting_order_position] += 1
            if event.name not in positions[event.fielding_position]:
                positions[event.fielding_position][event.name] = 1
            else:
                positions[event.fielding_position][event.name] += 1
            if event.name not in order[event.batting_order_position]:
                order[event.batting_order_position][event.name] = 1
            else:
                order[event.batting_order_position][event.name] += 1
for player in players.values():
    print(player)
for pos, pos_players in zip(
    [
        "Pitcher",
        "Catcher",
        "First Base",
        "Second Base",
        "Third Base",
        "Shortstop",
        "Left Field",
        "Center Field",
        "Right Field",
        "Designated Hitter",
    ],
    positions[1:],
):
    print(pos)
    for name, count in sorted(pos_players.items(), key=lambda x: x[1], reverse=True):
        print(f"  {name} {count}")
print(order)
