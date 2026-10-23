"""The game designer's qualitative Job x Raid matrix (2026-10-22), used only as a benchmark for the simulations.

+5 = working on that Job helps (almost directly) to satisfy that Raid; 0 = nearly independent; -5 = working on that Job
goes the opposite way. A hypothesis to check, not something the bots use. Columns follow COLS:
-Crimes (raid_07), -$ (raid_06), -Rats (raid_02), -Dope (raid_03), +Poker (raid_04), +Cops (raid_05), +Links (raid_01).
"""

COLS = ["raid_07", "raid_06", "raid_02", "raid_03", "raid_04", "raid_05", "raid_01"]
NAMES = ["-Crimes", "-$", "-Rats", "-Dope", "+Poker", "+Cops", "+Links"]
THEORY = {
    "job_01": [3, 0, -1, 0, 1, 2, 5],      # Vinci 1 Rissa
    "job_02": [0, 4, 0, 0, 0, 5, 0],       # 1 Cop/Fed
    "job_07": [-5, 0, -1, 0, 0, 1, 1],     # Criminali in 6 Hoods
    "job_04": [3, 0, -4, 0, 0, 0, 2],      # 2 Rats
    "job_05": [0, 4, -1, -5, 0, 1, 0],     # 4 Dope nel Covo
    "job_06": [4, -1, 1, 1, 2, 1, 5],      # 4 Link
    "job_03": [3, -3, 0, 0, 5, 0, 3],      # 2 Chip Poker
    "job_08": [-5, 0, -1, 0, 0, 1, 1],     # 10 Criminali fuori
    "job_09": [2, -5, 0, 4, 1, 0, 3],      # 30 dollari
}
