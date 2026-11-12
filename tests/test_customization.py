"""Кастомизация: скины куба, настройки игрока, коды тренировок."""

import pytest

from core.preferences import DEFAULTS, OPTIONS, Preferences
from logic.cube_skins import (SKINS, face_mark, face_names, option_text, shows_marks,
                              start_description)
from logic.rotations import IDENTITY, apply_sequence, face_at
from logic.task_generator import RotationTaskGenerator, top_color
from logic.training_code import CODE_LENGTH, make_code, parse_code
from logic.matching_tasks import MatchingTaskGenerator
from logic.projections import ProjectionTaskGenerator
from logic.construction import ConstructionTaskGenerator


# ---------- скины куба ----------
@pytest.mark.parametrize("skin", list(SKINS))
def test_every_skin_names_all_six_faces_differently(skin):
    names = face_names(skin)
    assert set(names) == {"+X", "-X", "+Y", "-Y", "+Z", "-Z"}
    assert len(set(names.values())) == 6


def test_dice_opposite_faces_sum_to_seven():
    names = face_names("dice")
    for a, b in (("+X", "-X"), ("+Y", "-Y"), ("+Z", "-Z")):
        assert int(names[a]) + int(names[b]) == 7


def test_marks_are_distinct_and_not_digit_like():
    letters = [face_mark("classic", f) for f in face_names("classic")]
    assert len(set(letters)) == 6
    assert face_mark("classic", "+Y") == "БЕ"
    assert face_mark("classic", "-Z") == "ЗЕ"


def test_colorblind_skin_always_shows_marks():
    assert shows_marks("colorblind", False)
    assert not shows_marks("classic", False)
    assert shows_marks("classic", True)


def test_texts():
    assert start_description("classic") == "Сверху белая грань, спереди зелёная"
    assert start_description("dice") == "Сверху 1 точка, спереди 2 точки"
    assert option_text("dice", "5") == "5 точек"
    assert option_text("classic", "синий") == "Синий"


@pytest.mark.parametrize("skin", list(SKINS))
def test_rotation_answers_follow_skin(skin):
    names = face_names(skin)
    generator = RotationTaskGenerator(seed=11, face_names=names)
    for _ in range(30):
        task = generator.generate("hard")
        top_face = face_at(apply_sequence(IDENTITY, task.moves), "+Y")
        assert task.correct_option == names[top_face]
        assert set(task.options) <= set(names.values())


def test_default_names_unchanged():
    task = RotationTaskGenerator(seed=1).generate("easy")
    assert task.correct_option == top_color(apply_sequence(IDENTITY, task.moves))


# ---------- настройки ----------
def test_preferences_defaults_and_validation():
    p = Preferences()
    assert p.as_dict() == DEFAULTS
    p.set("cube_skin", "dice")
    assert p.get("cube_skin") == "dice"
    with pytest.raises(ValueError):
        p.set("session_length", 7)
    with pytest.raises(KeyError):
        p.set("volume", 3)


def test_preferences_load_skips_broken_values():
    p = Preferences({"cube_skin": "dice", "session_length": "много", "unknown": 1})
    assert p.get("cube_skin") == "dice"
    assert p.get("session_length") == DEFAULTS["session_length"]


def test_defaults_are_allowed_values():
    p = Preferences()
    for key, value in DEFAULTS.items():
        p.set(key, value)                   # не должно быть ошибки


def test_custom_plan_is_validated_and_copied():
    p = Preferences()
    plan = p.get("custom_plan")
    plan["modes"].append("matching")        # изменили копию - настройка не тронута
    assert "matching" not in p.get("custom_plan")["modes"]
    with pytest.raises(ValueError):
        p.set("custom_plan", {"modes": []})
    p.set("custom_plan", plan)
    assert "matching" in p.get("custom_plan")["modes"]


def test_session_length_for_construction_is_shorter():
    p = Preferences({"session_length": 20})
    assert p.session_length("rotation") == 20
    assert p.session_length("construction") == 10
    p.set("session_length", 5)
    assert p.session_length("construction") == 3


# ---------- коды тренировок ----------
def test_code_round_trip():
    for mode in ("rotation", "matching", "projection", "construction"):
        for level in ("easy", "medium", "hard"):
            code = make_code(mode, level, 42)
            assert parse_code(code) == (mode, level, 42)


def test_code_format_and_tolerant_input():
    assert make_code("projection", "easy", 4821) == "31-4821"
    assert parse_code(" 31 4821 ") == ("projection", "easy", 4821)
    assert parse_code("314821") == ("projection", "easy", 4821)


@pytest.mark.parametrize("bad", ["", "12-34", "01-0000", "14-0000", "ab-cdef", "31-48211"])
def test_bad_codes_rejected(bad):
    with pytest.raises(ValueError):
        parse_code(bad)


@pytest.mark.parametrize("generator_class", [RotationTaskGenerator, MatchingTaskGenerator,
                                             ProjectionTaskGenerator,
                                             ConstructionTaskGenerator])
def test_same_code_gives_same_tasks(generator_class):
    """Главное свойство кода: одно зерно - одинаковые задания у всех."""
    a, b = generator_class(seed=4821), generator_class(seed=4821)
    assert [a.generate("medium") for _ in range(10)] == [b.generate("medium") for _ in range(10)]


def test_code_session_lengths_cover_all_modes():
    from logic.training_code import MODE_DIGITS
    assert set(CODE_LENGTH) == set(MODE_DIGITS)
