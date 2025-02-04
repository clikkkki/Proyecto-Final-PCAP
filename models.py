from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship # Me va a servir para relacionar distintas tablas
import db
from flask_login import UserMixin

# Clase para la tabla de usuarios
class Usuarios(UserMixin, db.Base): # UserMixin añade los atributos is_authenticates, is_active, is_anonymous y get_id

    '''
    Clase Usuarios:
    Creación de la tabla 'usuarios' con las siguientes columnas:
    - id (PK) - integer
    - nombre - string
    - correo - string
    - contrasena - string
    - es_admin - boolean
    '''

    __tablename__ = "usuarios"  # Nombre de la tabla en la base de datos
    __table_args__ = {"sqlite_autoincrement": True}  # ID autoincremental en SQLite

    # Columnas de la tabla
    id = Column(Integer, primary_key=True)  # Clave primaria
    nombre = Column(String(50), nullable=False)  # Nombre del cliente
    apellidos = Column(String(50), nullable=False) # Apellidos del cliente
    usuario = Column(String(50), nullable=False) # Nombre de usuario
    correo = Column(String(100), unique=True, nullable=False)  # Correo único y obligatorio
    contrasena = Column(String(100), nullable=False)  # Contraseña
    es_admin = Column(Boolean, default=False)  # Indica si el usuario es administrador

    # Relación con la tabla UsuarioContenido
    contenido = relationship("UsuarioContenido", back_populates="usuario")

    # Constructor
    def __init__(self, nombre, apellidos, usuario, correo, contrasena, es_admin=False):
        self.nombre = nombre
        self.apellidos = apellidos
        self.usuario = usuario
        self.correo = correo
        self.contrasena = contrasena
        self.es_admin = es_admin

    # Método str
    def __str__(self):
        return f"Usuario(Nombre: {self.usuario}, Correo: {self.correo}, Admin: {self.es_admin})"

class Contenido(db.Base):

    '''
    Clase Contenido:
    Creación de la tabla 'contenido' con las siguientes columnas:
    - id (PK) - integer
    - titulo - string
    - tipo - boolean (true - serie / false - película)
    - duracion - integer (en el caso de las series es el sumatorio de todos los capítulos)
    - lanzamiento - integer
    - director - string
    - genero - string
    - sinopsis (opcional) - string
    - nTemporadas
    - nCapitulos (solo si es serie)
    - capitulosTemporada
    - portada 
    '''

    __tablename__ = "contenido"  # Nombre de la tabla en la base de datos
    __table_args__ = {"sqlite_autoincrement": True}  # ID autoincremental en SQLite

    # Columnas de la tabla
    id = Column(Integer, primary_key=True)  # Clave primaria
    titulo = Column(String(100), nullable=False)  # Título
    tipo = Column(Boolean, nullable=False) # Tipo (serie o película, False - película, True - serie)
    duracion = Column(Integer, nullable=False)  # Duración (en minutos)
    lanzamiento = Column(Integer, nullable=False)  # Año del lanzamiento
    director = Column(String(100), nullable=False)  # Director
    genero = Column(String(200), nullable=False)  # Género
    sinopsis = Column(Text, nullable=False)  # Sinopsis
    nTemporadas = Column(Integer, nullable=False) # Número de Temporadas (en caso de película asignaré el valor de 1)
    nCapitulos = Column(Integer, nullable=False)  # Número de Capítulos (en caso de película asignaré el valor de 1)
    capitulosTemporada = Column(Text, nullable=False) # Número de Capítulos por Temporada (voy a manipularlo como un texto ya que sqlite no soporta listas)
    portada = Column(Text, nullable=False) # Ruta de la imagen de la portada

    # Relación con la tabla UsuarioContenido
    usuarios = relationship("UsuarioContenido", back_populates="contenido")

    # Constructor
    def __init__(self, titulo, tipo, duracion, lanzamiento, director, genero, sinopsis, nTemporadas, nCapitulos, capitulosTemporada, portada):
        self.titulo = titulo
        self.tipo = tipo
        self.duracion = duracion
        self.lanzamiento = lanzamiento
        self.director = director
        self.genero = genero
        self.sinopsis = sinopsis
        self.nTemporadas = nTemporadas
        self.nCapitulos = nCapitulos
        self.capitulosTemporada = capitulosTemporada
        self.portada = portada

    # Método str
    def __str__(self):

        # Creo una variable donde convierto la variable 'tipo' de booleano a string para poder imprimirlo
        tipo_str = "Serie" if self.tipo else "Película" # si tipo = True -> Serie, de lo contrario -> Película

        return (
            f"Contenido:\n"
            f"- ID: {self.id}\n"
            f"- Título: {self.titulo}\n"
            f"- Tipo: {tipo_str}\n"
            f"- Duración: {self.duracion} minutos\n"
            f"- Lanzamiento: {self.lanzamiento}\n"
            f"- Director: {self.director}\n"
            f"- Género: {self.genero}\n"
            f"- Sinopsis: {self.sinopsis or 'No disponible'}\n"
            f"- Número de capítulos: {self.nCapitulos if self.nCapitulos else 'N/A'}"
        )


class UsuarioContenido(db.Base):

    '''
    Clase UsuarioContenido:
    Esta clase representa una tabla intermedia para gestionar la relación entre la tabla
    'usuarios' y la tabla 'contenido'.

    Columnas:
    - usuario_id (ForeignKey): Clave foránea que referencia la ID del usuario en la tabla 'usuarios'.
    - contenido_id (ForeignKey): Clave foránea que referencia la ID del contenido (película o serie) en la tabla 'contenido'.
    - es_favorito (Boolean): Indica si el usuario ha marcado el contenido como favorito.
    - esta_visto (Boolean): Indica si el usuario ya ha visto el contenido.
    '''

    __tablename__ = 'usuario_contenido' # Nombre de la tabla en la base de datos
    __table_args__ = {"sqlite_autoincrement": True}  # ID autoincremental en SQLite

    # Columnas de la tabla
    id = Column(Integer, primary_key=True)  # Clave primaria
    id_usuario = Column(Integer, ForeignKey('usuarios.id'), nullable=False)  # Clave foránea usuario
    id_contenido = Column(Integer, ForeignKey('contenido.id'), nullable=False)  # Clave foránea contenido
    vista = Column(Boolean, default=False)  # Marcador de 'vista'
    favorita = Column(Boolean, default=False)  # Marcador de 'favorita'

    # Relación con las tablas referenciadas
    usuario = relationship("Usuarios", back_populates="contenido") # Para que la relación entre tablas sea bidireccional
    contenido = relationship("Contenido", back_populates="usuarios")

    def __init__(self, id_usuario, id_contenido, vista=False, favorita=False):
        self.id_usuario = id_usuario
        self.id_contenido = id_contenido
        self.vista = vista
        self.favorita = favorita