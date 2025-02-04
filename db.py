from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine("sqlite:///database/netflix.db",
                       connect_args={'check_same_thread': False}) # No puede gestionar la DB en el mismo hilo que la aplicación principal
# Flask al crear el servidor web ocupa y usa el hilo principal, así que ponemos esta coletilla para que la DB use un hilo propio y específico

# Advertencia, crear el engine no conecta inmediatamente a la base de datos

# Ahora crearemos la sesión, lo que nos permite realizar transacciones dentro de la DB
Session = sessionmaker(bind=engine) # estoy creando una clase
session = Session() # este objeto va a ser el encargado de poder comunicarse y realizar transacciones en la DB

# Esta clase se encarga de mapear la información de las clases en las que hereda
# y vincular su información a tablas de la DB
Base = declarative_base()