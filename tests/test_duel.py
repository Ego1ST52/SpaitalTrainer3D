import pytest

from logic.duel import Duel
from logic.session import TrainingSession

ANYA = {"id": 1, "name": "Аня", "color": "#22d3ee"}
BORIS = {"id": 2, "name": "Борис", "color": "#a78bfa"}


def played(duel, answers, seconds=5):
    session = TrainingSession(duel.mode, duel.level, len(answers), code=duel.code, locked=True)
    for answer in answers:
        session.record(answer, seconds)
    return session


def test_needs_two_different_players():
    with pytest.raises(ValueError):
        Duel([ANYA, ANYA], "rotation", "easy")
    with pytest.raises(ValueError):
        Duel([ANYA], "rotation", "easy")


def test_turns_and_winner_by_correct_answers():
    duel = Duel([ANYA, BORIS], "nets", "medium", seed=42)
    assert duel.code == "52-0042" and duel.current_player == ANYA
    duel.finish_turn(played(duel, [True, True, False]))
    assert duel.current_player == BORIS and not duel.is_done
    duel.finish_turn(played(duel, [True, False, False]))
    assert duel.is_done and duel.winner() == 0


def test_tie_breaks_by_points_then_time_then_draw():
    duel = Duel([ANYA, BORIS], "rotation", "easy", seed=1)
    duel.finish_turn(played(duel, [True, False], seconds=20))   # медленно - меньше баллов
    duel.finish_turn(played(duel, [True, False], seconds=2))
    assert duel.winner() == 1

    draw = Duel([ANYA, BORIS], "rotation", "easy", seed=1)
    draw.finish_turn(played(draw, [True, False]))
    draw.finish_turn(played(draw, [True, False]))
    assert draw.winner() is None


def test_foreign_session_and_extra_turn_rejected():
    duel = Duel([ANYA, BORIS], "rotation", "easy", seed=1)
    other = TrainingSession("rotation", "easy", 1, code="11-9999", locked=True)
    other.record(True, 1)
    with pytest.raises(ValueError):
        duel.finish_turn(other)
    duel.finish_turn(played(duel, [True]))
    duel.finish_turn(played(duel, [True]))
    with pytest.raises(ValueError):
        duel.finish_turn(played(duel, [True]))


def test_rematch_swaps_order_and_changes_tasks():
    duel = Duel([ANYA, BORIS], "count", "hard", seed=7)
    again = duel.rematch()
    assert again.players == [BORIS, ANYA] and again.mode == "count" and again.sessions == []
