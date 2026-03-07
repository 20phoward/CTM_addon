import sys
from unittest.mock import MagicMock

if "whisper" not in sys.modules:
    sys.modules["whisper"] = MagicMock()

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db, User, Team
from auth import hash_password
from main import app

TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def team(db):
    t = Team(name="Test Team")
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@pytest.fixture
def admin_user(db):
    user = User(
        email="admin@test.com",
        hashed_password=hash_password("Admin123"),
        name="Admin User",
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user):
    from auth import create_access_token
    return create_access_token(admin_user.id)


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def supervisor_user(db, team):
    user = User(
        email="supervisor@test.com",
        hashed_password=hash_password("Super123"),
        name="Supervisor User",
        role="supervisor",
        team_id=team.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def supervisor_token(supervisor_user):
    from auth import create_access_token
    return create_access_token(supervisor_user.id)


@pytest.fixture
def supervisor_headers(supervisor_token):
    return {"Authorization": f"Bearer {supervisor_token}"}


@pytest.fixture
def rep_user(db, team):
    user = User(
        email="rep@test.com",
        hashed_password=hash_password("Rep12345"),
        name="Rep User",
        role="rep",
        team_id=team.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def rep_token(rep_user):
    from auth import create_access_token
    return create_access_token(rep_user.id)


@pytest.fixture
def rep_headers(rep_token):
    return {"Authorization": f"Bearer {rep_token}"}
