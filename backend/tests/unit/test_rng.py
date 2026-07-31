import json

from dope_engine.domain.rng import GameRandom


def test_same_seed_produces_same_sequence() -> None:
    a = GameRandom.from_seed(123)
    b = GameRandom.from_seed(123)

    seq_a = [a.randint(1, 1_000_000) for _ in range(20)]
    seq_b = [b.randint(1, 1_000_000) for _ in range(20)]

    assert seq_a == seq_b


def test_different_seeds_diverge() -> None:
    a = GameRandom.from_seed(1)
    b = GameRandom.from_seed(2)

    seq_a = [a.randint(1, 1_000_000) for _ in range(20)]
    seq_b = [b.randint(1, 1_000_000) for _ in range(20)]

    assert seq_a != seq_b


def test_state_round_trip_resumes_identical_sequence() -> None:
    rng = GameRandom.from_seed(42)
    rng.randint(1, 100)  # advance a bit before snapshotting
    state = rng.get_state()

    # JSON round-trip, since this is exactly how it travels through a save file.
    state_json = json.loads(json.dumps(state))

    resumed = GameRandom.from_state(state_json)
    continued_original = [rng.randint(1, 1_000_000) for _ in range(10)]
    continued_resumed = [resumed.randint(1, 1_000_000) for _ in range(10)]

    assert continued_original == continued_resumed


def test_derive_stream_is_deterministic_given_same_parent_state() -> None:
    parent_a = GameRandom.from_seed(99)
    parent_b = GameRandom.from_seed(99)

    child_a = parent_a.derive_stream("bot_player_1")
    child_b = parent_b.derive_stream("bot_player_1")

    seq_a = [child_a.randint(0, 999) for _ in range(10)]
    seq_b = [child_b.randint(0, 999) for _ in range(10)]
    assert seq_a == seq_b


def test_derive_stream_differs_by_name() -> None:
    parent = GameRandom.from_seed(99)
    child_1 = parent.derive_stream("bot_player_1")
    child_2 = GameRandom.from_seed(99).derive_stream("bot_player_2")

    seq_1 = [child_1.randint(0, 999) for _ in range(10)]
    seq_2 = [child_2.randint(0, 999) for _ in range(10)]
    assert seq_1 != seq_2


def test_shuffle_and_sample_are_seed_deterministic() -> None:
    a = GameRandom.from_seed(5)
    b = GameRandom.from_seed(5)

    items_a = list(range(20))
    a.shuffle(items_a)
    items_b = list(range(20))
    b.shuffle(items_b)
    assert items_a == items_b

    assert a.sample(list(range(10)), 3) == b.sample(list(range(10)), 3)
