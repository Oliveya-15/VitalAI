import sqlite3

from sqlalchemy import create_engine, inspect

from tests.conftest import P, make_user

DIAB = {"Pregnancies": 2, "Glucose": 120, "BloodPressure": 70, "SkinThickness": 20, "Insulin": 80,
        "BMI": 28.0, "DiabetesPedigreeFunction": 0.4, "Age": 35}


def test_register_validation(anon):
    bad_pw = {"name": "Ann Lee", "email": "ann@example.com", "password": "short"}
    assert anon.post(f"{P}/auth/register", json=bad_pw).status_code == 422
    assert anon.post(f"{P}/auth/register", json=dict(bad_pw, password="onlyletters")).status_code == 422
    assert anon.post(f"{P}/auth/register", json=dict(bad_pw, password="Passw0rd1", email="not-an-email")).status_code == 422


def test_register_duplicate_login_me(anon):
    s = make_user(anon, "Dup@Example.com", name="Dup User")
    assert s["user"]["email"] == "dup@example.com"            # normalised
    assert "password" not in str(s["user"]).lower()
    r = anon.post(f"{P}/auth/register", json={"name": "Dup Two", "email": "dup@example.com", "password": "Passw0rd1"})
    assert r.status_code == 409
    assert anon.post(f"{P}/auth/login", json={"email": "dup@example.com", "password": "wrong-pass1"}).status_code == 401
    assert anon.post(f"{P}/auth/login", json={"email": "nobody@example.com", "password": "Passw0rd1"}).status_code == 401
    ok = anon.post(f"{P}/auth/login", json={"email": "DUP@example.com", "password": "Passw0rd1"})
    assert ok.status_code == 200
    me = anon.get(f"{P}/auth/me", headers={"Authorization": f"Bearer {ok.json()['token']}"})
    assert me.json()["name"] == "Dup User"


def test_protected_vs_public(anon):
    for method, path in [("get", "/diagnosis/models"), ("get", "/blood/stats"), ("get", "/assistant/status"),
                         ("get", "/diagnosis/history"), ("get", "/auth/me"), ("get", "/auth/activity"),
                         ("get", "/emergency/nearby?kind=hospital&lat=1&lon=1")]:
        assert getattr(anon, method)(f"{P}{path}").status_code == 401, path
    assert anon.post(f"{P}/assistant/chat", json={"message": "hi"}).status_code == 401
    assert anon.get(f"{P}/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    # public on purpose: emergency numbers and triage
    assert anon.get(f"{P}/emergency/numbers").json()["ambulance"] == "108"
    assert anon.post(f"{P}/emergency/triage", json={"text": "chest pain"}).json()["level"] == "emergency"
    assert anon.get(f"{P}/health").status_code == 200


def test_activity_and_summary(client):
    assert client.post(f"{P}/diagnosis/diabetes/predict", json={"values": DIAB}).status_code == 200
    client.post(f"{P}/tools/report", json={"text": "Fasting Glucose 130"})
    feed = client.get(f"{P}/auth/activity").json()
    types = [a["type"] for a in feed]
    assert "diagnosis" in types and "report_analyzed" in types and "account" in types
    assert feed[0]["created_at"] >= feed[-1]["created_at"]            # newest first
    summ = client.get(f"{P}/auth/summary").json()
    assert summ["assessments"] >= 1 and summ["last_assessment"]["disease"] == "diabetes"


def test_profile_update_and_password_change(anon):
    s = make_user(anon, "prof@example.com", name="Prof User")
    h = {"Authorization": f"Bearer {s['token']}"}
    r = anon.patch(f"{P}/auth/me", headers=h, json={"name": "Prof Updated", "city": "Siliguri", "blood_group": "B+", "phone": "9222222222"})
    assert r.status_code == 200 and r.json()["blood_group"] == "B+"
    assert anon.patch(f"{P}/auth/me", headers=h, json={"name": "X", "blood_group": "Z+"}).status_code == 422
    body = {"current_password": "nope-nope1", "new_password": "NewPassw0rd"}
    assert anon.post(f"{P}/auth/change-password", headers=h, json=body).status_code == 403
    body["current_password"] = "Passw0rd1"
    assert anon.post(f"{P}/auth/change-password", headers=h, json=dict(body, new_password="weak")).status_code == 422
    assert anon.post(f"{P}/auth/change-password", headers=h, json=body).status_code == 200
    assert anon.post(f"{P}/auth/login", json={"email": "prof@example.com", "password": "Passw0rd1"}).status_code == 401
    assert anon.post(f"{P}/auth/login", json={"email": "prof@example.com", "password": "NewPassw0rd"}).status_code == 200


def test_data_is_isolated_between_users(anon):
    a = {"Authorization": f"Bearer {make_user(anon, 'iso-a@example.com')['token']}"}
    b = {"Authorization": f"Bearer {make_user(anon, 'iso-b@example.com')['token']}"}
    anon.post(f"{P}/diagnosis/diabetes/predict", json={"values": DIAB}, headers=a)
    assert len(anon.get(f"{P}/diagnosis/history", headers=a).json()) == 1
    assert anon.get(f"{P}/diagnosis/history", headers=b).json() == []
    assert all(x["type"] != "diagnosis" for x in anon.get(f"{P}/auth/activity", headers=b).json())


def test_donor_ownership(anon):
    a = {"Authorization": f"Bearer {make_user(anon, 'don-a@example.com')['token']}"}
    b = {"Authorization": f"Bearer {make_user(anon, 'don-b@example.com')['token']}"}
    donor = {"name": "Don A", "phone": "9444444444", "blood_group": "A+", "city": "Siliguri", "consent": True}
    assert anon.post(f"{P}/blood/donors", json=donor, headers=a).status_code == 201
    assert anon.post(f"{P}/blood/donors", json=dict(donor, name="Hijack"), headers=b).status_code == 409   # cannot overwrite
    assert anon.post(f"{P}/blood/donors/opt-out", json={"phone": "9444444444"}, headers=b).status_code == 403
    assert anon.post(f"{P}/blood/donors", json=dict(donor, name="Don A2"), headers=a).json()["updated"] is True
    assert anon.post(f"{P}/blood/donors/opt-out", json={"phone": "9444444444"}, headers=a).json()["removed"] == 1


def test_delete_account_removes_personal_data(anon):
    s = make_user(anon, "bye@example.com")
    h = {"Authorization": f"Bearer {s['token']}"}
    anon.post(f"{P}/diagnosis/diabetes/predict", json={"values": DIAB}, headers=h)
    req = {"patient_name": "Pat", "blood_group": "O+", "units": 1, "hospital": "City Hosp", "city": "Siliguri",
           "urgency": "normal", "contact_phone": "9555555555"}
    anon.post(f"{P}/blood/requests", json=req, headers=h)
    open_before = [r for r in anon.get(f"{P}/blood/requests", headers=h).json() if r["contact_phone"] == "9555555555"]
    assert open_before
    assert anon.request("DELETE", f"{P}/auth/me", headers=h, json={"password": "wrong-pass1"}).status_code == 403
    assert anon.request("DELETE", f"{P}/auth/me", headers=h, json={"password": "Passw0rd1"}).status_code == 200
    assert anon.get(f"{P}/auth/me", headers=h).status_code == 401                      # token no longer valid
    other = {"Authorization": f"Bearer {make_user(anon, 'bye2@example.com')['token']}"}
    assert not [r for r in anon.get(f"{P}/blood/requests", headers=other).json() if r["contact_phone"] == "9555555555"]


def test_login_rate_limit(anon):
    make_user(anon, "brute@example.com")
    codes = [anon.post(f"{P}/auth/login", json={"email": "brute@example.com", "password": "bad-pass-1"}).status_code for _ in range(10)]
    assert codes[0] == 401 and codes[-1] == 429
    # even the right password is refused while blocked
    assert anon.post(f"{P}/auth/login", json={"email": "brute@example.com", "password": "Passw0rd1"}).status_code == 429


def test_migration_adds_user_id_to_existing_db(tmp_path, monkeypatch):
    """Simulates your live Neon DB: an `assessments` table created BEFORE login existed."""
    path = tmp_path / "old.db"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE assessments (id INTEGER PRIMARY KEY, client_id VARCHAR(64) NOT NULL, disease VARCHAR(32))")
    con.execute("INSERT INTO assessments (client_id, disease) VALUES ('old-browser', 'heart')")
    con.commit(); con.close()
    eng = create_engine(f"sqlite:///{path}")
    import app.migrate as migrate
    monkeypatch.setattr(migrate, "engine", eng)
    migrate.run()
    migrate.run()                                     # idempotent
    assert "user_id" in {c["name"] for c in inspect(eng).get_columns("assessments")}
    with eng.connect() as conn:                       # old rows survive
        assert conn.exec_driver_sql("SELECT count(*) FROM assessments").scalar() == 1
