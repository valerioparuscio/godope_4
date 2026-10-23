"""Variance of final points explained by what the Raids did to the player (times caught, stains applied), alone and
on top of the initial Jobs. Caveat: it is an outcome, partly caused by the Jobs and by what the player did."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import raidlib as R  # noqa: E402
import variance_shares as V  # noqa: E402
sys.stdout.reconfigure(encoding="utf-8")
for arg in sys.argv[1:]:
    label, files = arg.split("=", 1)
    df, games = R.load(files.split(","))
    J, Rm, JR = V.build(df)
    O = np.column_stack([df[c].values for c in ("caught1", "caught2", "caught3", "stain1", "stain2", "stain3")]).astype(float)
    g = df.game.values
    out = {}
    for view, y in (("total", df.pts.values.astype(float)), ("within", df.pts_c.values)):
        out[view] = (V.cv_r2(J, y, g), V.cv_r2(O, y, g), V.cv_r2(np.column_stack([J, O]), y, g))
    print(f"## {label} ({games.game.nunique()} partite)")
    for view, name in (("total", "rispetto alla media generale"), ("within", "rispetto alla media del proprio tavolo")):
        j, o, jo = out[view]
        print(f"- {name}: Job iniziali {100 * j:.1f}%; esito delle Retate (quante volte preso, macchie) {100 * o:.1f}%; insieme {100 * jo:.1f}%")
    print()
