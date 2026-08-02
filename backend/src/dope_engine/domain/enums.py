"""Core enumerations for the DOPE domain.

Values map 1:1 to the vocabulary agreed in docs/rules/RULES_CANONICAL.md;
keep new enum members in sync with that document rather than inventing
values here.
"""

from enum import StrEnum


class ControllerType(StrEnum):
    HUMAN = "human"
    BOT = "bot"


class PawnRole(StrEnum):
    IN_BASE = "in_base"
    CRIMINAL = "criminal"
    LINK = "link"
    GAMBLER = "gambler"
    RAT = "rat"


class DopeType(StrEnum):
    CAMALEONTE = "camaleonte"
    RANA = "rana"
    POLPO = "polpo"
    GUFO = "gufo"


class OfficerType(StrEnum):
    COP = "cop"
    FED = "fed"


class ActionType(StrEnum):
    PLACE_CRIMINAL = "place_criminal"
    MOVE_CRIMINAL = "move_criminal"
    BUY_DOPE = "buy_dope"
    SELL_DOPE = "sell_dope"
    CORRUPT_OFFICER = "corrupt_officer"
    BUY_OFFICER = "buy_officer"


class PokerSymbolColor(StrEnum):
    ROSA = "rosa"
    VERDE = "verde"
    AZZURRO = "azzurro"
    GRIGIO = "grigio"
    ARANCIONE = "arancione"


class GamePhase(StrEnum):
    SETUP = "setup"
    TIP_OFF = "tip_off"
    ACTION_PHASE = "action_phase"
    POKER_PHASE = "poker_phase"
    SHOWDOWN_PHASE = "showdown_phase"
    END_GAME_SCORING = "end_game_scoring"
    FINISHED = "finished"


class ActiveStep(StrEnum):
    NONE = "none"
    WAITING_FOR_GRIT_ACTION = "waiting_for_grit_action"
    WAITING_FOR_CARD_USAGE = "waiting_for_card_usage"
    WAITING_FOR_MAIN_ACTION_TARGETS = "waiting_for_main_action_targets"
    RESOLVING_TRIGGERED_EFFECTS = "resolving_triggered_effects"
    WAITING_FOR_LINK_EXTRA_ACTION = "waiting_for_link_extra_action"
    WAITING_FOR_CORRUPTION_ACTION = "waiting_for_corruption_action"
    WAITING_FOR_HAND_DISCARD = "waiting_for_hand_discard"
    WAITING_FOR_BRAWL_CARD = "waiting_for_brawl_card"
    WAITING_FOR_BRAWL_ASSIGNMENT = "waiting_for_brawl_assignment"
    WAITING_FOR_BRAWL_REWARD = "waiting_for_brawl_reward"
    WAITING_FOR_POKER_LAUNCH = "waiting_for_poker_launch"
    WAITING_FOR_POKER_BETS = "waiting_for_poker_bets"
    WAITING_FOR_POKER_CARD = "waiting_for_poker_card"
    WAITING_FOR_RAID_RESOLUTION = "waiting_for_raid_resolution"
    WAITING_FOR_STAIN_FOR_CASH_OFFER = "waiting_for_stain_for_cash_offer"
    WAITING_FOR_JOB_REWARD = "waiting_for_job_reward"
    WAITING_FOR_JAIL_ESCAPE = "waiting_for_jail_escape"
    WAITING_FOR_LINK_EVOLUTION_CHOICE = "waiting_for_link_evolution_choice"


class GameStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    WAITING_FOR_HUMAN = "waiting_for_human"
    FINISHED = "finished"


class JobBonusType(StrEnum):
    SKILL = "skill"
    LINK = "link"
    TWO_CARDS = "two_cards"
    NONE = "none"
