from core import stereo
from core.preferences import Preferences
from data.database import Database


def test_stereo_is_a_preference_off_by_default():
    prefs = Preferences()
    assert prefs.get("stereo") is False
    prefs.set("stereo", True)
    assert prefs.get("stereo") is True


def test_wanted_reads_last_player(tmp_path):
    path = tmp_path / "test.db"
    db = Database(path)
    anya = db.create_user("Аня")
    boris = db.create_user("Борис")
    db.set_setting(anya, "stereo", True)
    db.set_state("last_user", boris)
    db.close()
    assert stereo.wanted(path) is False          # последним играл Борис - без стерео

    db = Database(path)
    db.set_state("last_user", anya)
    db.close()
    assert stereo.wanted(path) is True


def test_wanted_without_players_or_database(tmp_path):
    assert stereo.wanted(tmp_path / "empty.db") is False
    assert stereo.wanted(tmp_path / "нет_папки" / "x.db") is False
