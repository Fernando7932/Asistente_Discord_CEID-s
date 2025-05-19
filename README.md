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
