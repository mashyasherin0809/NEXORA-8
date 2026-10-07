"""
Tests for NEXORA-8 Flask REST & SSE Server.
"""

import json
import pytest
from nexora.config import Config
from nexora.server.app import create_app


@pytest.fixture
def client():
    cfg = Config(model_provider="heuristic")
    app = create_app(cfg)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_api_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["agent"] == "NEXORA-8"


def test_api_stats(client):
    res = client.get("/api/stats")
    assert res.status_code == 200
    data = res.get_json()
    assert "total_sessions" in data
    assert "success_rate" in data


def test_api_analyze_diff(client):
    payload = {
        "before": "def f(): return 1\n",
        "after": "import os\ndef f(): return os.getcwd()\n",
        "modules": "os,math",
    }
    res = client.post("/api/analyze-diff", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["passed"] is True
    assert data["score"] >= 85


def test_api_analyze_diff_blocks_hallucination(client):
    payload = {
        "before": "def f(): return 1\n",
        "after": "import hallucinated_fake_package_xyz\ndef f(): return 1\n",
        "modules": "",
    }
    res = client.post("/api/analyze-diff", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["passed"] is False
    assert data["verdict"] == "Block"
