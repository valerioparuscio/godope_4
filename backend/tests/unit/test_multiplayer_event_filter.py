"""What a viewer may know of each kind of event (GPT_MULTIPLAYER.md section 15)."""

from __future__ import annotations

from dataclasses import fields

import pytest

from dope_engine.application.multiplayer.event_filter import (
    PUBLIC_EVENT_TYPES,
    REDACTORS,
    all_event_types,
    filter_event_for_viewer,
    filter_events_for_viewer,
)
from dope_engine.domain import events as ev
from dope_engine.domain.enums import DopeType
from dope_engine.domain.ids import CardId, ContactId, EventId, GameId, PlayerId, SkillId

HEADER = {"event_id": EventId("e1"), "game_id": GameId("g"), "revision": 5}
ALICE, BOB, CARL = PlayerId("player_0"), PlayerId("player_1"), PlayerId("player_2")

# Event fields that name a card (or the seed): only these public events may carry one.
CARD_FIELDS = {"card_id", "card_ids", "gamble_card_id", "drawn_card_ids", "stolen_card_id", "seed"}
PUBLIC_EVENTS_THAT_NAME_A_CARD = {
    ev.MarketingCardPlayed,  # played face up
    ev.CustomerCardBoostPlayed,  # played face up
    ev.PokerLaunched,  # the Gamble card is on the table
    ev.PokerCardRevealed,  # a reveal
    ev.BrawlCardRevealed,  # every card is turned over at once
}


def test_every_event_type_is_classified_exactly_once() -> None:
    every = set(all_event_types())

    assert every == set(PUBLIC_EVENT_TYPES) | set(REDACTORS)
    assert not set(PUBLIC_EVENT_TYPES) & set(REDACTORS)


def test_no_public_event_names_a_card_unless_it_was_reviewed_as_played_face_up() -> None:
    for event_type in PUBLIC_EVENT_TYPES:
        names_a_card = {f.name for f in fields(event_type)} & CARD_FIELDS
        if names_a_card:
            assert event_type in PUBLIC_EVENTS_THAT_NAME_A_CARD, (
                f"{event_type.__name__} is public but carries {sorted(names_a_card)}: "
                "redact it, or review it into PUBLIC_EVENTS_THAT_NAME_A_CARD"
            )


def test_an_unclassified_event_is_refused_rather_than_passed_through() -> None:
    class Surprise(ev.DomainEvent):
        pass

    with pytest.raises(ValueError, match="no visibility rule"):
        filter_event_for_viewer(Surprise(**HEADER), ALICE)


def test_a_drawn_card_is_known_only_to_whoever_drew_it() -> None:
    drawn = ev.CardDrawn(
        **HEADER, player_id=ALICE, contact_id=ContactId("preti"), card_id=CardId("c1")
    )

    assert filter_event_for_viewer(drawn, ALICE) == drawn
    seen_by_bob = filter_event_for_viewer(drawn, BOB)
    assert seen_by_bob.card_id is None
    # The fact stays: who drew from which deck.
    assert (seen_by_bob.player_id, seen_by_bob.contact_id) == (ALICE, ContactId("preti"))


def test_discarded_cards_keep_their_number_but_not_their_identity() -> None:
    discarded = ev.CardsDiscarded(**HEADER, player_id=ALICE, card_ids=(CardId("c1"), CardId("c2")))

    assert filter_event_for_viewer(discarded, ALICE) == discarded
    assert filter_event_for_viewer(discarded, BOB).card_ids == (None, None)


def test_cards_drawn_as_a_job_reward_are_private_to_the_player() -> None:
    claimed = ev.JobBonusClaimed(
        **HEADER,
        player_id=ALICE,
        job_id="job_01",
        column_index=2,
        bonus_type="two_cards",
        contact_id=ContactId("preti"),
        skill_id=SkillId("skill_preti_1"),
        link_pawn_id=None,
        drawn_card_ids=(CardId("c1"), CardId("c2")),
    )

    assert filter_event_for_viewer(claimed, ALICE) == claimed
    seen_by_bob = filter_event_for_viewer(claimed, BOB)
    assert seen_by_bob.drawn_card_ids == (None, None)
    # A Skill is on the table for everyone.
    assert seen_by_bob.skill_id == SkillId("skill_preti_1")


def test_a_stolen_card_is_known_to_the_two_who_swapped_it_and_to_nobody_else() -> None:
    stolen = ev.BrawlLoserRewardChosen(
        **HEADER,
        winner_id=ALICE,
        loser_id=BOB,
        reward_type="card",
        stolen_card_id=CardId("c9"),
        stolen_dope_type=DopeType.RANA,
        money_taken=2,
    )

    assert filter_event_for_viewer(stolen, ALICE) == stolen
    assert filter_event_for_viewer(stolen, BOB) == stolen
    seen_by_carl = filter_event_for_viewer(stolen, CARL)
    assert seen_by_carl.stolen_card_id is None
    assert (seen_by_carl.money_taken, seen_by_carl.stolen_dope_type) == (2, DopeType.RANA)


def test_the_seed_never_leaves_the_server() -> None:
    started = ev.GameStarted(**HEADER, seed=123456, rules_version="x", player_ids=(ALICE, BOB))

    for viewer in (ALICE, BOB, CARL):
        assert filter_event_for_viewer(started, viewer).seed == 0
    assert started.seed == 123456  # the original is untouched


def test_public_events_pass_through_unchanged() -> None:
    played = ev.CriminalPlaced(**HEADER, player_id=ALICE, pawn_id="p1", hood_id="hood_q1", cost=2)
    revealed = ev.BrawlCardRevealed(**HEADER, player_id=ALICE, card_id=CardId("c3"), gun_count=1)

    assert filter_events_for_viewer([played, revealed], BOB) == (played, revealed)
