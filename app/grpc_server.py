import grpc
from concurrent import futures
import time
import sys
import os
from pymongo import MongoClient
from bson import ObjectId

# Añade el path para los módulos generados por protoc
sys.path.append(os.path.join(os.path.dirname(__file__), 'proto'))
import user_pb2
import user_pb2_grpc

# Configuración de conexión a MongoDB
MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB = "userdb"         # Usando tu base de datos
MONGO_COLLECTION = "users"  # Usando tu colección

mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]
users_collection = db[MONGO_COLLECTION]

class UserServiceServicer(user_pb2_grpc.UserServiceServicer):
    def ListUsers(self, request, context):
        users = []
        users_cursor = users_collection.find()
        for user in users_cursor:
            users.append(
                user_pb2.UserResponse(
                    id=str(user.get("_id", "")),
                    username=user.get("username", ""),
                    email=user.get("email", "")
                )
            )
        return user_pb2.UserListResponse(users=users)

    def CreateUser(self, request, context):
        user_data = {
            "username": request.username,
            "email": request.email,
            "password": request.password  # Recuerda: nunca almacenes passwords en texto plano en producción.
        }
        result = users_collection.insert_one(user_data)
        return user_pb2.UserResponse(
            id=str(result.inserted_id),
            username=request.username,
            email=request.email
        )

    def GetUser(self, request, context):
        try:
            user = users_collection.find_one({"_id": ObjectId(request.id)})
        except Exception:
            user = None
        if user:
            return user_pb2.UserResponse(
                id=str(user.get("_id", "")),
                username=user.get("username", ""),
                email=user.get("email", "")
            )
        else:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details('User not found')
            return user_pb2.UserResponse()

    def UpdateUser(self, request, context):
        try:
            result = users_collection.update_one(
                {"_id": ObjectId(request.id)},
                {"$set": {"username": request.username, "email": request.email}}
            )
        except Exception:
            result = None
        if result and result.matched_count:
            return user_pb2.UserResponse(
                id=request.id,
                username=request.username,
                email=request.email
            )
        else:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details('User not found')
            return user_pb2.UserResponse()

    def DeleteUser(self, request, context):
        try:
            result = users_collection.delete_one({"_id": ObjectId(request.id)})
        except Exception:
            result = None
        return user_pb2.Empty()

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    user_pb2_grpc.add_UserServiceServicer_to_server(UserServiceServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("gRPC UserService running on port 50051")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()