import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
from openai import OpenAI
from ticket import Ticket
import os
from dotenv import load_dotenv


""" 

--CHATBOT DE ASISTENCIA AL ALUMNO CEIDS--


1. Proceso de instalación:

    - Crear una cuenta en Discord for developers y crear una nueva aplicacion.
    - Se generará una public key del bot y se pone en la variable "TOKEN_DISCORD"/
    - En el Apartado Bot dar todos los permisos en 'Privileged Gateway Intents'.
    
    - Para añadir el bot en el servidor en el apartado de 'Installaton' habrá un link de instalacion,
      este link lo va a mandar a su discord y deberá elegir el servidor en donde quiere invitar al bot.
      
    - Poner una API valida de algun proveedor de LLM's.
    - Se recomienda crear una nueva categoria llamada 'Soporte', igualmente 
      se puede alojar en cualquier categoria siempre y cuando se pase el ID de esta.
    - Es necesario crear un canal de texto llamado 'tickets' dentro de la categoria elegida, sino mandará un mensaje de error.
    - El bot ya esta listo para ejecutarse, para pausar el bot se presionar CTRL + C.
    

2. Bugs Encontrados:

    - Al momento que un usuario esta dentro de un ticket privado y el bot se pause inesperadamente, entonces no hara el borrado
      automatico del ticket.



"""



load_dotenv() 


# Leer rol de sistema del chatbot
def rol_sistema():
    rol = ""
    with open("role.txt", "r", encoding="UTF-8") as archivo:
        lineas = archivo.readlines()
        for linea in lineas:
            rol += linea + "\n"
    return rol
            
    
        
# Inicializa la API de OpenAI
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv('OPENAI_API_KEY')
)



# Variables constantes
ROL_SISTEMA = "Eres un asistente del Circulo de investigacion y Desarrollo de Software de la universidad de lima, limitate unicamente a responder preguntas acerca de tu rol y de este documento en donde hay informacion relacionada al circulo. Vuelvo a repetir no respondas nada ajeno al documento: " + rol_sistema()
TOKEN_DISCORD = os.getenv('DISCORD_TOKEN')
CATEGORIA_SOPORTE_ID = int(os.getenv('ID_CATEGORIA_DISCORD'))
CANAL_TICKETS_NOMBRE = "tickets"
EMOJI_TICKET = "✅"  # Emoji para crear tickets



# Configurar permisos del bot
intents = discord.Intents.default()
intents.message_content = True  # Necesario para leer el contenido de los mensajes
intents.guilds = True
intents.messages = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# Diccionario para controlar tickets activos
tickets_activos = {}
mensaje_tickets = ""



@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    await crear_mensaje_tickets()
    limpiar_tickets_inactivos.start()


#Mensaje inicial y unico del bot en el canal de soporte
async def crear_mensaje_tickets():
    global mensaje_tickets
    
    canal = discord.utils.get(bot.get_all_channels(), name=CANAL_TICKETS_NOMBRE)
    if not canal:
        print("Error: No se encontró el canal de tickets")
        return

    # Buscar si ya existe un mensaje del bot
    async for msg in canal.history(limit=10):
        if msg.author == bot.user and len(msg.embeds) > 0:
            mensaje_tickets = msg
            await mensaje_tickets.add_reaction(EMOJI_TICKET)
            return

    # Si no existe, crear uno nuevo. En caso especial en el que se elimine o se borre el mensaje por casualidad xd.
    embed = discord.Embed(
        title="🆘 Sistema de Tickets de Soporte",
        description=f"Reacciona con {EMOJI_TICKET} para crear un nuevo ticket de ayuda.\n\n"
                   "Un asistente te atenderá en un canal privado.",
        color=discord.Color.blue()
    )
    mensaje_tickets = await canal.send(embed=embed)
    await mensaje_tickets.add_reaction(EMOJI_TICKET)
    
@bot.event
async def on_raw_reaction_add(payload):
    # Ignorar reacciones del propio bot
    if payload.user_id == bot.user.id:
        return

    # Verificar que es la reacción correcta en el canal correcto
    if payload.channel_id != mensaje_tickets.channel.id or str(payload.emoji) != EMOJI_TICKET:
        return

    # Obtener información necesaria
    guild = bot.get_guild(payload.guild_id)
    usuario = guild.get_member(payload.user_id)
    canal = mensaje_tickets.channel

    # Verificar que es al mensaje correcto
    if payload.message_id != mensaje_tickets.id:
        return

    # Crear el ticket
    categoria = discord.utils.get(guild.categories, id=CATEGORIA_SOPORTE_ID)
    if not categoria:
        await canal.send("❌ No se encontró la categoría de soporte")
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        usuario: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
    }

    try:
        canal_ticket = await guild.create_text_channel(
            name=f"ticket-{usuario.name}",
            overwrites=overwrites,
            category=categoria,
            topic=f"Ticket de {usuario.name}"
        )
        
        tickets_activos[canal_ticket.id] = Ticket(
            canal=canal_ticket,
            usuario=usuario,
            ultima_interaccion=datetime.utcnow()
        )
        
        embed = discord.Embed(
            title=f"Ticket de {usuario.name}",
            description=f"¡Hola {usuario.mention}! Soy el asistente virtual.\n\n"
                       "Por favor describe tu consulta y te ayudaré.\n"
                       "Escribe `!cerrar` para finalizar este ticket.",
            color=discord.Color.green()
        )
        await canal_ticket.send(embed=embed)
        
        # Eliminar la reacción del usuario
        await mensaje_tickets.remove_reaction(EMOJI_TICKET, usuario)
        
    except Exception as e:
        print(f"Error al crear ticket: {e}")
        await canal.send(f"{usuario.mention} ❌ No pude crear tu ticket. Intenta nuevamente.")


# Tarea para limpiar tickets inactivos
@tasks.loop(seconds=30) #Repite esta tarea cada minuto
async def limpiar_tickets_inactivos():
    ahora = datetime.utcnow()
    tickets_a_eliminar = []
    
    for ticket_id, ticket in tickets_activos.items():
        if not ticket.cerrado and (ahora - ticket.ultima_interaccion) > timedelta(seconds=30):
            try:
                await ticket.canal.send("🔒 Cerrando ticket por inactividad...")
                await asyncio.sleep(3)
                await ticket.canal.delete(reason="Ticket inactivo por más de 30 segundos")
                tickets_a_eliminar.append(ticket_id)
            except Exception as e:
                print(f"Error al eliminar ticket {ticket_id}: {e}")
    
    for ticket_id in tickets_a_eliminar:
        del tickets_activos[ticket_id]


@bot.command()
async def cerrar(ctx):
    if not ctx.channel.name.startswith("ticket-"):
        return
    
    ticket = tickets_activos.get(ctx.channel.id)
    if not ticket or (ctx.author != ticket.usuario and not ctx.author.guild_permissions.manage_messages):
        await ctx.send("⚠️ No tienes permisos para cerrar este ticket")
        return
    
    ticket.cerrado = True
    
    embed = discord.Embed(
        title="Ticket cerrado",
        description="Este ticket será eliminado en breve.",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)
    
    await asyncio.sleep(5)
    try:
        await ctx.channel.delete(reason=f"Ticket cerrado por {ctx.author.name}")
        del tickets_activos[ctx.channel.id]
    except Exception as e:
        print(f"Error al eliminar canal: {e}")


# Respuesta de OpenAI en los tickets
@bot.event
async def on_message(message):
    if message.author == bot.user or message.content.startswith('!'):
        await bot.process_commands(message)
        return
    
    if message.channel.id in tickets_activos and not message.author.bot:
        ticket = tickets_activos[message.channel.id]
        ticket.ultima_interaccion = datetime.utcnow()
        
        try:
            async with message.channel.typing():
                response = client.chat.completions.create(
                    model="deepseek/deepseek-prover-v2:free",
                    messages=[
                        {"role": "system", "content": ROL_SISTEMA},
                        {"role": "user", "content": message.content}
                    ],
                    temperature=0.7,
                )
                
                respuesta = response.choices[0].message.content.strip()
                await message.channel.send(f"{message.author.mention} {respuesta}")
                
        except Exception as e:
            print(f"Error con OpenAI: {e}")
            await message.channel.send("⚠️ Ocurrió un error al procesar tu consulta")
    
    await bot.process_commands(message)


bot.run(TOKEN_DISCORD)



