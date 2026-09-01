from __future__ import annotations

import json
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_strategy_lab_route(client):
    res = client.get("/strategy-lab")
    assert res.status_code == 200
    assert b"UNLOAN" in res.data
    assert b"Strategy Lab" in res.data
    assert b"UPSTOX ALGOVERSE INTELLIGENCE" in res.data


def test_strategy_lab_data_api(client):
    res = client.get("/api/strategy-lab/data")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["ok"] is True
    data = json_data["data"]
    assert "candidates" in data
    assert "pipeline_working" in data
    assert "live_status" in data
    assert "equity_curve" in data
    assert "price_vwap_chart" in data
    assert "trade_audit_log" in data
    assert data["hard_loss_limit_inr"] == 1000.0
    cands = data["candidates"]
    if cands:
        c0 = cands[0]
        assert "in_sample" in c0
        assert "out_of_sample" in c0
        assert "regime_breakdown" in c0


def test_strategy_lab_import_algoverse_api(client):
    payload = {
        "name": "Algoverse Test Strategy",
        "direction": "LONG",
        "adx_threshold": 25.0,
        "vwap_mode": "STRICT",
        "stop_loss_pct": 1.0,
        "target_pct": 1.5,
        "entry_time": "09:20",
        "backtest_pnl": 4800.0,
        "win_rate": 66.0,
        "avg_win": 400.0,
        "avg_loss": 200.0,
        "max_drawdown": 380.0,
        "trade_count": 22,
    }
    res = client.post("/api/strategy-lab/import-algoverse", json=payload)
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["ok"] is True
    candidate = json_data["candidate"]
    assert candidate["backtest_source"] == "ALGOVERSE_SECONDARY"
    assert candidate["status"] == "SECONDARY_REFERENCE"


def test_strategy_lab_approve_api(client):
    res = client.post("/api/strategy-lab/approve", json={"candidate_id": "NOTRADE"})
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["ok"] is True
    assert json_data["status"] == "NO_TRADE"
