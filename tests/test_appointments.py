import db


def test_create_appointment_success(temp_db):
    data = {
        "user_id": 1,
        "name": "Ivan Ivanov",
        "phone": "+79999999999",
        "address": "Moscow",
        "date": "2025-12-30",
        "hour": 10,
        "type": "Нет соединения",
    }

    assert db.create_appointment(data) is True
    assert db.has_active_appointment(1) is True


def test_only_one_active_appointment_per_user(temp_db):
    data = {
        "user_id": 1,
        "name": "Ivan Ivanov",
        "phone": "+79999999999",
        "address": "Moscow",
        "date": "2025-12-30",
        "hour": 10,
        "type": "Нет соединения",
    }

    assert db.create_appointment(data) is True
    assert db.create_appointment(data) is False


def test_cancel_appointment(temp_db):
    data = {
        "user_id": 3,
        "name": "Petr",
        "phone": "333",
        "address": "SPB",
        "date": "2025-12-31",
        "hour": 12,
        "type": "Нет соединения",
    }

    assert db.create_appointment(data) is True
    assert db.cancel_appointment(3) is True
    assert db.has_active_appointment(3) is False

def test_update_appointment_success(temp_db):
    data = {
        "user_id": 4,
        "name": "Alex",
        "phone": "444",
        "address": "Kazan",
        "date": "2025-12-29",
        "hour": 9,
        "type": "Нет соединения",
    }

    assert db.create_appointment(data) is True

    data["hour"] = 10
    assert db.update_appointment(4, data) is True
