from app.database import get_db

def test_get_db_returns_db():
    db = get_db()
    assert db is not None
    assert hasattr(db, "name")