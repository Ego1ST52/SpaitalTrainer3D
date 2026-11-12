import pytest

from logic.projections import mirror2d, project
from logic.shadows import LIGHTS, SHADOW_LEVELS, ShadowTaskGenerator
from logic.shapes import random_shape
import random

L_SHAPE = ((0, 0, 0), (1, 0, 0), (2, 0, 0), (2, 1, 0), (0, 0, 1))


@pytest.mark.parametrize("seed", range(10))
def test_opposite_views_are_mirror_images(seed):
    """Вид слева - зеркало вида справа, вид сзади - зеркало вида спереди."""
    shape = random_shape(random.Random(seed), 6)
    assert project(shape, "left") == mirror2d(project(shape, "right"))
    assert project(shape, "back") == mirror2d(project(shape, "front"))


def test_left_view_of_l_shape():
    # Слева «вправо» уходит -z: кубик сзади (z=1) окажется слева на картинке
    assert project(L_SHAPE, "left") == ((0, 0), (1, 0), (1, 1))


@pytest.mark.parametrize("level", list(SHADOW_LEVELS))
def test_generated_shadow_tasks(level):
    generator = ShadowTaskGenerator(seed=5)
    config = SHADOW_LEVELS[level]
    for _ in range(40):
        task = generator.generate(level)
        assert task.view in config["views"]
        assert task.correct_option == project(task.shape, task.view)
        assert len(set(task.options)) == len(task.options) == config["options"]
        side, target = LIGHTS[task.view]
        assert side in task.question and target in task.question
        assert task.tags[0] == f"light:{task.view}"
