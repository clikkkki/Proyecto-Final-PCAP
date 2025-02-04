import base64
import math
import os
from fileinput import filename
from flask import Flask, render_template, request, redirect, url_for, flash, session
from sqlalchemy import delete, desc
from sqlalchemy.sql.functions import current_user, func
import db
from models import Usuarios, UsuarioContenido, Contenido
import json
from flask_login import LoginManager, logout_user, login_required, login_user, current_user
import secrets
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import io
from werkzeug.security import generate_password_hash, check_password_hash

clave = secrets.token_hex(16) # Genero una clave secreta (lo ideal sería almacenarla fuera del código)

app = Flask(__name__) # Creo el servidor web flask
app.secret_key = clave # Asigno la secret_key para proteger los datos
login_manager = LoginManager(app) # Inicializo flask-login
app.config['UPLOAD_FOLDER'] = 'static/recursos/portadas/'  # Ruta para guardar las imágenes
app.config['ALLOWED_EXTENSIONS'] = {'jpg'}  # Extensiones permitidas

@login_manager.user_loader
def load_user(user_id): # Indico a LoginManager cómo cargar un usuario de la db a partir del ID
    return db.session.query(Usuarios).get(int(user_id))

# HOME
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():

    todos_los_usuarios = db.session.query(Usuarios).all()  # Consulto y almaceno todas las cuentas para el inicio de sesión

    if request.method == 'POST':

        correo = request.form['correo']
        contrasena = request.form['contrasena']

        lista_correos = [] # Creo una lista con los correos para recorrerla y comparar con el correo introducido

        for cuenta in todos_los_usuarios:
            lista_correos.append(cuenta.correo)

        try:

            if correo not in  lista_correos:
                raise ValueError('El correo introducido no existe')
            else:
                cuenta_usuario = db.session.query(Usuarios).filter(Usuarios.correo==correo).first()

            if not check_password_hash(cuenta_usuario.contrasena, contrasena):
                raise ValueError('Contraseña incorrecta')

        except ValueError as e:

            # Capturar errores específicos y pasar el mensaje a la plantilla

            return render_template('index.html', error_message=e)


        except Exception as e:

            # Capturar errores generales y pasar el mensaje a la plantilla

            return render_template('index.html',
                                   error_message="Ha ocurrido un error inesperado. Inténtalo de nuevo más tarde.")

        login_user(cuenta_usuario) # Inicia sesión
        return redirect(url_for('mostrar_catalogo'))

    else:
        return render_template('index.html')

@app.route('/logout')
@login_required # Decorador para proteger la ruta (si no estás logeado no puedes acceder a ella)
def logout(): # Cierro la sesión del usuario y lo redirijo a 'login'
    logout_user()
    return redirect(url_for('login'))

@app.route('/registro', methods=['GET', 'POST']) # Uso el método get para visualizar la página y el post para enviar los datos a la db
def crear_cuenta():
    # Hago un if para comprobar con el método post si los datos han sido enviados
    # y si no es así, primero cargo el archivo 'registro.html' para mostrar la página de registro al usuario
    if request.method == 'POST':

        campos = list(request.form.values()) # Lista de todos los elementos enviados

        try:

            if any (not campo for campo in campos): # Comprueba si hay algún elemento vacío
                raise ValueError('Todos los campos deben ser completados')

            if db.session.query(Usuarios).filter(Usuarios.correo == request.form['correo']).first(): # Comprueba si el correo introducido ya existe
                raise ValueError('Este correo ya existe')

            if not request.form['correo'].endswith('@gmail.com'): # Comprueba si el correo introducido ya acaba en '@gmail.com'
                raise ValueError("Asegúrate de introducir un correo válido (debe terminar en '@gmail.com')")

            # Comprueba si la contraseña contiene algún número, mayúscula y contiene mínimo 10 carácteres (para mayor seguridad del usuario)
            contra = request.form['contrasena']
            if not (any(caracter.isdigit() for caracter in contra) and any(caracter.isupper() for caracter in contra) and len(contra) >= 10):
                raise ValueError("La contraseña debe tener al menos 10 carácteres e incluir números y mayúsculas")

            # Con esta función genero un hash de la contraseña para mayor seguridad
            contra_hasheada = generate_password_hash(contra, method='pbkdf2:sha256:600000', salt_length=16)

            cuenta = Usuarios(
                nombre=request.form['nombre'],
                apellidos=request.form['apellidos'],
                usuario=request.form['usuario'],
                correo=request.form['correo'],
                contrasena=contra_hasheada,
                es_admin=False
            )

            db.session.add(cuenta) # Añado los datos a la DB
            db.session.commit()


        except ValueError as e:

            # Capturar errores específicos y pasar el mensaje a la plantilla

            return render_template('crear_cuenta.html', error_message=e)


        except Exception as e:

            # Capturar errores generales y pasar el mensaje a la plantilla

            return render_template('registro.html',
                                   error_message="Ha ocurrido un error inesperado. Inténtalo de nuevo más tarde.")

        return render_template('cuenta_creada.html') # Muestro un mensaje de cuenta creada con éxito en una página nueva

    return render_template('crear_cuenta.html')


@app.route('/cuenta-creada')
def mensaje():
    return redirect(url_for('home'))  # Una vez creada la cuenta y mostrado el mensaje redirecciono a 'home'


@app.route('/mostrar-catalogo')
@login_required
def mostrar_catalogo():

    if current_user.es_admin: # Si el usuario logueado es administrador lo envío al menú de edición
        return redirect(url_for('editar'))
    else: # De lo contrario le muestro el catálogo
        return render_template('cliente.html')


@app.route('/volver-a-home')
@login_required
def volver():
    return redirect(url_for('mostrar_catalogo'))


@app.route('/peliculas')
@login_required
def peliculas():

    lista_peliculas = db.session.query(Contenido).filter(Contenido.tipo==False).all()


    return render_template('catalogo.html', lista_contenido=lista_peliculas, tipo='película')


@app.route('/series')
@login_required
def series():

    lista_series = db.session.query(Contenido).filter(Contenido.tipo==True).all()

    return render_template('catalogo.html', lista_contenido=lista_series, tipo='serie')


@app.route('/favoritas')
@login_required
def favoritas():

    # Añado todos los elementos de la tabla UsuarioContenido con el valor de favorita = True y que coincida con el id del usuario logueado
    lista_favoritas_uc = db.session.query(UsuarioContenido).filter_by(
        id_usuario=current_user.id,
        favorita=True).all()

    # Recorro la lista de elementos y almaceno las coincidencias en la tabla Contenido (donde está toda la información del contenido en cuestión)
    # en una lista la cual envío al front end
    lista_favoritas = []
    for contenido in lista_favoritas_uc:
        fav = db.session.query(Contenido).filter(Contenido.id==contenido.id_contenido).first()
        lista_favoritas.append(fav)

    # Guardo una lista de ids en la sesión (para no tener que repetir la consulta más adelante)
    session['lista_favoritas'] = [favorita.id for favorita in lista_favoritas]

    return render_template('catalogo.html', lista_contenido=lista_favoritas, tipo='favorita')


@app.route('/vistas')
@login_required
def vistas():

    # Añado todos los elementos de la tabla UsuarioContenido con el valor de vista = True y que coincida con el id del usuario logueado
    lista_vistas_uc = db.session.query(UsuarioContenido).filter_by(
        id_usuario=current_user.id,
        vista=True).all()

    # Recorro la lista de elementos y almaceno las coincidencias en la tabla Contenido (donde está toda la información del contenido en cuestión)
    # en una lista la cual envío al front end
    lista_vistas = []
    for contenido in lista_vistas_uc:
        vista = db.session.query(Contenido).filter(Contenido.id == contenido.id_contenido).first()
        lista_vistas.append(vista)

    # Guardo una lista de ids en la sesión (para no tener que repetir la consulta más adelante)
    session['lista_vistas'] = [vista.id for vista in lista_vistas]

    return render_template('catalogo.html', lista_contenido=lista_vistas, tipo='vista')


@app.route('/añadir-favoritas/<id>')
@login_required
def aniadir_favoritas(id):

    # Primero compruebo si el usuario tiene el contenido en vistos o favoritos
    # De esta manera evito duplicados y también evito manipular erróneamente datos (por ejemplo si el contenido
    # ya estaba en favoritos y quiere añadirla a vistos, no cambiar el booleano de vistos, sino solamente el de favoritos)

    favorita = db.session.query(UsuarioContenido).filter_by(
        id_usuario = current_user.id,
        id_contenido = int(id)
    ).first()

    if favorita: # Si ya existe una relación contenido/usuario:

        favorita.favorita = True

    else:

        favorita = UsuarioContenido(
            id_usuario = current_user.id,
            id_contenido = int(id), # Parámetro recibido por ruta
            vista = False,
            favorita = True
        )
        db.session.add(favorita)

    db.session.commit()

    return redirect(request.referrer)  # Redirijo a la página anterior


@app.route('/añadir-vistas/<id>')
@login_required
def aniadir_vistas(id):

    # Compruebo si el usuario tiene el contenido en vistos o favoritos

    vista = db.session.query(UsuarioContenido).filter_by(
        id_usuario=current_user.id,
        id_contenido=int(id)
    ).first()

    if vista: # Si ya existe una relación contenido/usuario:

        vista.vista = True

    else:

        vista = UsuarioContenido(
            id_usuario=current_user.id,
            id_contenido=int(id),  # Parámetro recibido por ruta
            vista=True,
            favorita=False
        )
        db.session.add(vista)

    db.session.commit()

    return redirect(request.referrer)  # Redirijo a la página anterior


@app.route('/quitar-favoritas/<id>')
@login_required
def quitar_favoritas(id):

    # Compruebo si el usuario tiene el mismo contenido en vistos, si es así, solamente cambio el valor del booleano de 'favorita'
    # de no ser así elimino el elemento de la tabla

    favorita = db.session.query(UsuarioContenido).filter_by(
        id_usuario=current_user.id,
        id_contenido=int(id)
    ).first()

    es_vista = db.session.query(UsuarioContenido).filter_by(
        id_usuario=current_user.id,
        id_contenido=int(id),
        vista=True
    ).first()

    if es_vista: # Si ya existe una relación contenido/usuario:

        favorita.favorita = False # Si también tiene el contenido en 'vistas' solamente cambio el booleano de favorita a False

    else:

        db.session.delete(favorita) # Si el contenido tiene los dos valores (vista & favorita) en False, elimino la instancia de la tabla

    db.session.commit()

    return redirect(request.referrer)  # Redirijo a la página anterior


@app.route('/quitar-vistas/<id>')
@login_required
def quitar_vistas(id):

    # Compruebo si el usuario tiene el mismo contenido en favoritos, si es así, solamente cambio el valor del booleano de 'vista'
    # de no ser así elimino el elemento de la tabla

    vista = db.session.query(UsuarioContenido).filter_by(
        id_usuario=current_user.id,
        id_contenido=int(id)
    ).first()

    es_favorita = db.session.query(UsuarioContenido).filter_by(
        id_usuario=current_user.id,
        id_contenido=int(id),
        favorita=True
    ).first()

    if es_favorita:  # Si ya existe una relación contenido/usuario:

        vista.vista = False  # Si también tiene el contenido en 'favoritas' solamente cambio el booleano de vista a False

    else:

        db.session.delete(vista)  # Si el contenido tiene los dos valores (vista & favorita) en False, elimino la instancia de la tabla

    db.session.commit()

    return redirect(request.referrer)  # Redirijo a la página anterior


@app.route('/modo-edit')
@login_required
def editar():
    return render_template('administrador.html')


@app.route('/modo-edit-usuarios')
@login_required
def edit_usuario():

    lista_usuarios = db.session.query(Usuarios).filter_by(es_admin=False).all() # Listo los usuarios que NO son administradores

    return render_template('usuarios.html', lista=lista_usuarios)


@app.route('/modo-edit-usuario-crear/', methods=['GET','POST'])
@login_required
def crear_usuario():

    if request.method == 'POST':

        campos = list(request.form.values())  # Lista de todos los elementos enviados

        try:

            if any(not campo for campo in campos):  # Comprueba si hay algún elemento vacío
                raise ValueError('Todos los campos deben ser completados')

            if db.session.query(Usuarios).filter(
                    Usuarios.correo == request.form['correo']).first():  # Comprueba si el correo introducido ya existe
                raise ValueError('Este correo ya existe')

            contra = request.form['contrasena'] # Hasheo la contraseña
            contra_hasheada = generate_password_hash(contra, method='pbkdf2:sha256:600000', salt_length=16)

            cuenta = Usuarios(
                nombre=request.form['nombre'],
                apellidos=request.form['apellidos'],
                usuario=request.form['usuario'],
                correo=request.form['correo'],
                contrasena=contra_hasheada,
                es_admin=False
            )

            db.session.add(cuenta)  # Añado los datos a la DB
            db.session.commit()


        except ValueError as e:

            # Capturar errores específicos y pasar el mensaje a la plantilla

            return render_template('usuarios.html', error_message=e)


        except Exception as e:

            # Capturar errores generales y pasar el mensaje a la plantilla

            return render_template('usuarios.html',
                                   error_message="Ha ocurrido un error inesperado. Inténtalo de nuevo más tarde.")

        return redirect(request.referrer)  # Redirijo a la página anterior


@app.route('/modo-edit-usuario-editar/<id>', methods=['GET','POST'])
@login_required
def editar_usuario(id):

    if request.method == 'POST':

        campos = list(request.form.values())  # Lista de todos los elementos enviados
        usuario = db.session.query(Usuarios).filter(Usuarios.id==id).first() # Busco la instancia del usuario el cual quiero editar con el id recibido
        atributos = [columna.name for columna in Usuarios.__table__.columns] # Creo una lista con los atributos de la tabla Usuarios

        for atributo,campo in zip(atributos[1:],campos): # Recorro las dos listas a la vez
            if campo: # Si el campo de texto no está vacío sobreescribo el valor del atributo
                if atributo == 'correo' and db.session.query(Usuarios).filter(
                    Usuarios.correo == campo).first():
                    flash('El correo introducido ya existe')
                else:
                    setattr(usuario,atributo,campo) # Asigno los valores de los atributos dinámicamente con 'setattr(objeto,atributo,valor)'

        db.session.commit()

    return redirect(url_for('edit_usuario'))


@app.route('/modo-edit-usuario-eliminar/<id>')
@login_required
def eliminar_usuario(id):

    usuario = db.session.query(Usuarios).filter(Usuarios.id == int(id)).first() # Capturo el usuario
    contenido_usuario = db.session.query(UsuarioContenido).filter_by(id_usuario = id).all() # También miro si tiene contenido en vistos o favoritos

    db.session.delete(usuario) # Elimino el usuario
    if contenido_usuario: # Si existe algún registro del usuario
        for registro in contenido_usuario: # Recorro las instancias capturadas
            db.session.delete(registro) # Elimino los vistos y favoritos del usuario

    db.session.commit() # Guardo los cambios

    return redirect(request.referrer)  # Redirijo a la página anterior


@app.route('/modo-edit-contenido')
@login_required
def edit_contenido():

    lista_contenido = db.session.query(Contenido).all()

    return render_template('contenido.html', lista=lista_contenido)


@app.route('/modo-edit-contenido-crear/', methods=['GET','POST'])
@login_required
def crear_contenido():

    if request.method == 'POST':

        campos = list(request.form.values())  # Lista de todos los elementos enviados

        # Guardo el archivo de la portada en la variable 'file'
        file = request.files.get('portada')
        if file and validacion_archivo(file.filename): # Valido el archivo (si la extensión es buena)
            # Guardo el nombre del archivo para posteriormente crear la ruta
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)  # Guardo la imagen en la carpeta especificada
        else:
            flash('Error al subir la imagen. Asegúrate de que sea un archivo .jpg.')
            return redirect(request.referrer)  # Redirijo a la página anterior

        try:

            if any(not campo for campo in campos):  # Comprueba si hay algún elemento vacío
                raise ValueError('Todos los campos deben ser completados')

            # Comprueba si el contenido introducido ya existe (si coincide título + director + año de lanzamiento)
            if db.session.query(Contenido).filter_by(
                titulo=request.form['titulo'],
                lanzamiento=request.form['lanzamiento'],
                director=request.form['director']
            ).first():
                raise ValueError('Ya existe')

            # Si es una Serie y coinciden el número de temporadas con los elementos de la lista 'capítulos por temporada' o es una Película
            # p.ej. nTemporadas = 5 & capitulosTemporada = [4,4,4,6,6] -> True | nTemporadas = 3 & capitulosTemporada = [2,4] -> False

            if (request.form['tipo'] == 'Serie' and len(request.form['capitulosTemporada'].strip('[]').split(',')) == int(request.form['nTemporadas'])) or request.form['tipo'] == 'Película':
                if request.form['tipo'] == 'Serie': # Este cálculo solo es necesario hacerlo si el contenido es una serie
                    # Hago un sumatorio de todos los capitulates por temporada para calcular los capitulates totales
                    # Como los elementos de la lista son de tipo str y la función sum() trabaja con tipos int lo que hago es
                    # recorrer los elementos de la lista y convertirlos en tipo integer con la función int()
                    capitulosTotales = sum(int(x) for x in request.form['capitulosTemporada'].strip('[]').split(','))

                contenido = Contenido(
                    titulo=request.form['titulo'],
                    # Si en el selector de tipo seleccionan 'Película' asigno un 0 a la variable (ya que es un booleano) de lo contrario un 1 (si es una serie)
                    tipo=0 if request.form['tipo']=='Película' else 1,
                    duracion=request.form['duracion'],
                    lanzamiento=request.form['lanzamiento'],
                    director=request.form['director'],
                    genero=request.form['genero'],
                    sinopsis=request.form['sinopsis'],
                    # Si se trata de una película asigno automáticamente el valor de '1' temporadas, capítulos (totales) y capítulos por temporada
                    nTemporadas=request.form['nTemporadas'] if request.form['tipo']=='Serie' else 1,
                    nCapitulos=capitulosTotales if request.form['tipo']=='Serie' else 1,
                    capitulosTemporada=request.form['capitulosTemporada'] if request.form['tipo']=='Serie' else '[1]',
                    portada= filepath # Ruta de la portada
                )

                db.session.add(contenido)  # Añado los datos a la DB
                db.session.commit() # Guardo los cambios

                # Aquí puedes guardar los datos en la base de datos o realizar más acciones
                flash(f'Contenido "{contenido.titulo}" creado con éxito.')

            else:
                flash('Asegúrate de que coincidan el número de temporadas con el número de elementos de la lista "capítulos por temporada" o introducirlo en el formato especificado.')

        except ValueError as e:

            # Capturar errores específicos y pasar el mensaje a la plantilla

            return render_template('contenido.html', error_message=e)

        except Exception as e:

            # Capturar errores generales y pasar el mensaje a la plantilla

            return render_template('contenido.html',
                                   error_message="Ha ocurrido un error inesperado. Inténtalo de nuevo más tarde.")

        return redirect(request.referrer)  # Redirijo a la página anterior


@app.route('/modo-edit-contenido-editar/<id>', methods=['GET','POST'])
@login_required
def editar_contenido(id):

    contenido = db.session.query(Contenido).filter(Contenido.id==id).first() # Busco la instancia del contenido el cual quiero editar con el id recibido

    # Guardo el archivo de la portada en la variable 'file'
    file = request.files.get('portada')
    if file:  # Si se ha cargado un archivo:
        if validacion_archivo(file.filename):  # Valido el archivo (si la extensión es buena)
            # Guardo el nombre del archivo para posteriormente crear la ruta
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)  # Guardo la imagen en la carpeta especificada

            # Borro el archivo anterior de la carpeta y actualizo la ruta de la portada
            os.remove(contenido.portada) # Elimino
            setattr(contenido,'portada',filepath) # Actualizo


        else:
            flash('Error al subir la imagen. Asegúrate de que sea un archivo .jpg.')
            return redirect(request.referrer)  # Redirijo a la página anterior

    # Con una sentencia if diferencio el tipo de contenido para así permitir o no que el administrador pueda editar el número de temporadas y capítulos por temporada
    if contenido.tipo:
        if request.form['titulo']:
            setattr(contenido,'titulo', request.form['titulo'])
        if request.form['duracion']:
            setattr(contenido,'duracion', request.form['duracion'])
        if request.form['lanzamiento']:
            setattr(contenido,'lanzamiento', request.form['lanzamiento'])
        if request.form['director']:
            setattr(contenido,'director', request.form['director'])
        if request.form['genero']:
            setattr(contenido,'genero', request.form['genero'])
        if request.form['sinopsis']:
            setattr(contenido,'sinopsis', request.form['sinopsis'])

        # No se puede cambiar solo uno de estos dos campos, ya que implicaría una contradicción
        if request.form['nTemporadas'] and request.form['capitulosTemporada']:

            # Compruebo si coinciden el número de temporadas con el número de elementos de la lista 'capitulosTemporada'
            if len(request.form['capitulosTemporada'].strip('[]').split(',')) == int(request.form['nTemporadas']):
                sumaCapitulosTotales = sum(int(x) for x in request.form['capitulosTemporada'].strip('[]').split(','))
                setattr(contenido,'capitulosTotales',sumaCapitulosTotales)
                setattr(contenido,'nTemporadas', request.form['nTemporadas'])
                setattr(contenido,'capitulosTemporada', request.form['capitulosTemporada'])

            else:
                flash('Asegúrate de que coincidan el número de temporadas con el número de elementos de la lista "capítulos por temporada" o introducirlo en el formato especificado.')

    else:
        if request.form['titulo']:
            setattr(contenido, 'titulo', request.form['titulo'])
        if request.form['duracion']:
            setattr(contenido, 'duracion', request.form['duracion'])
        if request.form['lanzamiento']:
            setattr(contenido, 'lanzamiento', request.form['lanzamiento'])
        if request.form['director']:
            setattr(contenido, 'director', request.form['director'])
        if request.form['genero']:
            setattr(contenido, 'genero', request.form['genero'])
        if request.form['sinopsis']:
            setattr(contenido, 'sinopsis', request.form['sinopsis'])


    db.session.commit() # Guardo los cambios

    return redirect(url_for('edit_contenido'))


@app.route('/modo-edit-contenido-eliminar/<id>')
@login_required
def eliminar_contenido(id):

    contenido = db.session.query(Contenido).filter(Contenido.id == int(id)).first() # Capturo el contenido
    contenido_usuario = db.session.query(UsuarioContenido).filter_by(
        id_contenido=id).all()  # También miro si tiene contenido en vistos o favoritos

    db.session.delete(contenido) # Elimino el contenido
    if contenido_usuario:  # Si existe algún registro que implique al contenido en cuestión
        for registro in contenido_usuario:  # Recorro las instancias capturadas
            db.session.delete(registro)  # Elimino los vistos y favoritos relacionados

    db.session.commit()  # Guardo los cambios

    return redirect(request.referrer)  # Redirijo a la página anterior


@app.route('/buscar-modo-admin/<pagina>', methods=['GET','POST'])
@login_required
def buscar_modo_admin(pagina):

    if request.method == 'POST':

        busqueda = request.form['busqueda']
        coincidencias = []

        if pagina == 'contenido':
            contenido = db.session.query(Contenido).all()
            for item in contenido:
                # SQLalchemy devuelve una lista de tuplas asi que tengo que indicar el índice [0] para trabajar con el contenido limpio
                if busqueda.lower() in item.titulo.lower(): # Para mejorar el rango de la búsqueda paso las dos cadenas a minúsculas
                    coincidencias.append(item)

            return render_template('contenido.html', busqueda = coincidencias)

        elif pagina == 'usuarios':
            usuarios = db.session.query(Usuarios).filter_by(es_admin=False).all()
            for usuario in usuarios:
                if busqueda in usuario.usuario:
                    coincidencias.append(usuario)

            return render_template('usuarios.html', busqueda = coincidencias  )

        else:
            flash('Ha ocurrido un error, inténtalo de nuevo.')

        return redirect(request.referrer)


@app.route('/buscar-catalogo', methods=['GET','POST'])
@login_required
def buscar_catalogo():

    # Obtengo el texto del formulario en minúsculas y borrando posibles espacios
    busqueda = request.form.get('busqueda', '').strip().lower()

    # Obtengo el tipo de contenido actual que se está mostrando
    #  (por ejemplo: 'película', 'serie', 'favorita' o 'vista')
    tipo = request.form.get('tipo')

    # Si el campo "busqueda" está vacío, avisamos y volvemos a la página anterior
    if not busqueda:
        flash("Por favor, introduce algún texto para buscar.")
        return redirect(request.referrer or url_for('peliculas'))

    # Creo la lista donde guardaremos las coincidencias
    coincidencias = []

    # Filtro según el tipo de contenido que estamos mostrando
    # (cada caso corresponde a la sección donde estaba el usuario)

    if tipo == 'película':
        # Obtengo todas las películas de la BD
        peliculas = db.session.query(Contenido).filter(Contenido.tipo == False).all()

        # Filtro la búsqueda del usuario
        coincidencias = [p for p in peliculas if busqueda in p.titulo.lower()]

        # Renderizo el template de catálogo, indicando que el tipo es 'película'
        return render_template('catalogo.html',
                               tipo='película',
                               lista_contenido=coincidencias)

    elif tipo == 'serie':
        # Consulto la base de datos para obtener todas las series
        series = db.session.query(Contenido).filter(Contenido.tipo == True).all()

        # Filtro por título
        coincidencias = [s for s in series if busqueda in s.titulo.lower()]

        # Devuelvo el render al mismo 'catalogo.html', indicando tipo 'serie'
        return render_template('catalogo.html',
                               tipo='serie',
                               lista_contenido=coincidencias)

    elif tipo == 'favorita':

        # Recupero la lista de ids de la sesión
        lista_ids = session.get('lista_favoritas', [])

        # Filtro la lista en la db
        favoritos = (db.session.query(Contenido)
                     .filter(Contenido.id.in_(lista_ids))
                     .all())

        # Filtro por el título
        resultados = [f for f in favoritos if busqueda in f.titulo.lower()]

        return render_template('catalogo.html',
                               tipo='favorita',
                               lista_contenido=resultados)

    elif tipo == 'vista':

        # Recupero la lista de ids de la sesión
        lista_ids = session.get('lista_vistas', [])

        # Filtro la lista en la db
        vistos = (db.session.query(Contenido)
                     .filter(Contenido.id.in_(lista_ids))
                     .all())

        # Filtro por el título
        resultados = [f for f in vistos if busqueda in f.titulo.lower()]

        return render_template('catalogo.html',
                               tipo='vista',
                               lista_contenido=resultados)

    else:
        flash("No se ha reconocido el tipo de contenido para realizar la búsqueda.")
        return redirect(request.referrer)


@app.route('/mi-actividad')
@login_required
def estadisticas_cliente():

    try:
        n_contenido = db.session.query(Contenido).count()  # Número total de contenido
        n_vistas_totales = db.session.query(UsuarioContenido).filter_by(
            id_usuario=current_user.id,
            vista=True).count()  # Número de películas y series vistas

        # A continuación, uso dos métodos distintos para obtener el número de películas y series vistas por el usuario actual.
        # La primera consulta usa .count(), mientras que la segunda usa func.count().scalar() para mayor eficiencia.

        # 1. Número de películas vistas por el usuario
        # Se usa .join() para unir Contenido con UsuarioContenido y así acceder a ambas tablas en una sola consulta.
        #  Sin embargo, .count() puede generar una consulta SQL menos eficiente, ya que SQLAlchemy podría crear una subconsulta interna.
        n_peliculas_vistas = db.session.query(Contenido).join(
            UsuarioContenido,
            Contenido.id == UsuarioContenido.id_contenido).filter(
            UsuarioContenido.id_usuario == current_user.id,
            UsuarioContenido.vista == True,  # Está marcada como vista
            Contenido.tipo == False  # Es tipo película
        ).count()

        # 2. Número de series vistas por el usuario
        # Se usa func.count() para contar los registros directamente en la base de datos, sin necesidad de recuperar objetos en memoria.
        # Esto genera una consulta SQL más optimizada con COUNT(*), lo que la hace más eficiente que .count().
        n_series_vistas = db.session.query(func.count(Contenido.id)).join(
            UsuarioContenido,
            Contenido.id == UsuarioContenido.id_contenido).filter(
            UsuarioContenido.id_usuario == current_user.id,
            UsuarioContenido.vista == True,  # Está marcada como vista
            Contenido.tipo == True  # Es tipo serie
        ).scalar()  # scalar() obtiene el valor numérico directamente, sin envolverlo en una tupla

        # 3. Cantidad de tiempo invertido en ver Películas
        tiempo_peliculas = (db.session.query(func.sum(Contenido.duracion)).join(
            UsuarioContenido,
            Contenido.id == UsuarioContenido.id_contenido).filter(
            UsuarioContenido.id_usuario == current_user.id,
            UsuarioContenido.vista == True,  # Está marcada como vista
            Contenido.tipo == False  # Es tipo película
        ).scalar()) / 60 # Divido entre 60 para mostrarlo en horas y no en minutos

        # 4. Tiempo invertido en ver Series
        # Multiplico la duración media por capítulo por el número de capítulos
        tiempo_series = (db.session.query(func.sum(Contenido.duracion * Contenido.nCapitulos)).join(
            UsuarioContenido,
            Contenido.id == UsuarioContenido.id_contenido).filter(
            UsuarioContenido.id_usuario == current_user.id,
            UsuarioContenido.vista == True,  # Está marcada como vista
            Contenido.tipo == True  # Es tipo serie
        ).scalar()) / 60 # Divido entre 60 para mostrarlo en horas y no en minutos

        # Tiempo total invertido en ver el contendido de la plataforma
        tiempo_total = tiempo_series + tiempo_peliculas

        # -------------------------------------------------------------------------------------------------------------------------------
        #                                                    GRÁFICA nº1 - contenido visto
        # -------------------------------------------------------------------------------------------------------------------------------
        # Primero de todo creo el DataFrame con los datos registrados previamente con el método pd.DataFrame()
        df = pd.DataFrame({
            'Categoría': ['Películas', 'Series', 'Total'],  # Etiquetas para el eje X
            'Valor': [n_peliculas_vistas, n_series_vistas, n_vistas_totales]  # Valores para el eje Y
        })

        # Configuro el estilo de Seaborn
        sns.set_theme(style="darkgrid")
        plt.style.use("dark_background")

        # Creo el gráfico de barras
        plt.figure(figsize=(10, 6))  # Tamaño del gráfico
        ax = sns.barplot(data=df, x='Categoría', y='Valor', palette="Reds")

        # Personalizo el gráfico
        plt.ylim(0, n_contenido)  # Límite del eje Y hasta el nº de elementos de la tabla Contenido
        plt.xlabel("")  # Quitar etiqueta del eje X
        plt.ylabel("")  # Etiqueta para el eje Y
        plt.title("Películas y series vistas")  # Título del gráfico

        # Cambio el color de los ejes
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.tick_params(colors='white')

        grafica_1_io = io.BytesIO() # Creo un buffer (espacio de memoria temporal)
        plt.savefig(grafica_1_io, format='png', dpi=100, bbox_inches='tight') # Guardo la imagen de la gráfica en el buffer
        # Especifico el formato 'png', resolución y ajusto los márgenes
        plt.close() # Cierro la figura de Matplotlib para liberar memoria
        grafica_1_io.seek(0) # Muevo el puntero al inicio del archivo

        grafica_1_64 = base64.b64encode(grafica_1_io.getvalue()).decode('utf-8') # Convierto la imagen en un string
        # base64.b64encode() convierte de binario (bytes) a Base64, pero en formato de bytes (b'')
        # y con .decode('utf-8') lo que estoy haciendo es transformar de bytes a texto legible (ya que HTML no puede manejar binarios)

        # -------------------------------------------------------------------------------------------------------------------------------
        #                                                    GRÁFICA nº2 - tiempo de actividad
        # -------------------------------------------------------------------------------------------------------------------------------
        # Primero de todo creo el DataFrame con los datos registrados previamente con el método pd.DataFrame()
        df = pd.DataFrame({
            'Categoría': ['Películas', 'Series', 'Total'],  # Etiquetas para el eje X
            'Valor': [tiempo_peliculas, tiempo_series, tiempo_total]  # Valores para el eje Y
        })

        # Configuro el estilo de Seaborn
        sns.set_theme(style="darkgrid")
        plt.style.use("dark_background")

        # Creo el gráfico de barras
        plt.figure(figsize=(10, 6))  # Tamaño del gráfico
        ax = sns.barplot(data=df, x='Categoría', y='Valor', palette="Reds")

        # Personalizo el gráfico
        plt.ylim(0, math.ceil(tiempo_total / 100)*100)  # Límite del eje Y es el tiempo total
        # La intención és que el límite del eje varíe según el tiempo invertido para mejor visualización de la gráfica
        # y para no poner como límite el tiempo total, lo que hago es redondearlo a la siguiente cifra multiple de 100
        plt.xlabel("")  # Quitar etiqueta del eje X
        plt.ylabel("")  # Etiqueta para el eje Y
        plt.title("Tiempo dedicado a ver películas y series (en horas)")  # Título del gráfico

        # Cambio el color de los ejes
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.tick_params(colors='white')

        grafica_2_io = io.BytesIO()  # Creo un buffer (espacio de memoria temporal)
        plt.savefig(grafica_2_io, format='png', dpi=100, bbox_inches='tight')  # Guardo la imagen de la gráfica en el buffer
        # Especifico el formato 'png', resolución y ajusto los márgenes
        plt.close()  # Cierro la figura de Matplotlib para liberar memoria
        grafica_2_io.seek(0)  # Muevo el puntero al inicio del archivo

        grafica_2_64 = base64.b64encode(grafica_2_io.getvalue()).decode('utf-8')  # Convierto la imagen en un string


        return render_template(
            'mi_actividad.html',
            grafica_1 = grafica_1_64,
            grafica_2 = grafica_2_64
        ) # Renderizo la pantalla y envío las gráficas

    except TypeError:

        return render_template('mi_actividad.html', mensaje_error = 'No hay suficientes datos para generar las gráficas.')


@app.route('/estadísticas')
@login_required
def estadisticas_administrador():

    try:
        # -------------------------------------------------------------------------------------------------------------------------------
        #                                                    CONSULTAS A LA DB
        # -------------------------------------------------------------------------------------------------------------------------------

        top_5_usuarios = db.session.query(
            Usuarios.usuario,  # Nombre del usuario
            (func.sum(Contenido.duracion * Contenido.nCapitulos # Calculo el tiempo total invertido
            ) / 60).label("tiempo_invertido")  # Convierto a horas
        ).join(
            UsuarioContenido, Usuarios.id == UsuarioContenido.id_usuario # Relaciono las tablas
        ).join(
            Contenido, UsuarioContenido.id_contenido == Contenido.id # Relaciono las tablas
        ).filter(
            UsuarioContenido.vista == True  # Solo incluye contenidos vistos
        ).group_by(
            Usuarios.id  # Agrupo por usuario
        ).order_by(
            desc("tiempo_invertido")  # Ordeno en orden descendente
        ).limit(5).all()  # Solo los 5 primeros

        top_5_peliculas = db.session.query(
            Contenido.titulo,
            func.count(UsuarioContenido.id_contenido).label('reproducciones')
        ).join(
            UsuarioContenido,
            Contenido.id == UsuarioContenido.id_contenido
        ).filter(
            UsuarioContenido.vista == True, # Solo incluye contenidos vistos
            Contenido.tipo == False # Solo incluye películas
        ).group_by(
            Contenido.id
        ).order_by(
            desc('reproducciones')
        ).limit(5).all()

        top_5_series = db.session.query(
            Contenido.titulo,
            func.count(UsuarioContenido.id_contenido).label('reproducciones')
        ).join(
            UsuarioContenido,
            Contenido.id == UsuarioContenido.id_contenido
        ).filter(
            UsuarioContenido.vista == True, # Solo incluye contenidos vistos
            Contenido.tipo == True # Solo incluye series
        ).group_by(
            Contenido.id
        ).order_by(
            desc('reproducciones')
        ).limit(5).all()

        # Si no hay datos envio un 'ValueError' que voy a capturar más adelante para mostrar un mensaje por pantalla
        if not top_5_peliculas or not top_5_series or not top_5_usuarios:
            raise ValueError

        tiempo_usuario_mas_activo = top_5_usuarios[0][1]

        # -------------------------------------------------------------------------------------------------------------------------------
        #                                                    GRÁFICA nº1 - actividad
        # -------------------------------------------------------------------------------------------------------------------------------
        # Primero de todo creo el DataFrame con los datos registrados previamente con el método pd.DataFrame()
        df = pd.DataFrame({
            'Categoría': [usuario[0] for usuario in top_5_usuarios],  # Etiquetas para el eje X
            'Valor': [usuario[1] for usuario in top_5_usuarios]  # Valores para el eje Y
        })

        # Configuro el estilo de Seaborn
        sns.set_theme(style="darkgrid")
        plt.style.use("dark_background")

        # Creo el gráfico de barras
        plt.figure(figsize=(10, 6))  # Tamaño del gráfico
        ax = sns.barplot(data=df, x='Categoría', y='Valor', palette="Reds")

        # Personalizo el gráfico
        plt.ylim(0, tiempo_usuario_mas_activo)  # Límite del eje Y
        plt.xlabel("USUARIOS")  # Quitar etiqueta del eje X
        plt.ylabel("TIEMPO (EN HORAS)")  # Etiqueta para el eje Y
        plt.title("USUARIOS MÁS ACTIVOS")  # Título del gráfico
        plt.xticks(rotation=45, ha="right")  # Alineo las etiquetas 45 grados para que no se solapen

        # Cambio el color de los ejes
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.tick_params(colors='white')

        grafica_usuarios_io = io.BytesIO()  # Creo un buffer (espacio de memoria temporal)
        plt.savefig(grafica_usuarios_io, format='png', dpi=100,
                    bbox_inches='tight')  # Guardo la imagen de la gráfica en el buffer
        # Especifico el formato 'png', resolución y ajusto los márgenes
        plt.close()  # Cierro la figura de Matplotlib para liberar memoria
        grafica_usuarios_io.seek(0)  # Muevo el puntero al inicio del archivo

        grafica_usuarios_64 = base64.b64encode(grafica_usuarios_io.getvalue()).decode(
            'utf-8')  # Convierto la imagen en un string
        # base64.b64encode() convierte de binario (bytes) a Base64, pero en formato de bytes (b'')
        # y con .decode('utf-8') lo que estoy haciendo es transformar de bytes a texto legible (ya que HTML no puede manejar binarios)

        top_repeticiones_peliculas = top_5_peliculas[0][1]

        # -------------------------------------------------------------------------------------------------------------------------------
        #                                                    GRÁFICA nº2 - tendencia películas
        # -------------------------------------------------------------------------------------------------------------------------------
        # Primero de todo creo el DataFrame con los datos registrados previamente con el método pd.DataFrame()
        df = pd.DataFrame({
            'Categoría': [pelicula[0] for pelicula in top_5_peliculas],  # Etiquetas para el eje X
            'Valor': [pelicula[1] for pelicula in top_5_peliculas]  # Valores para el eje Y
        })

        # Configuro el estilo de Seaborn
        sns.set_theme(style="darkgrid")
        plt.style.use("dark_background")

        # Creo el gráfico de barras
        plt.figure(figsize=(10, 6))  # Tamaño del gráfico
        ax = sns.barplot(data=df, x='Categoría', y='Valor', palette="Reds")

        # Personalizo el gráfico
        plt.ylim(0, top_repeticiones_peliculas)  # Límite del eje Y
        plt.xlabel("TÍTULO")  # Quitar etiqueta del eje X
        plt.ylabel("REPETICIONES")  # Etiqueta para el eje Y
        plt.title("TOP 5 PELÍCULAS")  # Título del gráfico
        plt.xticks(rotation=45, ha="right")  # Alineo las etiquetas 45 grados para que no se solapen

        # Cambio el color de los ejes
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.tick_params(colors='white')

        grafica_peliculas_io = io.BytesIO()  # Creo un buffer (espacio de memoria temporal)
        plt.savefig(grafica_peliculas_io, format='png', dpi=100,
                    bbox_inches='tight')  # Guardo la imagen de la gráfica en el buffer
        # Especifico el formato 'png', resolución y ajusto los márgenes
        plt.close()  # Cierro la figura de Matplotlib para liberar memoria
        grafica_peliculas_io.seek(0)  # Muevo el puntero al inicio del archivo

        grafica_peliculas_64 = base64.b64encode(grafica_peliculas_io.getvalue()).decode(
            'utf-8')  # Convierto la imagen en un string
        # base64.b64encode() convierte de binario (bytes) a Base64, pero en formato de bytes (b'')
        # y con .decode('utf-8') lo que estoy haciendo es transformar de bytes a texto legible (ya que HTML no puede manejar binarios)

        top_repeticiones_series = top_5_series[0][1]

        # -------------------------------------------------------------------------------------------------------------------------------
        #                                                    GRÁFICA nº3 - tendencia series
        # -------------------------------------------------------------------------------------------------------------------------------
        # Primero de todo creo el DataFrame con los datos registrados previamente con el método pd.DataFrame()
        df = pd.DataFrame({
            'Categoría': [serie[0] for serie in top_5_series],  # Etiquetas para el eje X
            'Valor': [serie[1] for serie in top_5_series]  # Valores para el eje Y
        })

        # Configuro el estilo de Seaborn
        sns.set_theme(style="darkgrid")
        plt.style.use("dark_background")

        # Creo el gráfico de barras
        plt.figure(figsize=(10, 6))  # Tamaño del gráfico
        ax = sns.barplot(data=df, x='Categoría', y='Valor', palette="Reds")

        # Personalizo el gráfico
        plt.ylim(0, top_repeticiones_series)  # Límite del eje Y
        plt.xlabel("TÍTULO")  # Quitar etiqueta del eje X
        plt.ylabel("REPETICIONES")  # Etiqueta para el eje Y
        plt.title("TOP 5 SERIES")  # Título del gráfico
        plt.xticks(rotation=45, ha="right") # Alineo las etiquetas 45 grados para que no se solapen

        # Cambio el color de los ejes
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.tick_params(colors='white')

        grafica_series_io = io.BytesIO()  # Creo un buffer (espacio de memoria temporal)
        plt.savefig(grafica_series_io, format='png', dpi=100,
                    bbox_inches='tight')  # Guardo la imagen de la gráfica en el buffer
        # Especifico el formato 'png', resolución y ajusto los márgenes
        plt.close()  # Cierro la figura de Matplotlib para liberar memoria
        grafica_series_io.seek(0)  # Muevo el puntero al inicio del archivo

        grafica_series_64 = base64.b64encode(grafica_series_io.getvalue()).decode(
            'utf-8')  # Convierto la imagen en un string
        # base64.b64encode() convierte de binario (bytes) a Base64, pero en formato de bytes (b'')
        # y con .decode('utf-8') lo que estoy haciendo es transformar de bytes a texto legible (ya que HTML no puede manejar binarios)


        return render_template(
            'estadisticas.html',
            grafica_usuarios = grafica_usuarios_64,
            grafica_peliculas = grafica_peliculas_64,
            grafica_series = grafica_series_64
        ) # Renderizo la pantalla y envío las gráficas

    except TypeError:

        return render_template('estadisticas.html', mensaje_error='No hay suficientes datos para generar las gráficas.')

    except ValueError:

        return render_template('estadisticas.html', mensaje_error='No hay suficientes datos para generar las gráficas.')


def crear_cuenta_admin():

    '''
    Aquí voy a crear (si no está ya creada) la cuenta del administrador
    '''

    nombre = 'Administrador'
    apellidos = '-'
    usuario = 'Admin'
    correo = 'admin@admin.com'
    contrasena = generate_password_hash('AdminIstradoR123', method='pbkdf2:sha256:600000', salt_length=16)

    todos_los_usuarios = db.session.query(Usuarios).all() # Consulto y almaceno todas las cuentas para el inicio de sesión
    lista_correos = [] # Creo una lista donde voy a añadir todos los correos creados (ya que el correo es lo único irrepetible de una cuenta)
    for usuario in todos_los_usuarios:
        lista_correos.append(usuario.correo)

    if correo not in lista_correos:
        cuenta_admin = Usuarios(
            nombre=nombre,
            apellidos=apellidos,
            usuario=usuario,
            correo=correo,
            contrasena=contrasena,
            es_admin=True
        )

        db.session.add(cuenta_admin)  # Añado los datos a la DB
        db.session.commit()

def catalogo():

    # Primero extraigo los títulos de las películas/series que pueda haber ya en la db para que no se repitan

    titulos = db.session.query(Contenido.titulo).all()

    lista_titulos = [titulo for tupla in titulos for titulo in tupla] # Ya que la db me envia una lista de tuplas

    # Cargo un archivo json que contiene el catálogo
    with open('data/contenido.json','r',encoding='utf-8') as archivo:
        datos = json.load(archivo)

    # Si no existe ya la película en la DB la añado (para que no se añada todo el catálogo cada vez que ejecuto el programa)
    for dato in datos:
        if dato['titulo'] not in lista_titulos:
            catalogoPeliSerie = Contenido(
                titulo=dato['titulo'],
                tipo=dato['tipo'],
                duracion=dato['duracion'],
                lanzamiento=dato['lanzamiento'],
                director=dato['director'],
                genero=dato['genero'],
                sinopsis=dato['sinopsis'],
                nTemporadas=dato.get('nTemporadas', 1),
                nCapitulos=dato.get('nCapitulos', 1), # Si no es una serie, introduzco un 1 para evitar valores nulos
                capitulosTemporada=str(dato.get('capitulosTemporada', [1])),
                portada=('static/recursos/portadas/' + dato['titulo'] + '.jpg')
            )
            db.session.add(catalogoPeliSerie)

    db.session.commit()


# Esta función me devuelve un booleano
def validacion_archivo(archivo):
    # Primero miro si el nombre del archivo contiene un punto '.'
    # Después divido el nombre en dos; antes y después del punto mediante rsplit(), por ejemplo 'imagen.jpg' -> ['imagen','jpg']
    # y compruebo si la segunda parte ([1], la cual va a ser la extension 'jpg') está dentro de las extensiones válidas configuradas previamente
    return '.' in archivo and archivo.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']


if __name__ == "__main__":
    db.Base.metadata.create_all(bind=db.engine)  # Creamos las tablas del modelo de datos

    crear_cuenta_admin() # Creo la cuenta del administrador
    catalogo() # Añado el catálogo del json

    app.run(debug=True)  # Iniciamos el servidor Flask * después de cargar los datos a la db

