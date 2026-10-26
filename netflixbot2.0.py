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

# --- TU ID DE ADMINISTRADOR PRINCIPAL (SUPER ADMIN) ---
SUPER_ADMIN_ID = 6323259714

# --- SISTEMA DE ALMACENAMIENTO INTELIGENTE (VOLUMEN O LOCAL) ---
if os.path.exists('/app') or os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY_STATIC_URL'):
    os.makedirs('/app/data', exist_ok=True)
    ARCHIVO_ACCESOS = '/app/data/accesos.json'
    ARCHIVO_ADMINS = '/app/data/admins.json'
else:
    ARCHIVO_ACCESOS = 'accesos.json'
    ARCHIVO_ADMINS = 'admins.json'

# --- GESTIÓN DE ACCESOS DE CLIENTES ---
def cargar_accesos():
    if os.path.exists(ARCHIVO_ACCESOS):
        with open(ARCHIVO_ACCESOS, 'r') as f:
            return json.load(f)
    return {}

def guardar_accesos(datos):
    with open(ARCHIVO_ACCESOS, 'w') as f:
        json.dump(datos, f)

# --- GESTIÓN DE ADMINISTRADORES DINÁMICOS ---
def cargar_admins():
    if os.path.exists(ARCHIVO_ADMINS):
        with open(ARCHIVO_ADMINS, 'r') as f:
            return json.load(f)
    return []

def guardar_admins(datos):
    with open(ARCHIVO_ADMINS, 'w') as f:
        json.dump(datos, f)

def es_admin(user_id):
    if user_id == SUPER_ADMIN_ID:
        return True
    return user_id in cargar_admins()

def tiene_acceso(user_id, correo, plataforma):
    if es_admin(user_id):
        return True # Los administradores tienen acceso total a todo
    accesos = cargar_accesos()
    user_str = str(user_id)
    if user_str in accesos:
        permiso_requerido = f"{correo}:{plataforma}"
        return permiso_requerido in accesos[user_str]
    return False

# --- CONEXIÓN AL CORREO ---
conexion_mail = None

def conectar_correo():
    global conexion_mail
    print("Iniciando sesión en Gmail (una sola vez)...")
    conexion_mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    conexion_mail.login(EMAIL_MADRE, PASSWORD_MADRE)

conectar_correo()

# Función segura para decodificar correos con tildes
def decodificar_texto(payload_bytes):
    try:
        return payload_bytes.decode('utf-8')
    except UnicodeDecodeError:
        try:
            return payload_bytes.decode('latin-1')
        except:
            return payload_bytes.decode('utf-8', errors='ignore')

def buscar_en_correo(correo_cliente, tipo_busqueda):
    global conexion_mail
    try:
        try:
            conexion_mail.select('inbox')
        except:
            conectar_correo()
            conexion_mail.select('inbox')

        if tipo_busqueda == "link":
            asunto = "hogar"
        elif tipo_busqueda == "codigo6":
            asunto = "vence"
        elif tipo_busqueda == "codigo4":
            asunto = "inicio"
        elif tipo_busqueda == "temporal":
            asunto = "temporal"
        elif tipo_busqueda == "max":
            asunto = "urgente"
        else:
            asunto = ""

        if tipo_busqueda == "max":
            status, mensajes = conexion_mail.search(None, f'(TO "{correo_cliente}" FROM "Max" SUBJECT "{asunto}")')
        elif asunto != "":
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
                    payload = part.get_payload(decode=True)
                    if payload:
                        cuerpo = decodificar_texto(payload)
                        break
        else:
            payload = mensaje_email.get_payload(decode=True)
            if payload:
                cuerpo = decodificar_texto(payload)

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
        elif tipo_busqueda == "max":
            match = re.search(r'\b\d{6}\b', cuerpo)
            return f"🍿 ✅ CÓDIGO DE MAX (6 dígitos): {match.group(0)}" if match else "❌ Código de Max no encontrado en el correo."

    except Exception as e:
        return f"Error de conexión: {e}"

# --- COMANDOS DE CONTROL DE ADMINISTRADORES (SOLO SUPER ADMIN) ---

@bot.message_handler(commands=['agregar_admin'])
def agregar_admin(message):
    if message.from_user.id != SUPER_ADMIN_ID:
        bot.reply_to(message, "⛔ Solo el Administrador Principal puede agregar nuevos administradores.")
        return
    try:
        partes = message.text.split()
        nuevo_id = int(partes[1])
        
        admins = cargar_admins()
        if nuevo_id not in admins and nuevo_id != SUPER_ADMIN_ID:
            admins.append(nuevo_id)
            guardar_admins(admins)
            bot.reply_to(message, f"✅ Administrador agregado con éxito.\nEl ID {nuevo_id} ahora tiene permisos de administración.")
        else:
            bot.reply_to(message, "⚠️ Este ID ya es administrador o es el principal.")
    except (IndexError, ValueError):
        bot.reply_to(message, "⚠️ Formato incorrecto. Usa: /agregar_admin ID_DE_TELEGRAM")

@bot.message_handler(commands=['quitar_admin'])
def quitar_admin(message):
    if message.from_user.id != SUPER_ADMIN_ID:
        bot.reply_to(message, "⛔ Solo el Administrador Principal puede quitar administradores.")
        return
    try:
        partes = message.text.split()
        admin_a_quitar = int(partes[1])
        
        admins = cargar_admins()
        if admin_a_quitar in admins:
            admins.remove(admin_a_quitar)
            guardar_admins(admins)
            bot.reply_to(message, f"❌ Administrador removido.\nEl ID {admin_a_quitar} ya no es administrador.")
        else:
            bot.reply_to(message, "⚠️ Ese ID no se encuentra en la lista de administradores secundarios.")
    except (IndexError, ValueError):
        bot.reply_to(message, "⚠️ Formato incorrecto. Usa: /quitar_admin ID_DE_TELEGRAM")

# --- COMANDOS DE PERMISOS PARA CLIENTES (PARA ADMINS) ---

@bot.message_handler(commands=['permitir'])
def dar_permiso(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permisos para usar este comando.")
        return
    try:
        partes = message.text.split()
        id_cliente = partes[1]
        correo = partes[2]
        plataforma = partes[3].lower()
        
        if plataforma not in ["netflix", "max"]:
            bot.reply_to(message, "⚠️ Plataforma inválida. Debe ser exactamente: netflix o max")
            return
        
        accesos = cargar_accesos()
        if id_cliente not in accesos:
            accesos[id_cliente] = []
            
        permiso = f"{correo}:{plataforma}"
        if permiso not in accesos[id_cliente]:
            accesos[id_cliente].append(permiso)
        
        guardar_accesos(accesos)
        bot.reply_to(message, f"✅ Acceso concedido.\nEl ID {id_cliente} ahora puede usar *{plataforma.upper()}* en el correo {correo}.")
    except IndexError:
        bot.reply_to(message, "⚠️ Formato incorrecto.\nUsa: /permitir ID_CLIENTE correo@gmail.com netflix\no bien: /permitir ID_CLIENTE correo@gmail.com max")

@bot.message_handler(commands=['revocar'])
def quitar_permiso(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permisos para usar este comando.")
        return
    try:
        partes = message.text.split()
        id_cliente = partes[1]
        correo = partes[2]
        plataforma = partes[3].lower()
        
        accesos = cargar_accesos()
        permiso = f"{correo}:{plataforma}"
        
        if id_cliente in accesos and permiso in accesos[id_cliente]:
            accesos[id_cliente].remove(permiso)
            guardar_accesos(accesos)
            bot.reply_to(message, "❌ Acceso revocado correctamente.")
        else:
            bot.reply_to(message, "Ese usuario no tenía ese permiso registrado.")
    except IndexError:
        bot.reply_to(message, "⚠️ Formato incorrecto. Usa: /revocar ID_CLIENTE correo@gmail.com netflix (o max)")

# --- COMANDO /START ---

@bot.message_handler(commands=['start'])
def enviar_bienvenida(message):
    texto_ayuda = (
        "🤖 *¡Bienvenido al Bot Automático de Códigos!* 🎬🍿\n\n"
        "📋 *Comandos Disponibles:*\n"
        "• `/mi_id` - Muestra tu ID único de Telegram.\n"
        "• `/link [correo]` - Link de hogar para TV (Netflix).\n"
        "• `/codigo [correo]` - Código de inicio de 4 dígitos (Netflix).\n"
        "• `/codigo6 [correo]` - Código de inicio de 6 dígitos (Netflix).\n"
        "• `/temporal [correo]` - Código temporal para móvil (Netflix).\n"
        "• `/max [correo]` - Código de verificación de Max.\n\n"
        "⚠️ *Nota:* Solo podrás solicitar códigos de la plataforma que tengas contratada y autorizada."
    )
    bot.reply_to(message, texto_ayuda, parse_mode="Markdown")

# --- COMANDOS PARA CLIENTES ---

@bot.message_handler(commands=['mi_id'])
def mostrar_id(message):
    bot.reply_to(message, f"Tu ID de Telegram es: {message.from_user.id}")

def procesar_peticion(message, tipo, plataforma):
    try:
        correo_cliente = message.text.split()[1]
        
        if not tiene_acceso(message.from_user.id, correo_cliente, plataforma):
            bot.reply_to(message, f"⛔ No tienes una suscripción activa para {plataforma.upper()} en este correo o no estás autorizado.")
            return

        bot.send_chat_action(message.chat.id, 'typing')
        respuesta = buscar_en_correo(correo_cliente, tipo)
        bot.reply_to(message, respuesta)
    except IndexError:
        bot.reply_to(message, f"⚠️ Formato incorrecto. Usa: /{message.text.split()[0].replace('/', '')} correo@gmail.com")

@bot.message_handler(commands=['link'])
def mandar_link(message):
    procesar_peticion(message, "link", "netflix")

@bot.message_handler(commands=['codigo'])
def mandar_codigo4(message):
    procesar_peticion(message, "codigo4", "netflix")

@bot.message_handler(commands=['codigo6'])
def mandar_codigo6(message):
    procesar_peticion(message, "codigo6", "netflix")

@bot.message_handler(commands=['temporal'])
def mandar_temporal(message):
    procesar_peticion(message, "temporal", "netflix")

@bot.message_handler(commands=['max'])
def mandar_max(message):
    procesar_peticion(message, "max", "max")

bot.polling(none_stop=True)
