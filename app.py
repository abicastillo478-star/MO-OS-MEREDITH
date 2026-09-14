from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
import json
import os
import shutil
from pathlib import Path
from config import WHATSAPP
from functools import wraps

app = Flask(__name__)
app.secret_key = "CAMBIA-ESTA-CLAVE"
USUARIO_ADMIN = "admin"
CONTRASENA_ADMIN = "angelcruel"
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

BASE_DIR = Path(__file__).resolve().parent

# Render's normal filesystem is temporary. This app is configured to use
# /var/data when a Render Persistent Disk is attached there.
# Locally, it falls back to a data/ folder inside the project.
PERSISTENT_DIR = Path(os.environ.get("MONOS_DATA_DIR", "/var/data"))
if not PERSISTENT_DIR.exists():
    PERSISTENT_DIR = BASE_DIR / "data"
PERSISTENT_DIR.mkdir(parents=True, exist_ok=True)

DATA = PERSISTENT_DIR / "productos.json"
UPLOADS = PERSISTENT_DIR / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)

BUNDLED_DATA = BASE_DIR / "productos.json"
BUNDLED_UPLOADS = BASE_DIR / "static" / "uploads"
ALLOWED = {"png", "jpg", "jpeg", "webp", "gif"}


def inicializar_almacenamiento():
    """Create the persistent catalog the first time the app starts."""
    if not DATA.exists():
        if BUNDLED_DATA.exists():
            shutil.copy2(BUNDLED_DATA, DATA)
        else:
            DATA.write_text("[]", encoding="utf-8")

    # If the project contains bundled upload files, copy them only when the
    # persistent upload directory does not already contain that file.
    if BUNDLED_UPLOADS.exists():
        for origen in BUNDLED_UPLOADS.iterdir():
            if origen.is_file():
                destino = UPLOADS / origen.name
                if not destino.exists():
                    shutil.copy2(origen, destino)


inicializar_almacenamiento()


def cargar_productos():
    try:
        return json.loads(DATA.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        DATA.write_text("[]", encoding="utf-8")
        return []


def guardar_productos(productos):
    # Atomic-ish replacement prevents a half-written JSON file if the process
    # is interrupted during a write.
    temporal = DATA.with_suffix(".tmp")
    temporal.write_text(
        json.dumps(productos, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    temporal.replace(DATA)


def guardar_imagen(archivo):
    if not archivo or not archivo.filename:
        return "https://placehold.co/700x700/f9dbe8/6b4358?text=MOÑO+MEREDITH"

    nombre = secure_filename(archivo.filename)
    if not nombre or "." not in nombre:
        return None

    extension = nombre.rsplit(".", 1)[-1].lower()
    if extension not in ALLOWED:
        return None

    base = Path(nombre).stem or "foto"
    destino = UPLOADS / nombre
    contador = 1
    while destino.exists():
        destino = UPLOADS / f"{base}_{contador}.{extension}"
        contador += 1

    archivo.save(str(destino))
    # Images are served through Flask from the persistent directory.
    return url_for("imagen", nombre=destino.name)


@app.get("/uploads/<path:nombre>")
def imagen(nombre):
    # send_from_directory prevents path traversal and serves files from the
    # persistent upload directory.
    from flask import send_from_directory
    return send_from_directory(UPLOADS, nombre)


@app.route("/")
def inicio():
    productos = cargar_productos()
    return render_template("index.html", productos=productos, whatsapp=WHATSAPP)

from functools import wraps
from flask import session

app.secret_key = "CAMBIA-ESTA-CLAVE"

USUARIO_ADMIN = "admin"
CONTRASENA_ADMIN = "angelcruel"

def requiere_login(f):
    @wraps(f)
    def protegida(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return protegida

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "")
        contrasena = request.form.get("contrasena", "")

        if usuario == USUARIO_ADMIN and contrasena == CONTRASENA_ADMIN:
            session["admin"] = True
            return redirect(url_for("admin"))

        return "Usuario o contraseña incorrectos", 401

    return '''
    <h2>Acceso al catálogo</h2>
    <form method="post">
        <input name="usuario" placeholder="Usuario" required><br><br>
        <input name="contrasena" type="password" placeholder="Contraseña" required><br><br>
        <button type="submit">Entrar</button>
    </form>
    '''

@app.route("/salir")
def salir():
    session.pop("admin", None)
    return redirect(url_for("login"))
@app.route("/admin", methods=["GET", "POST"])
@requiere_logincargar_productos()

    if request.method == "POST":
        imagen = guardar_imagen(request.files.get("foto"))
        if imagen is None:
            return "Formato de imagen no permitido. Usa JPG, JPEG, PNG, WEBP o GIF.", 400

        imagen_url = request.form.get("imagen", "").strip()
        if imagen_url:
            imagen = imagen_url

        nuevo = {
            "nombre": request.form["nombre"].strip(),
            "precio": request.form["precio"].strip(),
            "categoria": request.form["categoria"].strip(),
            "descripcion": request.form["descripcion"].strip(),
            "imagen": imagen,
            "disponible": True
        }
        productos.append(nuevo)
        guardar_productos(productos)
        return redirect(url_for("admin"))

    return render_template("admin.html", productos=productos)


@app.post("/admin/eliminar/<int:indice>")
def eliminar(indice):
    productos = cargar_productos()
    if 0 <= indice < len(productos):
        eliminado = productos.pop(indice)
        guardar_productos(productos)

        # Delete local uploaded image too, but never delete external URLs.
        imagen_url = str(eliminado.get("imagen", ""))
        if imagen_url.startswith("/uploads/"):
            nombre = imagen_url.rsplit("/", 1)[-1]
            archivo = UPLOADS / nombre
            if archivo.exists() and archivo.is_file():
                archivo.unlink()

    return redirect(url_for("admin"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
