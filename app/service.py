import grpc
from concurrent import futures
from bson import ObjectId, errors as bson_errors
from app.database import get_db
from app.auth import get_password_hash, verify_password, create_access_token
import app.proto.user_pb2 as user_pb2
import app.proto.user_pb2_grpc as user_pb2_grpc

class UserService(user_pb2_grpc.UserServiceServicer):
    def __init__(self):
        self.db = get_db()
        self.collection = self.db["users"]

    def CreateUser(self, request, context):
        # ¡CORREGIDO! Hashea la contraseña al crear usuario
        hashed_pw = get_password_hash(request.password)
        user = {
            "username": request.username,
            "email": request.email,
            "password": hashed_pw
        }
        result = self.collection.insert_one(user)
        return user_pb2.UserResponse(
            id=str(result.inserted_id),
            username=user["username"],
            email=user["email"]
        )

    def GetUser(self, request, context):
        try:
            user = self.collection.find_one({"_id": ObjectId(request.id)})
        except bson_errors.InvalidId:
            user = None
        if user:
            return user_pb2.UserResponse(
                id=str(user["_id"]),
                username=user["username"],
                email=user["email"]
            )
        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details('User not found')
        return user_pb2.UserResponse()

    def UpdateUser(self, request, context):
        try:
            user_id = ObjectId(request.id)
        except bson_errors.InvalidId:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details('Invalid user id')
            return user_pb2.UserResponse()
        # ¡CORREGIDO! Hashea la contraseña al actualizar usuario
        hashed_pw = get_password_hash(request.password)
        result = self.collection.update_one(
            {"_id": user_id},
            {"$set": {
                "username": request.username,
                "email": request.email,
                "password": hashed_pw
            }}
        )
        if result.matched_count:
            user = self.collection.find_one({"_id": user_id})
            return user_pb2.UserResponse(
                id=str(user["_id"]),
                username=user["username"],
                email=user["email"]
            )
        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details('User not found')
        return user_pb2.UserResponse()

    def DeleteUser(self, request, context):
        try:
            user_id = ObjectId(request.id)
        except bson_errors.InvalidId:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details('Invalid user id')
            return user_pb2.Empty()
        result = self.collection.delete_one({"_id": user_id})
        if result.deleted_count == 0:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details('User not found')
        return user_pb2.Empty()

    def ListUsers(self, request, context):
        users = self.collection.find()
        user_list = []
        for user in users:
            user_list.append(user_pb2.UserResponse(
                id=str(user["_id"]),
                username=user["username"],
                email=user["email"]
            ))
        return user_pb2.UserListResponse(users=user_list)

    # ---------- NUEVOS MÉTODOS gRPC ----------
    def Register(self, request, context):
        if self.collection.find_one({"email": request.email}):
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details("Email ya registrado")
            return user_pb2.RegisterResponse()
        hashed_pw = get_password_hash(request.password)
        user = {
            "username": request.username,
            "email": request.email,
            "password": hashed_pw
        }
        result = self.collection.insert_one(user)
        return user_pb2.RegisterResponse(id=str(result.inserted_id))

    def Login(self, request, context):
        user = self.collection.find_one({"email": request.email})
        # Agrega debug temporal
        print("user:", user)
        print("request.password:", request.password)
        if user:
            print("user['password']:", user["password"])
            print("verify_password result:", verify_password(request.password, user["password"]))
        if not user or not verify_password(request.password, user["password"]):
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            context.set_details("Credenciales incorrectas")
            return user_pb2.LoginResponse(access_token="", token_type="")
        token = create_access_token({"sub": user["email"]})
        return user_pb2.LoginResponse(access_token=token, token_type="bearer")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    user_pb2_grpc.add_UserServiceServicer_to_server(UserService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("gRPC UserService running on port 50051")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()