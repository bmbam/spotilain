import os
import discord
import spotipy
import requests
import asyncio
from io import BytesIO
from PIL import Image, ImageEnhance
from discord.ext import tasks, commands
from dotenv import load_dotenv
from database import get_db_connection, init_db

load_dotenv()

# --- CONFIGURACIÓN DE LA RED ---
intents = discord.Intents.all()
# Reemplaza con tu ID de Discord real
TU_ID = 919008060339527700
# ID del canal donde se enviarán las canciones automáticamente
CANAL_WIRED_ID = 1411590530546012203 

bot = commands.Bot(command_prefix="{", intents=intents, owner_id=TU_ID)

# Diccionario global para evitar spam de la misma canción
last_played = {}

# --- HELPERS ---

def get_user_sp(discord_id):
    """Obtiene el cliente de Spotify usando el token de la DB"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT spotify_token FROM usuarios WHERE discord_id = %s", (discord_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()

        if result:
            return spotipy.Spotify(auth=result[0])
    except Exception as e:
        print(f"Error al conectar con la DB: {e}")
    return None

# --- TAREAS AUTOMÁTICAS (THE WIRED MONITOR) ---

@tasks.loop(seconds=15)
async def check_spotify_activity():
    """Revisa qué están escuchando los usuarios y lo publica"""
    channel = bot.get_channel(CANAL_WIRED_ID)
    if not channel:
        return

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT discord_id FROM usuarios")
        users = cur.fetchall()
        cur.close()
        conn.close()
    except:
        return

    for (user_id,) in users:
        sp_user = get_user_sp(user_id)
        if not sp_user:
            continue

        try:
            current = sp_user.current_playback()
            
            if current and current['is_playing'] and current['item']:
                track_id = current['item']['id']
                
                # Solo envía si la canción es nueva para este usuario
                if last_played.get(user_id) != track_id:
                    song_name = current['item']['name']
                    artist_name = current['item']['artists'][0]['name']
                    cover_url = current['item']['album']['images'][0]['url']
                    
                    # Intentamos buscar el nombre del usuario en el cache del bot
                    user_obj = bot.get_user(user_id)
                    name = user_obj.name if user_obj else f"Usuario {user_id}"

                    embed = discord.Embed(
                        title="🎶 Transmisión en Vivo: The Wired",
                        description=f"**{name}** está escuchando:\n**{song_name}**\n*por {artist_name}*",
                        color=0x1DB954
                    )
                    embed.set_thumbnail(url=cover_url)
                    embed.set_footer(text="Everyone is always connected...")
                    
                    await channel.send(embed=embed)
                    last_played[user_id] = track_id
            
            elif not current or not current['is_playing']:
                last_played[user_id] = None

        except Exception as e:
            print(f"Error en flujo de {user_id}: {e}")

@check_spotify_activity.before_loop
async def before_check():
    await bot.wait_until_ready()

# --- EVENTOS ---

@bot.event
async def on_ready():
    print(f"\n[SISTEMA LAIN ACTIVO]")
    print(f"Nodo central: {bot.user}")
    print(f"Monitoreando canal: {CANAL_WIRED_ID}")
    if not check_spotify_activity.is_running():
        check_spotify_activity.start()

# --- COMANDOS ---

@bot.command(name="login")
async def login(ctx):
    """Genera el link de sincronización personal"""
    # Usamos la URL de Railway que configuramos antes
    link = f"{os.getenv('RAILWAY_URL')}/login?user_id={ctx.author.id}"
    
    embed = discord.Embed(
        title="📥 Sincronización con The Wired",
        description=f"Haz clic [aquí]({link}) para autorizar tu flujo de datos.",
        color=0x9b59b6
    )
    embed.set_footer(text="Present Day, Present Time... HAHAHAHA")
    
    try:
        await ctx.author.send(embed=embed)
        await ctx.send(f"🛰️ {ctx.author.mention}, protocolo enviado por privado.")
    except discord.Forbidden:
        await ctx.send(f"❌ {ctx.author.mention}, no puedo enviarte DMs. Abre tus mensajes privados.")

@bot.command(name="top")
async def top(ctx, tipo="artistas"):
    """Grilla visual 5x2 de lo más escuchado"""
    sp_user = get_user_sp(ctx.author.id)
    if not sp_user:
        return await ctx.send("❌ No estás conectado a la Wired. Usa `{login`.")

    async with ctx.typing():
        try:
            if tipo.lower() in ["tracks", "canciones"]:
                res = sp_user.current_user_top_tracks(limit=10, time_range='short_term')
                titulo = "📊 FRECUENCIAS: TRACKS"
                items = res['items']
                image_urls = [item['album']['images'][0]['url'] for item in items]
            else:
                res = sp_user.current_user_top_artists(limit=10, time_range='short_term')
                titulo = "👤 ENTIDADES: ARTISTAS"
                items = res['items']
                image_urls = [item['images'][0]['url'] for item in items]

            # Procesamiento de imagen (Estética Lain)
            cols, rows, size, pad = 5, 2, 200, 15
            canvas = Image.new('RGB', (cols*size + (cols+1)*pad, rows*size + (rows+1)*pad), (15, 15, 15))
            
            for i, url in enumerate(image_urls):
                img_data = requests.get(url).content
                img = Image.open(BytesIO(img_data)).convert('L').resize((size, size))
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.4).convert('RGB')
                canvas.paste(img, ((i%cols)*size + (i%cols+1)*pad, (i//cols)*size + (i//cols+1)*pad))

            with BytesIO() as img_bin:
                canvas.save(img_bin, 'PNG')
                img_bin.seek(0)
                file = discord.File(fp=img_bin, filename='top.png')
                embed = discord.Embed(title=titulo, color=0x2b2b2b)
                embed.set_image(url="attachment://top.png")
                await ctx.send(file=file, embed=embed)
        except Exception as e:
            await ctx.send(f"⚠️ Error en la transferencia: {e}")

bot.run(os.getenv('DISCORD_TOKEN'))
