import os
import sys
import tempfile

# In-memory SQLite для тестов (чистая БД на каждый запуск процесса).
# Должно быть установлено ДО импорта config/db.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["APP_ENV"] = "dev"
os.environ["DEV_LOGIN_ENABLED"] = "true"
os.environ["ADMIN_VK_IDS"] = "400977,795384"
os.environ["SECRET_KEY"] = "test-secret-not-for-prod"
os.environ["VK_APP_SECRET"] = "test-secret"
os.environ["VK_SERVICE_TOKEN"] = ""
os.environ["VK_GROUP_ID"] = ""
os.environ["MEMBER_GATE_ENABLED"] = "false"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from db import get_db
from deps import get_current_user
from models import Base, Setting, User

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    seed = TestingSessionLocal()
    seed.add(Setting(key="game_open", value="1"))
    seed.commit()
    seed.close()
    yield
    Base.metadata.drop_all(bind=engine)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _deny_user():
    """Для клиента без авторизации — имитируем 401 через зависимость."""
    from fastapi import HTTPException, status
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Не авторизован")


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _make_user_override(vk_id: int, role: str):
    """Фабрика override'ов get_current_user под конкретную роль.

    Generator-форма: сессия держится открытой до конца запроса, чтобы
    возвращённый user оставался bound.
    """
    def _override():
        db = TestingSessionLocal()
        try:
            user = db.query(User).filter(User.vk_id == vk_id).first()
            if user is None:
                user = User(vk_id=vk_id, role=role)
                db.add(user)
                db.commit()
                db.refresh(user)
            yield user
        finally:
            db.close()
    return _override


def _setup_app(app):
    """Общие настройки app для всех фикстур-клиентов."""
    app.dependency_overrides[get_db] = _override_get_db
    # Middleware должен писать логи в тестовую БД.
    app.state.session_factory = TestingSessionLocal


@pytest.fixture
def client():
    """Клиент без авторизации — для тестов health/public и 401."""
    from main import app
    _setup_app(app)
    app.dependency_overrides[get_current_user] = _deny_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_client():
    """Клиент, авторизованный как admin (vk_id=400977)."""
    from main import app
    _setup_app(app)
    app.dependency_overrides[get_current_user] = _make_user_override(400977, "admin")
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def player_client():
    """Клиент, авторизованный как player (vk_id=123)."""
    from main import app
    _setup_app(app)
    app.dependency_overrides[get_current_user] = _make_user_override(123, "player")
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def raw_client():
    """Клиент без override get_current_user — авторизация реальным
    Bearer-токеном (для тестов гейтов внутри зависимости)."""
    from main import app
    _setup_app(app)
    app.dependency_overrides.pop(get_current_user, None)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def uploads_tmp(monkeypatch):
    import config
    tmp = tempfile.mkdtemp(prefix="holidays_test_uploads_")
    monkeypatch.setattr(config, "UPLOADS_DIR", tmp)
    yield tmp
    for name in os.listdir(tmp):
        os.remove(os.path.join(tmp, name))
    os.rmdir(tmp)


def make_user_client(vk_id: int, role: str = "player"):
    """Создаёт TestClient от имени произвольного игрока.

    Менеджер контекста: восстанавливает предыдущий override get_current_user на выходе.
    """
    from contextlib import contextmanager
    from main import app
    from fastapi.testclient import TestClient

    @contextmanager
    def _ctx():
        _setup_app(app)
        prev = app.dependency_overrides.get(get_current_user)
        app.dependency_overrides[get_current_user] = _make_user_override(vk_id, role)
        with TestClient(app) as c:
            yield c
        if prev is not None:
            app.dependency_overrides[get_current_user] = prev
        else:
            app.dependency_overrides.pop(get_current_user, None)

    return _ctx()
