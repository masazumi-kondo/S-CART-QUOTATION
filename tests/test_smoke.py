import os
import tempfile

import pytest


@pytest.fixture()
def app(monkeypatch):
    d = tempfile.mkdtemp()
    monkeypatch.setenv("SCART_DB_PATH", os.path.join(d, "t.db"))
    monkeypatch.setenv("FLASK_DEBUG", "1")
    from app import create_app
    return create_app()


def test_fresh_db_boots(app):
    c = app.test_client()
    assert c.get("/health").status_code == 200
    assert c.get("/login").status_code == 200


def test_v2_rates_are_unified(app):
    from app.models.v2_calculation_setting import V2CalculationSetting
    from app.cost_utils import LABOR_RATE, DESIGN_SELL_RATE, SETUP_SELL_RATE
    with app.app_context():
        s = V2CalculationSetting.query.get(1)
        assert (s.cost_hourly_rate, s.sell_hourly_rate) == (6820, 12000)
        j = s.to_v2_json()
        assert (j["costHourlyRate"], j["sellHourlyRate"]) == (6820, 12000)
    assert (LABOR_RATE, DESIGN_SELL_RATE, SETUP_SELL_RATE) == (6820, 12000, 12000)


def test_production_persists_secret_key(monkeypatch, tmp_path):
    monkeypatch.setenv("FLASK_DEBUG", "0")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("SCART_DB_PATH", str(tmp_path / "t.db"))
    from app import create_app
    k1 = create_app().config["SECRET_KEY"]
    k2 = create_app().config["SECRET_KEY"]
    assert k1 == k2 and k1 != "dev_secret_key" and (tmp_path / ".secret_key").exists()


def test_journal_mode_not_wal(app):
    from app import db
    with app.app_context():
        mode = db.session.execute(db.text("PRAGMA journal_mode")).scalar()
        assert mode.lower() == "delete"
