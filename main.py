from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from database import save_user_token, init_db
import os
import urllib.parse
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json

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
        return {"error": "Faltan variables de entorno en Railway"}

    scope = "user-read-currently-playing user-read-playback-state user-top-read"
    
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
    try:
        # 1. Configuramos el manejador para intercambiar el código por el TOKEN REAL
        sp_oauth = SpotifyOAuth(
            client_id=os.getenv("SPOTIPY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
            redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI")
        )
        
        # 2. Obtenemos el diccionario completo del token (access, refresh, expires_at)
        token_info = sp_oauth.get_access_token(code)
        
        # 3. Guardamos el JSON completo como texto en la base de datos
        # Esto permite que el bot use json.loads() y refresque el token solo
        save_user_token(int(state), json.dumps(token_info))
        
        return {
            "message": "Sincronización exitosa con la Wired.",
            "detalle": "El flujo de datos ha sido vinculado a tu ID de Discord."
        }
    except Exception as e:
        return {"error": f"Error en la conexión con la Wired: {str(e)}"}
