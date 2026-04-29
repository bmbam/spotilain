import os
import discord
import spotipy
import requests
import datetime
from io import BytesIO
from PIL import Image, ImageEnhance
from discord.ext import tasks, commands
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from database import get_db_connection # Importamos tu lógica de DB

load_dotenv()

# --- CONFIGURACIÓN DE LA RED ---
intents = discord.Intents.all()
TU_ID = 000000000000000000 # Pon tu ID aquí

bot = commands.Bot(command_prefix="{", intents=intents, owner_id=TU_ID)

# --- HELPER: Obtener cliente de Spotify por usuario ---
def get_user_sp(discord_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT spotify_token FROM usuarios WHERE discord_id = %s", (discord_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()

    if result:
        # Reconstruimos el cliente con el token guardado
        return spotipy.Spotify(auth=result[0])
    return None

# --- EVENTOS ---
@bot.event
async def on_ready():
    print(f"\n[SISTEMA LAIN ACTIVO]")
    print(f"Nodo central: {bot.user}")
    print("And everyone is always connected...\n")

# --- COMANDOS DE ADMINISTRACIÓN ---

@bot.command(name="login")
async def login(ctx):
    """Genera el link de sincronización con la Wired"""
    link = f"{os.getenv('RAILWAY_URL')}/login?user_id={ctx.author.id}"
    embed = discord.Embed(
        title="📥 Sincronización con The Wired",
        description=f"Haz clic [aquí]({link}) para autorizar a **Lain** a acceder a tu flujo de datos.",
        color=0x9b59b6
    )
    embed.set_footer(text="No matter where you are, everyone is always connected.")
    await ctx.author.send(embed=embed)
    await ctx.send(f"🛰️ {ctx.author.mention}, te he enviado el protocolo de acceso por privado.")

# --- COMANDO TOP (MULTI-USUARIO) ---

@bot.command(name="top")
async def top(ctx, tipo="artistas"):
    """Grilla visual 5x2 personalizada"""
    sp_user = get_user_sp(ctx.author.id)
    if not sp_user:
        return await ctx.send("❌ No estás conectado a la Wired. Usa `{login` primero.")

    async with ctx.typing():
        try:
            r_type = tipo.lower()
            if r_type in ["tracks", "canciones"]:
                res = sp_user.current_user_top_tracks(limit=10, time_range='short_term')
                titulo, items = "📊 FRECUENCIAS: TRACKS", res['items']
                image_urls = [item['album']['images'][0]['url'] for item in items]
            else:
                res = sp_user.current_user_top_artists(limit=10, time_range='short_term')
                titulo, items = "👤 ENTIDADES: ARTISTAS", res['items']
                image_urls = [item['images'][0]['url'] for item in items]

            # --- PROCESAMIENTO VISUAL LAIN ---
            cols, rows, size, pad = 5, 2, 200, 15
            canvas = Image.new('RGB', (cols*size + (cols+1)*pad, rows*size + (rows+1)*pad), (15, 15, 15))
            
            for i, url in enumerate(image_urls):
                img_data = requests.get(url).content
                img = Image.open(BytesIO(img_data)).convert('L').resize((size, size)) # Blanco y negro
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
            await ctx.send(f"⚠️ Error en la transferencia de datos: {e}")

bot.run(os.getenv('DISCORD_TOKEN'))
