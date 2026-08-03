import telebot
import imaplib
import email
import re
import json
import os

TOKEN = '8792363295:AAHJSbUDQLfr-e1s19XKA1wAGedFOgb70t8'
bot = telebot.TeleBot(TOKEN)

EMAIL_MADRE = 'cosasmuni9@gmail.com'
PASSWORD_MADRE = 'yspncrmxpdrtqgdc'
IMAP_SERVER = 'imap.gmail.com'

# --- TU ID DE ADMINISTRADOR ---
ADMIN_ID = 6323259714

# --- SISTEMA DE BASES DE DATOS (ACCESOS) ---
ARCHIVO_ACCESOS = 'accesos.json'

def cargar_accesos():
    if os.path.exists(ARCHIVO_ACCESOS):
        with open(ARCHIVO_ACCESOS, 'r') as f:
            return json.load(f)
    return {}

def guardar_accesos(datos):
    with open(ARCHIVO_ACCESOS, 'w') as f:
        json.dump(datos, f)

def tiene_acceso(user_id, correo):
    if user_id == ADMIN_ID:
        return True # El administrador siempre tiene acceso a todo
    accesos = cargar_accesos()
    user_str = str(user_id)
    if user_str in accesos:
        return correo in accesos[user_str]
    return False

# --- CONEXIÓN AL CORREO ---
conexion_mail = None

def conectar_correo():
    global conexion_mail
    print("Iniciando sesión en Gmail (una sola vez)...")
    conexion_mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    conexion_mail.login(EMAIL_MADRE, PASSWORD_MADRE)

conectar_correo()

def buscar_en_correo(correo_cliente, tipo_busqueda):
    global conexion_mail
    try:
        try:
            conexion_mail.select('inbox')
        except:
            conectar_correo()
            conexion_mail.select('inbox')

        # 1. Asignar la palabra clave del asunto dependiendo del comando
        if tipo_busqueda == "link":
            asunto = "hogar"
        elif tipo_busqueda == "codigo6":
            asunto = "vence"
        elif tipo_busqueda == "codigo4":
            asunto = "inicio"
        elif tipo_busqueda == "temporal":
            asunto = "temporal"
        else:
            asunto = ""

        # 2. Buscar en Gmail filtrando por esa palabra exacta
        if asunto != "":
            status, mensajes = conexion_mail.search(None, f'(TO "{correo_cliente}" FROM "Netflix" SUBJECT "{asunto}")')
        else:
            status, mensajes = conexion_mail.search(None, f'(TO "{correo_cliente}" FROM "Netflix")')
        lista_ids = mensajes[0].split()

        if not lista_ids:
            return "❌ No se encontró ningún correo reciente para esta cuenta. Espera 1 minuto y vuelve a intentar."

        ultimo_id = lista_ids[-1]
        status, datos = conexion_mail.fetch(ultimo_id, '(RFC822)')
        mensaje_raw = datos[0][1]
        mensaje_email = email.message_from_bytes(mensaje_raw)

        cuerpo = ""
        if mensaje_email.is_multipart():
            for part in mensaje_email.walk():
                if part.get_content_type() == "text/plain" or part.get_content_type() == "text/html":
                    cuerpo = part.get_payload(decode=True).decode('utf-8')
                    break
        else:
            cuerpo = mensaje_email.get_payload(decode=True).decode('utf-8')

        if tipo_busqueda == "link":
            match = re.search(r'(https://www\.netflix\.com/account/update.*?)["\s]', cuerpo)
            return f"✅ LINK DE HOGAR (TV):\n{match.group(1)}" if match else "❌ Link no encontrado en el correo."
        elif tipo_busqueda == "codigo4":
            match = re.search(r'\b\d{4}\b', cuerpo)
            return f"✅ CÓDIGO DE INICIO (4 dígitos): {match.group(0)}" if match else "❌ Código no encontrado."
        elif tipo_busqueda == "codigo6":
            match = re.search(r'\b\d{6}\b', cuerpo)
            return f"✅ CÓDIGO DE INICIO (6 dígitos): {match.group(0)}" if match else "❌ Código no encontrado."
        elif tipo_busqueda == "temporal":
            match = re.search(r'\b\d{4}\b', cuerpo)
            return f"📱 ✅ CÓDIGO TEMPORAL (Celular): {match.group(0)}" if match else "❌ Código temporal no encontrado."

    except Exception as e:
        return f"Error de conexión: {e}"

# --- COMANDOS DE ADMINISTRACIÓN (SOLO PARA TI) ---

@bot.message_handler(commands=['permitir'])
def dar_permiso(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ No tienes permisos para usar este comando.")
        return
    try:
        partes = message.text.split()
        id_cliente = partes[1]
        correo = partes[2]
        
        accesos = cargar_accesos()
        if id_cliente not in accesos:
            accesos[id_cliente] = []
        if correo not in accesos[id_cliente]:
            accesos[id_cliente].append(correo)
        
        guardar_accesos(accesos)
        bot.reply_to(message, f"✅ Acceso concedido.\nEl ID {id_cliente} ahora puede usar el correo {correo}.")
    except IndexError:
        bot.reply_to(message, "⚠️ Formato incorrecto. Usa: /permitir ID_CLIENTE correo@gmail.com")

@bot.message_handler(commands=['revocar'])
def quitar_permiso(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ No tienes permisos para usar este comando.")
        return
    try:
        partes = message.text.split()
        id_cliente = partes[1]
        correo = partes[2]
        
        accesos = cargar_accesos()
        if id_cliente in accesos and correo in accesos[id_cliente]:
            accesos[id_cliente].remove(correo)
            guardar_accesos(accesos)
            bot.reply_to(message, f"❌ Acceso revocado.\nEl ID {id_cliente} ya no puede usar el correo {correo}.")
        else:
            bot.reply_to(message, "Ese usuario no tenía acceso a ese correo.")
    except IndexError:
        bot.reply_to(message, "⚠️ Formato incorrecto. Usa: /revocar ID_CLIENTE correo@gmail.com")


# --- COMANDOS PARA LOS CLIENTES ---

@bot.message_handler(commands=['mi_id'])
def mostrar_id(message):
    bot.reply_to(message, f"Tu ID de Telegram es: {message.from_user.id}")

def procesar_peticion(message, tipo):
    try:
        correo_cliente = message.text.split()[1]
        
        # VERIFICACIÓN DE SEGURIDAD
        if not tiene_acceso(message.from_user.id, correo_cliente):
            bot.reply_to(message, "⛔ No tienes una suscripción activa o no tienes permiso para ver los códigos de este correo.")
            return

        bot.send_chat_action(message.chat.id, 'typing')
        respuesta = buscar_en_correo(correo_cliente, tipo)
        bot.reply_to(message, respuesta)
    except IndexError:
        bot.reply_to(message, f"⚠️ Formato incorrecto. Usa: /{message.text.split()[0].replace('/', '')} correo@gmail.com")

@bot.message_handler(commands=['link'])
def mandar_link(message):
    procesar_peticion(message, "link")

@bot.message_handler(commands=['codigo'])
def mandar_codigo4(message):
    procesar_peticion(message, "codigo4")

@bot.message_handler(commands=['codigo6'])
def mandar_codigo6(message):
    procesar_peticion(message, "codigo6")

@bot.message_handler(commands=['temporal'])
def mandar_temporal(message):
    procesar_peticion(message, "temporal")

bot.polling(none_stop=True)