"""summary."""

from pathlib import Path

import pyretrosheet
from pyretrosheet.models.play import Play
from pyretrosheet.models.player import Player
from pyretrosheet.models.radj import RAdj
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
    last_inning = -1
    last_team = TeamLocation.HOME
    base = []
    outs = 3
    for event in game.chronological_events:
        if isinstance(event, RAdj):
            assert outs == 3 or (outs == 0 and len(base) == 0)
            if outs == 3:
                outs = 0
                if last_team == TeamLocation.HOME:
                    last_inning += 1
                    last_team = TeamLocation.VISITING
                else:
                    last_team = TeamLocation.HOME
            base = [event.base]
            print("radj", base)
        elif isinstance(event, Play):
            if event.inning != last_inning or event.team_location != last_team:
                base = []
                assert outs == 3
                outs = 0
            print(event.raw)
            for adv in event.event.advances:
                print(" ", adv.from_base, "out" if adv.is_out else adv.to_base)
            out, score, bat_end, base = event.event.get_final_stat(base)
            outs += out
            print(outs, out, score, bat_end, base)
            print(event.event.description.put_out_at_base)
            last_inning = event.inning
            last_team = event.team_location
        else:
            print(event)
