from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from database import save_user_token, init_db
import os
import urllib.parse

app = FastAPI()

@app.on_event("startup")
async def startup():
    init_db()

@app.get("/")
def home():
    return {"status": "The Wired is online"}

@app.get("/login")
async def login(user_id: str):
    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI")
    
    if not client_id or not redirect_uri:
        return {"error": "Faltan variables de entorno (CLIENT_ID o REDIRECT_URI)"}

    # Permisos para ver qué escucha y su top (ideal para los Widgets V2)
    scope = "user-read-currently-playing user-top-read"
    
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": user_id  
    }
    
    spotify_url = f"https://accounts.spotify.com/authorize?{urllib.parse.urlencode(params)}"
    
    return RedirectResponse(spotify_url)

@app.get("/callback")
async def callback(code: str, state: str):
    # 'state' contiene el discord_id que enviamos en /login
    try:
        save_user_token(int(state), code)
        return {"message": "Sincronización exitosa con la Wired. Ya puedes cerrar esta pestaña."}
    except Exception as e:
        return {"error": f"Error al guardar en base de datos: {str(e)}"}
