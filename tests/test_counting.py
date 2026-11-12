import pytest

from logic.counting import (COUNT_LEVELS, CountTaskGenerator, cubes, hidden_count, is_hidden,
                            total_cubes)


def test_total_and_list_of_cubes():
    heights = ((2, 1), (0, 3))
    assert total_cubes(heights) == 6
    assert len(cubes(heights)) == 6


def test_single_column_has_no_hidden_cubes():
    # Один столбик: видна передняя и левая грань каждого кубика
    assert hidden_count(((3,),)) == 0


def test_cube_surrounded_front_left_top_is_hidden():
    # Кубик (1, 1, 0) закрыт сверху (столбик 2), спереди (ряд 0) и слева (столбец 0)
    heights = ((1, 1), (1, 2))
    assert is_hidden(heights, 1, 1, 0)
    assert not is_hidden(heights, 1, 1, 1)       # верхний кубик открыт сверху
    assert hidden_count(heights) == 1


@pytest.mark.parametrize("level", list(COUNT_LEVELS))
def test_generated_tasks(level):
    generator = CountTaskGenerator(seed=6)
    config = COUNT_LEVELS[level]
    for _ in range(40):
        task = generator.generate(level)
        assert task.correct_option == total_cubes(task.heights)
        assert hidden_count(task.heights) >= 1                 # есть что «найти»
        assert len(set(task.options)) == len(task.options) == config["options"]
        assert list(task.options) == sorted(task.options)      # числа по порядку
        assert all(n > 0 for n in task.options)
        # Неверный вариант «только видимые» есть всегда
        visible = total_cubes(task.heights) - hidden_count(task.heights)
        assert visible in task.options
        assert max(max(row) for row in task.heights) <= config["max_height"]


def test_visible_only_mistake_is_tagged():
    task = CountTaskGenerator(seed=2).generate("medium")
    visible = total_cubes(task.heights) - hidden_count(task.heights)
    assert task.answer_tags(task.options.index(visible)) == ("chose:visible_only",)
    assert task.answer_tags(task.correct_index) == ()
