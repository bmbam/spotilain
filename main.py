from fastapi.responses import RedirectResponse
import urllib.parse

@app.get("/login")
async def login(user_id: str):
    # Definimos los permisos que pediremos a Spotify
    scope = "user-read-currently-playing user-top-read"
    
    # Construimos la URL de autorización de Spotify
    # Usamos 'state' para pasar el ID de Discord y recuperarlo en el callback
    params = {
        "client_id": os.getenv("SPOTIPY_CLIENT_ID"),
        "response_type": "code",
        "redirect_uri": os.getenv("SPOTIPY_REDIRECT_URI"),
        "scope": scope,
        "state": user_id  # <--- Aquí viaja el ID de Discord
    }
    
    spotify_url = f"https://accounts.spotify.com/authorize?{urllib.parse.urlencode(params)}"
    
    return RedirectResponse(spotify_url)
