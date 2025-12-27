import db


def test_save_and_load_user_state(temp_db):
    db.save_user_state(1, "NAME", {"step": 1})

    state, data = db.load_user_state(1)

    assert state == "NAME"
    assert data["step"] == 1


def test_clear_user_state(temp_db):
    db.save_user_state(2, "DATE", {"x": 123})
    db.save_user_state(2, None, {})

    state, data = db.load_user_state(2)

    assert state is None
    assert data == {}
