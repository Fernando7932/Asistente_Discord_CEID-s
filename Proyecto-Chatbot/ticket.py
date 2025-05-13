


class Ticket:
    def __init__(self, canal, usuario, ultima_interaccion):
        self.canal = canal
        self.usuario = usuario
        self.ultima_interaccion = ultima_interaccion
        self.cerrado = False