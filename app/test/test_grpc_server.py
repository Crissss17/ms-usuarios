import pytest
from app.grpc_server import UserServiceServicer

def test_createuser_method_exists():
    service = UserServiceServicer()
    assert hasattr(service, "CreateUser")
    assert callable(getattr(service, "CreateUser", None))