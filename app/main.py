from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from pymongo import MongoClient
from bson import ObjectId
from app.auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user
)
from fastapi.security import OAuth2PasswordRequestForm

app = FastAPI()
client = MongoClient("mongodb://localhost:27017/")
db = client["userdb"]
users_collection = db["users"]

class User(BaseModel):
    username: str
    email: str
    password: str

def user_serializer(user) -> dict:
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "email": user["email"],
    }

def validate_object_id(user_id: str):
    try:
        return ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de usuario inválido")

@app.post("/register")
def register(user: User):
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email ya registrado")
    hashed_pw = get_password_hash(user.password)
    user_dict = user.dict()
    user_dict["password"] = hashed_pw
    result = users_collection.insert_one(user_dict)
    return {"id": str(result.inserted_id)}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_collection.find_one({"email": form_data.username})
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    token = create_access_token({"sub": user["email"]})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/users/me")
def get_me(current_user=Depends(get_current_user)):
    user = users_collection.find_one({"email": current_user["sub"]})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user_serializer(user)

@app.get("/users/{user_id}")
def get_user(user_id: str, current_user=Depends(get_current_user)):
    oid = validate_object_id(user_id)
    user = users_collection.find_one({"_id": oid})
    if user:
        return user_serializer(user)
    raise HTTPException(status_code=404, detail="Usuario no encontrado")

@app.put("/users/{user_id}")
def update_user(user_id: str, user: User, current_user=Depends(get_current_user)):
    oid = validate_object_id(user_id)
    hashed_pw = get_password_hash(user.password)
    user_dict = user.dict()
    user_dict["password"] = hashed_pw
    result = users_collection.update_one({"_id": oid}, {"$set": user_dict})
    if result.matched_count:
        return {"msg": "Usuario actualizado"}
    raise HTTPException(status_code=404, detail="Usuario no encontrado")

@app.delete("/users/{user_id}")
def delete_user(user_id: str, current_user=Depends(get_current_user)):
    oid = validate_object_id(user_id)
    result = users_collection.delete_one({"_id": oid})
    if result.deleted_count:
        return {"msg": "Usuario eliminado"}
    raise HTTPException(status_code=404, detail="Usuario no encontrado")