P = "/api/v1"

DIAB = {"Pregnancies": 6, "Glucose": 148, "BloodPressure": 72, "SkinThickness": 35, "Insulin": 0,
        "BMI": 33.6, "DiabetesPedigreeFunction": 0.627, "Age": 50}
HEART = {"age": 63, "sex": 1, "cp": 3, "trestbps": 145, "chol": 233, "fbs": 1, "restecg": 0,
         "thalach": 150, "exang": 0, "oldpeak": 2.3, "slope": 0, "ca": 0, "thal": 1}


def test_health(client):
    assert client.get(f"{P}/health").json()["status"] == "ok"


def test_models_listed(client):
    keys = {m["key"] for m in client.get(f"{P}/diagnosis/models").json()}
    assert keys == {"diabetes", "heart", "parkinsons"}


def test_predict_diabetes_and_history(client):
    h = {"X-Client-Id": "test-client"}
    r = client.post(f"{P}/diagnosis/diabetes/predict", json={"values": DIAB}, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["probability"] <= 1 and len(body["top_factors"]) == 5
    assert len(client.get(f"{P}/diagnosis/history", headers=h).json()) == 1


def test_predict_heart(client):
    r = client.post(f"{P}/diagnosis/heart/predict", json={"values": HEART})
    assert r.status_code == 200 and r.json()["risk_level"] in {"low", "moderate", "high"}


def test_predict_rejects_missing_and_absurd(client):
    assert client.post(f"{P}/diagnosis/heart/predict", json={"values": {"age": 50}}).status_code == 422
    bad = dict(HEART, age=900)
    assert client.post(f"{P}/diagnosis/heart/predict", json={"values": bad}).status_code == 422
    assert client.post(f"{P}/diagnosis/nope/predict", json={"values": {}}).status_code == 404


def test_triage_emergency_and_routine(client):
    e = client.post(f"{P}/emergency/triage", json={"text": "my father has chest pain and sweating"}).json()
    assert e["level"] == "emergency" and e["call"]["number"] == "108"
    s = client.post(f"{P}/emergency/triage", json={"text": "I have a mild cold"}).json()
    assert s["level"] == "routine"


def test_chat_safety_and_fallback(client):
    r = client.post(f"{P}/assistant/chat", json={"message": "she cannot breathe and lips are blue"}).json()
    assert r["mode"] == "safety_triage"
    r = client.post(f"{P}/assistant/chat", json={"message": "what are the signs of a stroke?"}).json()
    assert r["mode"] == "rule_based" and "FAST" in r["reply"]          # education, not an alarm
    r = client.post(f"{P}/assistant/chat", json={"message": "my father has face drooping and slurred speech"}).json()
    assert r["mode"] == "safety_triage"
    r = client.post(f"{P}/assistant/chat", json={"message": "who can donate blood?"}).json()
    assert r["mode"] == "rule_based" and "donat" in r["reply"].lower()


def test_tools(client):
    assert client.post(f"{P}/tools/bmi", json={"weight_kg": 70, "height_cm": 175}).json()["category"] == "Normal weight"
    assert client.post(f"{P}/tools/blood-pressure", json={"systolic": 150, "diastolic": 95}).json()["level"] == "high"
    rep = client.post(f"{P}/tools/report", json={"text": "Fasting Glucose: 132 mg/dL\nHbA1c 5.4 %\nHaemoglobin 10.9 g/dL", "sex": "female"}).json()
    by = {r["test"]: r["status"] for r in rep["results"]}
    assert by["Fasting glucose"] == "high" and by["HbA1c"] == "normal" and by["Haemoglobin"] == "low"


def test_blood_flow(client):
    donor = {"name": "Asha Roy", "phone": "9876543210", "blood_group": "O-", "city": "Siliguri",
             "lat": 26.72, "lon": 88.43, "consent": True}
    assert client.post(f"{P}/blood/donors", json=donor).status_code == 201
    recent = dict(donor, name="Too Soon", phone="9876500000", blood_group="O+",
                  last_donated="2999-01-01T00:00:00Z")  # future date -> not eligible
    client.post(f"{P}/blood/donors", json=recent)
    assert client.post(f"{P}/blood/donors", json=dict(donor, consent=False, phone="9000000001")).status_code == 422

    req = {"patient_name": "Ravi", "blood_group": "A+", "units": 2, "hospital": "City Hospital", "city": "Siliguri",
           "lat": 26.71, "lon": 88.42, "urgency": "critical", "contact_phone": "9123456789"}
    out = client.post(f"{P}/blood/requests", json=req).json()
    names = [m["name"] for m in out["matches"]]
    assert "Asha Roy" in names and "Too Soon" not in names   # O- can give to A+, rest-period enforced
    rid = out["request"]["id"]
    assert client.patch(f"{P}/blood/requests/{rid}/status?contact_phone=1111111111", json={"status": "fulfilled"}).status_code == 403
    assert client.patch(f"{P}/blood/requests/{rid}/status?contact_phone=9123456789", json={"status": "fulfilled"}).status_code == 200
    assert client.get(f"{P}/blood/stats").json()["total_donors"] >= 2


def test_ambulance_flow(client):
    a = {"operator": "Seva Ambulance", "phone": "9000011111", "vehicle_type": "ALS", "city": "Siliguri", "lat": 26.72, "lon": 88.43}
    aid = client.post(f"{P}/emergency/ambulances", json=a).json()["id"]
    assert client.get(f"{P}/emergency/ambulances").json() == []          # unverified -> hidden
    assert client.post(f"{P}/emergency/admin/ambulances/{aid}/verify").status_code == 403
    assert client.post(f"{P}/emergency/admin/ambulances/{aid}/verify", headers={"X-Admin-Key": "test-admin"}).status_code == 200
    req = {"patient_name": "Mina", "phone": "9333333333", "emergency_type": "Accident", "severity": "critical",
           "lat": 26.71, "lon": 88.42}
    out = client.post(f"{P}/emergency/ambulance-requests", json=req).json()
    assert out["suggested_ambulances"][0]["id"] == aid and "108" in out["warning"]
    rid = out["id"]
    assert client.patch(f"{P}/emergency/ambulance-requests/{rid}/status", json={"status": "dispatched", "ambulance_id": aid}).status_code == 403
    assert client.patch(f"{P}/emergency/ambulance-requests/{rid}/status", json={"status": "dispatched", "ambulance_id": aid},
                        headers={"X-Admin-Key": "test-admin"}).status_code == 200
    got = client.get(f"{P}/emergency/ambulance-requests/{rid}?phone=9333333333").json()
    assert got["status"] == "dispatched" and got["ambulance"]["id"] == aid
