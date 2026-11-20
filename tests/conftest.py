import os
os.environ["DATABASE_URL"] = "sqlite:///./test_waloma.db"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-tests"
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import User, UserRole, AccountStatus
from app.core.security import hash_password

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture()
def client(db):
    def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture()
def admin(db):
    user = User(member_id="WAL-ADMIN-000001", full_name="Test Admin", email="admin@test.com", phone="1234567", password_hash=hash_password("StrongPassword123!"), role=UserRole.ADMIN, status=AccountStatus.APPROVED)
    db.add(user); db.commit(); db.refresh(user)
    return user
