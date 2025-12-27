import db


def test_only_one_appointment_per_time_slot(temp_db):
    a1 = {
        "user_id": 1,
        "name": "User1",
        "phone": "111",
        "address": "A",
        "date": "2025-12-30",
        "hour": 11,
        "type": "Медленный интернет",
    }

    a2 = {
        "user_id": 2,
        "name": "User2",
        "phone": "222",
        "address": "B",
        "date": "2025-12-30",
        "hour": 11,
        "type": "Wi-Fi не отображается",
    }

    assert db.create_appointment(a1) is True
    assert db.create_appointment(a2) is False
