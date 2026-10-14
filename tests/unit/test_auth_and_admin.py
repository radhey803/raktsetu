from starlette.testclient import TestClient

from bloodgrid.api.main import app

client = TestClient(app)


def test_auth_signup_and_login():
    signup_payload = {
        "email": "doctor@hospital.org",
        "password": "SecurePassword123!",
        "full_name": "Dr. Sarah Patel",
        "organization_name": "Anand Hospital",
    }
    resp = client.post("/v1/auth/register", json=signup_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["user"]["email"] == "doctor@hospital.org"
    assert "access_token" in data["tokens"]

    # Login
    login_payload = {"email": "doctor@hospital.org", "password": "SecurePassword123!"}
    l_resp = client.post("/v1/auth/login", json=login_payload)
    assert l_resp.status_code == 200
    l_data = l_resp.json()
    assert l_data["success"] is True
    assert "access_token" in l_data["tokens"]


def test_auth_login_invalid_password():
    payload = {"email": "doctor@hospital.org", "password": "WrongPassword!"}
    resp = client.post("/v1/auth/login", json=payload)
    assert resp.status_code == 401


def test_api_key_generation_and_listing():
    # Generate API key using valid test prefix key
    headers = {"X-API-Key": "bg_test_admin_key_12345"}
    gen_payload = {"key_name": "Emergency Service Bot", "tier": "developer"}
    resp = client.post("/v1/auth/api-keys", json=gen_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "api_key_secret" in data
    assert data["key_id"].startswith("bg_live_")

    # List API keys
    list_resp = client.get("/v1/auth/api-keys", headers=headers)
    assert list_resp.status_code == 200
    keys_data = list_resp.json()
    assert keys_data["success"] is True
    assert len(keys_data["keys"]) > 0


def test_admin_pipeline_runs_audit():
    headers = {"X-API-Key": "bg_test_admin_key_12345"}
    resp = client.get("/v1/admin/pipeline-runs?limit=5", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "runs" in data


def test_health_probes():
    h_resp = client.get("/healthz")
    assert h_resp.status_code == 200
    assert h_resp.json()["status"] == "ok"

    r_resp = client.get("/readyz")
    assert r_resp.status_code == 200
    assert r_resp.json()["status"] == "ready"


def test_static_pages_routes():
    assert client.get("/").status_code == 200
    assert client.get("/dashboard").status_code == 200
    assert client.get("/terms").status_code == 200
    assert client.get("/privacy").status_code == 200
    assert client.get("/disclaimer").status_code == 200
