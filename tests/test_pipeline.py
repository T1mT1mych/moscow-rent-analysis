"""Тесты для src/pipeline.py — порядок шагов и поведение при ошибке, без прогона ноутбуков"""

import src.pipeline as pipeline


def test_steps_follow_dependency_order():
    titles = [title for title, _ in pipeline.STEPS]
    assert titles.index('SQLite: таблицы и представления') < titles.index('Витрина данных для дашборда')
    # раздел 8.8 глубокого анализа читает витрину из базы
    assert titles.index('Витрина данных для дашборда') < titles.index('Глубокий анализ')
    # графики README выгружаются из уже выполненного ноутбука
    assert titles[-1] == 'Графики для README'


def test_list_prints_steps(capsys):
    assert pipeline.main(['--list']) == 0
    assert '9. Графики для README' in capsys.readouterr().out


def test_wrong_start_step_is_rejected():
    assert pipeline.main(['--from', '42']) == 2


def test_failed_step_stops_pipeline_and_tells_where_to_resume(monkeypatch, capsys):
    calls = []

    def broken():
        raise FileNotFoundError('clean_rentals.csv')

    monkeypatch.setattr(pipeline, 'STEPS', [
        ('первый', lambda: calls.append(1)),
        ('второй', broken),
        ('третий', lambda: calls.append(3)),
    ])
    assert pipeline.main([]) == 1
    assert calls == [1]
    err = capsys.readouterr().err
    assert 'Шаг 2 упал' in err and '--from 2' in err


def test_resume_skips_earlier_steps(monkeypatch):
    calls = []
    monkeypatch.setattr(pipeline, 'STEPS', [(str(i), lambda i=i: calls.append(i)) for i in range(1, 4)])
    assert pipeline.main(['--from', '2']) == 0
    assert calls == [2, 3]
