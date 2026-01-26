"""
Pytest configuration and shared fixtures.
"""
import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Set test environment variables before importing app
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"  # Use different DB for tests

# Import after setting env vars
from app.models.base import Base
from app.main import app
from app.config import settings


@pytest.fixture(scope="function")
def test_db():
    """Create a test database in memory."""
    from app.models.base import get_db
    
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    db = TestingSessionLocal()
    yield db
    db.close()

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def sample_pgn():
    """Sample PGN for testing."""
    return """[Event "Test Game"]
[Site "Test"]
[Date "2024.01.01"]
[Round "1"]
[White "Test Player"]
[Black "Test Opponent"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 8. c3 O-O 9. h3 Nb8 10. d4 Nbd7 11. c4 c6 12. cxb5 axb5 13. Nc3 b4 14. Nb1 a5 15. Bc2 c5 16. d5 c4 17. Nbd2 Nc5 18. b3 cxb3 19. axb3 Nce4 20. Nxe4 Nxe4 21. Bd3 Nf6 22. Bb2 Bd7 23. Qd2 Qc7 24. Rc1 Rfc8 25. Qe3 h6 26. Rc4 Ra6 27. Rec1 Rca8 28. Qg3 Kh7 29. Qh4 Kg8 30. Qg3 Kh7 31. Qh4 Kg8 32. Qg3 1-0"""


@pytest.fixture
def sample_pgn_minimal():
    """Minimal PGN for quick tests."""
    return """1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 8. c3 O-O 1-0"""


@pytest.fixture
def invalid_pgn():
    """Invalid PGN for error testing."""
    return "This is not a valid PGN"


@pytest.fixture
def mock_redis(monkeypatch):
    """Mock Redis for testing."""
    from unittest.mock import MagicMock

    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = True
    mock_redis.ping.return_value = True

    monkeypatch.setattr("app.utils.cache.redis_client", mock_redis)
    return mock_redis
