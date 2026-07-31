"""Stable string identifiers used across the domain.

`NewType` gives static type-checkers a way to catch e.g. a HoodId being
passed where a PlayerId is expected, while keeping the runtime
representation a plain `str` (serializable as-is, no custom codec needed).
"""

from typing import NewType

GameId = NewType("GameId", str)
PlayerId = NewType("PlayerId", str)
PawnId = NewType("PawnId", str)
OfficerId = NewType("OfficerId", str)
HoodId = NewType("HoodId", str)
SpotId = NewType("SpotId", str)
ContactId = NewType("ContactId", str)
CardId = NewType("CardId", str)
JobId = NewType("JobId", str)
SkillId = NewType("SkillId", str)
RaidCardId = NewType("RaidCardId", str)
TileId = NewType("TileId", str)
DecisionId = NewType("DecisionId", str)
CommandId = NewType("CommandId", str)
EventId = NewType("EventId", str)

DEN_ID = HoodId("den")
