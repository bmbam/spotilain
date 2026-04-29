import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Establece conexión con PostgreSQL usando la URL de Railway"""
    # Railway proporciona automáticamente la variable DATABASE_URL
    url = os.getenv('DATABASE_URL')
    return psycopg2.connect(url)

def init_db():
    """Inicializa la estructura de la Red (Crea las tablas si no existen)"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Tabla de usuarios sincronizados
    # Guardamos el discord_id, el token de acceso y el nombre de usuario de MAL opcional
    cur.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            discord_id BIGINT PRIMARY KEY,
            spotify_token TEXT,
            mal_user TEXT,
            fecha_conexion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    cur.close()
    conn.close()
    print("[SISTEMA] Estructura de la base de datos verificada.")

def save_user_token(discord_id, token):
    """Guarda o actualiza el token de un usuario (Protocolo de Sincronización)"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        INSERT INTO usuarios (discord_id, spotify_token) 
        VALUES (%s, %s) 
        ON CONFLICT (discord_id) 
        DO UPDATE SET spotify_token = EXCLUDED.spotify_token
    ''', (discord_id, token))
    
    conn.commit()
    cur.close()
    conn.close()

def get_user_token(discord_id):
    """Recupera el token de un usuario específico de los registros"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT spotify_token FROM usuarios WHERE discord_id = %s", (discord_id,))
    result = cur.fetchone()
    
    cur.close()
    conn.close()
    return result[0] if result else None
