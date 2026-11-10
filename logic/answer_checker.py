def check_answer(task, chosen_index):
    """True, если выбран правильный вариант. Некорректный выбор - ошибка."""
    is_int = isinstance(chosen_index, int) and not isinstance(chosen_index, bool)
    if not is_int or not 0 <= chosen_index < len(task.options):
        raise ValueError(f"Некорректный номер варианта: {chosen_index!r}")
    return chosen_index == task.correct_index