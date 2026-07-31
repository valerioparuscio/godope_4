"""Deterministic random number generation for the game engine.

CLAUDE.md forbids calling global random functions directly: every random
choice the engine makes must flow through a `GameRandom` instance whose
seed (or full internal state) is part of the saved game, so that
identical (initial state, seed, command sequence) always replays to the
identical outcome.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")

# random.Random.getstate() returns (version, internal_state_tuple, gauss_next).
# The middle element is kept as a `list` (not `tuple`) here purely so the
# generic dataclass codec in serialization.py — which needs a fixed-arity
# `get_args()` per tuple slot — can round-trip this through JSON.
RngState = tuple[int, list[int], float | None]


@dataclass
class GameRandom:
    """Wraps `random.Random` with JSON-safe (de)serialization and the
    ability to derive independent, reproducible child streams (e.g. one
    per bot) without ever touching the global `random` module.
    """

    _random: random.Random

    @classmethod
    def from_seed(cls, seed: int) -> GameRandom:
        return cls(random.Random(seed))

    @classmethod
    def from_state(cls, state: RngState) -> GameRandom:
        r = random.Random()
        version, internal_state, gauss_next = state
        r.setstate((version, tuple(internal_state), gauss_next))
        return cls(r)

    def get_state(self) -> RngState:
        version, internal_state, gauss_next = self._random.getstate()
        return (version, list(internal_state), gauss_next)

    def derive_stream(self, name: str) -> GameRandom:
        """Create a reproducible, independent child stream.

        Consumes entropy from this stream (so it participates in the
        deterministic sequence like any other draw) then mixes it with
        `name` so distinctly-named children never collide.
        """
        salt = self._random.getrandbits(64)
        digest = hashlib.sha256(f"{salt}:{name}".encode()).digest()
        child_seed = int.from_bytes(digest[:8], byteorder="big")
        return GameRandom.from_seed(child_seed)

    def randint(self, a: int, b: int) -> int:
        return self._random.randint(a, b)

    def choice(self, seq: list[T]) -> T:
        return self._random.choice(seq)

    def shuffle(self, seq: list[T]) -> None:
        self._random.shuffle(seq)

    def sample(self, seq: list[T], k: int) -> list[T]:
        return self._random.sample(seq, k)
