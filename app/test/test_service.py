import pytest
from unittest.mock import MagicMock, patch
from app.service import UserService
import app.proto.user_pb2 as user_pb2
import grpc

class DummyContext:
    def __init__(self):
        self.code = None
        self.details = None
    def set_code(self, code):
        self.code = code
    def set_details(self, details):
        self.details = details

@pytest.fixture
def user_service():
    with patch("app.service.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db
        yield UserService()

def test_create_user(user_service):
    user_service.collection.insert_one.return_value.inserted_id = "123"
    req = user_pb2.CreateUserRequest(username="user", email="mail@test.com", password="pw")
    response = user_service.CreateUser(req, DummyContext())
    assert response.username == "user"
    assert response.email == "mail@test.com"
    assert response.id == "123"

def test_get_user_found(user_service):
    user_service.collection.find_one.return_value = {"_id": "123", "username": "u", "email": "e"}
    req = user_pb2.GetUserRequest(id="123")
    resp = user_service.GetUser(req, DummyContext())
    # Si el servicio no rellena los campos, verifica por qué. Puedes agregar un print(resp) para debug.
    assert resp.username == "u"
    assert resp.email == "e"
    assert resp.id == "123"

def test_get_user_not_found(user_service):
    user_service.collection.find_one.return_value = None
    req = user_pb2.GetUserRequest(id="notfound")
    ctx = DummyContext()
    resp = user_service.GetUser(req, ctx)
    assert ctx.code == grpc.StatusCode.NOT_FOUND

def test_update_user_found(user_service):
    user_service.collection.update_one.return_value.matched_count = 1
    user_service.collection.find_one.return_value = {"_id": "X", "username": "nuevo", "email": "nuevo@x.com"}
    req = user_pb2.UpdateUserRequest(
        id="X", username="nuevo", email="nuevo@x.com", password="pw"
    )
    resp = user_service.UpdateUser(req, DummyContext())
    assert resp.username == "nuevo"
    assert resp.email == "nuevo@x.com"
    assert resp.id == "X"

def test_update_user_not_found(user_service):
    # Usa un id válido de ObjectId (24 chars hex) para que pase la validación:
    user_service.collection.update_one.return_value.matched_count = 0
    req = user_pb2.UpdateUserRequest(
        id="507f1f77bcf86cd799439011", username="n", email="n", password="pw"
    )
    ctx = DummyContext()
    resp = user_service.UpdateUser(req, ctx)
    assert ctx.code == grpc.StatusCode.NOT_FOUND

def test_update_user_invalid_id(user_service):
    # Esto sí debe dar INVALID_ARGUMENT:
    req = user_pb2.UpdateUserRequest(id="X", username="n", email="n", password="pw")
    ctx = DummyContext()
    resp = user_service.UpdateUser(req, ctx)
    assert ctx.code == grpc.StatusCode.INVALID_ARGUMENT

def test_delete_user(user_service):
    user_service.collection.delete_one.return_value.deleted_count = 1
    req = user_pb2.DeleteUserRequest(id="X")
    resp = user_service.DeleteUser(req, DummyContext())
    assert isinstance(resp, user_pb2.Empty)

def test_register_already_exists(user_service):
    user_service.collection.find_one.return_value = {"email": "exist@test.com"}
    req = user_pb2.RegisterRequest(username="a", email="exist@test.com", password="pw")
    ctx = DummyContext()
    resp = user_service.Register(req, ctx)
    assert ctx.code == grpc.StatusCode.ALREADY_EXISTS

def test_login_success(user_service):
    with patch("app.service.verify_password", return_value=True), \
         patch("app.service.create_access_token", return_value="token"):
        user_service.collection.find_one.return_value = {"email": "e", "password": "hashed"}
        req = user_pb2.LoginRequest(email="e", password="pw")
        ctx = DummyContext()
        resp = user_service.Login(req, ctx)
        assert resp.access_token == "token"
        assert resp.token_type == "bearer"

def test_login_fail(user_service):
    with patch("app.service.verify_password", return_value=False):
        user_service.collection.find_one.return_value = {"email": "e", "password": "hashed"}
        req = user_pb2.LoginRequest(email="e", password="pw")
        ctx = DummyContext()
        resp = user_service.Login(req, ctx)
        assert ctx.code == grpc.StatusCode.UNAUTHENTICATED