import grpc
from concurrent import futures
from bson import ObjectId, errors as bson_errors

from app.database import get_db
import app.proto.user_pb2 as user_pb2
import app.proto.user_pb2_grpc as user_pb2_grpc

class UserService(user_pb2_grpc.UserServiceServicer):
    def __init__(self):
        self.db = get_db()
        self.collection = self.db["users"]

    def CreateUser(self, request, context):
        user = {
            "username": request.username,
            "email": request.email,
            "password": request.password
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
        result = self.collection.update_one(
            {"_id": user_id},
            {"$set": {
                "username": request.username,
                "email": request.email,
                "password": request.password
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