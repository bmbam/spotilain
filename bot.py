import os
import discord
import spotipy
import requests
import json
from io import BytesIO
from PIL import Image, ImageEnhance
from discord.ext import tasks, commands
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from database import get_db_connection

load_dotenv()

# --- CONFIGURACIÓN ---
intents = discord.Intents.all()
# Configura estos IDs según tu servidor
TU_ID = 919008060339527700  # Tu ID de Discord
CANAL_WIRED_ID = 964595061335670815 # ID del canal de monitoreo

bot = commands.Bot(command_prefix="{", intents=intents, owner_id=TU_ID)
last_played = {}

# --- MANEJADOR DE AUTENTICACIÓN (Refresco Automático) ---
def get_user_sp(discord_id):
    """Obtiene cliente Spotify con auto-refresco de token"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT spotify_token FROM usuarios WHERE discord_id = %s", (discord_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()

        if result:
            # El token se guarda como un string JSON en la DB
            token_info = json.loads(result[0])
            
            auth_manager = SpotifyOAuth(
                client_id=os.getenv("SPOTIPY_CLIENT_ID"),
                client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
                redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
                scope="user-read-currently-playing user-top-read"
            )

            # Refrescar si es necesario
            if auth_manager.is_token_expired(token_info):
                token_info = auth_manager.refresh_access_token(token_info['refresh_token'])
                # Guardar el nuevo token actualizado en la DB
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("UPDATE usuarios SET spotify_token = %s WHERE discord_id = %s", 
                            (json.dumps(token_info), discord_id))
                conn.commit()
                cur.close()
                conn.close()

            return spotipy.Spotify(auth=token_info['access_token'])
    except Exception as e:
        print(f"Error en la sincronización de la Wired para {discord_id}: {e}")
    return None

# --- TAREAS AUTOMÁTICAS ---
@tasks.loop(seconds=15)
async def check_spotify_activity():
    """Monitorea el flujo de datos de los usuarios"""
    channel = bot.get_channel(CANAL_WIRED_ID)
    if not channel: return

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT discord_id FROM usuarios")
        users = cur.fetchall()
        cur.close()
        conn.close()
    except: return

    for (user_id,) in users:
        sp_user = get_user_sp(user_id)
        if not sp_user: continue

        try:
            current = sp_user.current_playback()
            if current and current['is_playing'] and current['item']:
                track_id = current['item']['id']
                
                if last_played.get(user_id) != track_id:
                    song_name = current['item']['name']
                    artist_name = current['item']['artists'][0]['name']
                    cover_url = current['item']['album']['images'][0]['url']
                    
                    user_obj = bot.get_user(user_id)
                    name = user_obj.name if user_obj else f"Usuario {user_id}"

                    embed = discord.Embed(
                        title="🎶 Transmisión en Vivo: The Wired",
                        description=f"**{name}** está escuchando:\n**{song_name}**\n*por {artist_name}*",
                        color=0x1DB954
                    )
                    embed.set_thumbnail(url=cover_url)
                    embed.set_footer(text="And everyone is always connected...")
                    
                    await channel.send(embed=embed)
                    last_played[user_id] = track_id
            elif not current or not current['is_playing']:
                last_played[user_id] = None
        except Exception as e:
            print(f"Error de flujo (401 evitado): {e}")

@check_spotify_activity.before_loop
async def before_check():
    await bot.wait_until_ready()

# --- EVENTOS ---
@bot.event
async def on_ready():
    print(f"\n[SISTEMA LAIN ACTIVO]")
    print(f"Nodo central: {bot.user}")
    if not check_spotify_activity.is_running():
        check_spotify_activity.start()

# --- COMANDOS ---
@bot.command(name="login")
async def login(ctx):
    """Protocolo de inicio de sesión"""
    link = f"{os.getenv('RAILWAY_URL')}/login?user_id={ctx.author.id}"
    embed = discord.Embed(
        title="📥 Sincronización con The Wired",
        description=f"Haz clic [aquí](https://{link}) para autorizar tu acceso.",
        color=0x9b59b6
    )
    try:
        await ctx.author.send(embed=embed)
        await ctx.send(f"🛰️ {ctx.author.mention}, protocolo enviado por privado.")
    except:
        await ctx.send("❌ Error: Abre tus mensajes privados.")

@bot.command(name="top")
async def top(ctx, tipo="artistas"):
    """Grilla visual 5x2 (CHEMICVL Aesthetic)"""
    sp_user = get_user_sp(ctx.author.id)
    if not sp_user: return await ctx.send("❌ No conectado.")

    async with ctx.typing():
        try:
            if tipo.lower() in ["tracks", "canciones"]:
                res = sp_user.current_user_top_tracks(limit=10, time_range='short_term')
                image_urls = [item['album']['images'][0]['url'] for item in res['items']]
                titulo = "📊 FRECUENCIAS: TRACKS"
            else:
                res = sp_user.current_user_top_artists(limit=10, time_range='short_term')
                image_urls = [item['images'][0]['url'] for item in res['items']]
                titulo = "👤 ENTIDADES: ARTISTAS"

            cols, rows, size, pad = 5, 2, 200, 15
            canvas = Image.new('RGB', (cols*size+(cols+1)*pad, rows*size+(rows+1)*pad), (15,15,15))
            
            for i, url in enumerate(image_urls):
                img = Image.open(BytesIO(requests.get(url).content)).convert('L').resize((size,size))
                img = ImageEnhance.Contrast(img).enhance(1.4).convert('RGB')
                canvas.paste(img, ((i%cols)*size+(i%cols+1)*pad, (i//cols)*size+(i//cols+1)*pad))

            with BytesIO() as img_bin:
                canvas.save(img_bin, 'PNG')
                img_bin.seek(0)
                await ctx.send(file=discord.File(img_bin, 'top.png'), 
                               embed=discord.Embed(title=titulo, color=0x2b2b2b).set_image(url="attachment://top.png"))
        except Exception as e:
            await ctx.send(f"⚠️ Error: {e}")

bot.run(os.getenv('DISCORD_TOKEN'))
