from fastapi import FastAPI, Request
from database import save_user_token, init_db
import os

app = FastAPI()

@app.on_event("startup")
async def startup():
    init_db()

@app.get("/")
def home():
    return {"status": "The Wired is online"}

@app.get("/callback")
async def callback(code: str, state: str):
    # 'state' debe ser el ID de Discord que enviamos en el link
    # Aquí procesarías el 'code' para obtener el token real de Spotify
    # Por ahora, guardamos el registro
    save_user_token(int(state), code)
    return {"message": "Conexión exitosa. Puedes cerrar esta pestaña."}
