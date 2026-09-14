from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
from functools import wraps
import base64
import json
import os
from pathlib import Path
import requests
from config import WHATSAPP

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
app.secret_key = os.environ.get("SECRET_KEY", "cambia-esta-clave-en-render")

USUARIO_ADMIN = os.environ.get("ADMIN_USER", "admin")
CONTRASENA_ADMIN = os.environ.get("ADMIN_PASSWORD", "1234")

BASE_DIR = Path(__file__).resolve().parent
DATA_LOCAL = BASE_DIR / "productos.json"
ALLOWED = {"png", "jpg", "jpeg", "webp", "gif"}

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
GITHUB_REPO = os.environ.get(
    "GITHUB_REPO",
    "abicastillo478-star/MO-OS-MEREDITH"
).strip()
GITHUB_BRANCH = os.environ.get(
    "GITHUB_DATA_BRANCH",
    "catalogo"
).strip()

GITHUB_API = "https://api.github.com"


def requiere_login(func):
    @wraps(func)
    def protegida(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login"))
        return func(*args, **kwargs)

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

    return """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Acceso · MOÑOS MEREDITH</title>
<style>
body{
    margin:0;
    background:#fff9fc;
    color:#674755;
    font-family:Arial,sans-serif;
    display:grid;
    place-items:center;
    min-height:100vh;
}
.box{
    width:min(360px,88%);
    background:white;
    padding:30px;
    border-radius:20px;
    box-shadow:0 10px 40px #9d607b22;
}
.box h2{
    font-family:Georgia,serif;
    font-weight:400;
    font-size:32px;
}
.box input{
    box-sizing:border-box;
    width:100%;
    padding:13px;
    margin:6px 0;
    border:1px solid #e7cbd8;
    border-radius:10px;
}
.box button{
    width:100%;
    padding:13px;
    border:0;
    border-radius:25px;
    background:#a76582;
    color:white;
    font-weight:bold;
    margin-top:10px;
}
</style>
</head>
<body>
<div class="box">
<h2>MOÑOS MEREDITH</h2>
<p>Acceso al catálogo</p>
<form method="post">
<input name="usuario" placeholder="Usuario" required>
<input name="contrasena" type="password" placeholder="Contraseña" required>
<button>Entrar</button>
</form>
</div>
</body>
</html>"""


@app.route("/salir")
def salir():
    session.pop("admin", None)
    return redirect(url_for("login"))


def gh_headers():
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def gh_url(path):
    return f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{path}"


def asegurar_rama():
    if not GITHUB_TOKEN:
        return False

    ref_url = (
        f"{GITHUB_API}/repos/{GITHUB_REPO}"
        f"/git/ref/heads/{GITHUB_BRANCH}"
    )

    respuesta = requests.get(
        ref_url,
        headers=gh_headers(),
        timeout=15
    )

    if respuesta.status_code == 200:
        return True

    if respuesta.status_code != 404:
        respuesta.raise_for_status()

    main_url = (
        f"{GITHUB_API}/repos/{GITHUB_REPO}"
        f"/git/ref/heads/main"
    )

    main = requests.get(
        main_url,
        headers=gh_headers(),
        timeout=15
    )

    main.raise_for_status()

    sha = main.json()["object"]["sha"]

    crear = requests.post(
        f"{GITHUB_API}/repos/{GITHUB_REPO}/git/refs",
        headers=gh_headers(),
        json={
            "ref": f"refs/heads/{GITHUB_BRANCH}",
            "sha": sha
        },
        timeout=15,
    )

    if crear.status_code not in (201, 422):
        crear.raise_for_status()

    return True


def obtener_github(path):
    respuesta = requests.get(
        gh_url(path),
        headers=gh_headers(),
        params={"ref": GITHUB_BRANCH},
        timeout=20,
    )

    if respuesta.status_code == 404:
        return None, None

    respuesta.raise_for_status()

    data = respuesta.json()

    contenido = base64.b64decode(
        data["content"].replace("\n", "")
    )

    return contenido, data["sha"]


def leer_productos_github():
    contenido, sha = obtener_github("productos.json")

    if contenido is None:
        return None, None

    return json.loads(
        contenido.decode("utf-8")
    ), sha


def guardar_github(path, contenido, mensaje, sha=None):
    if isinstance(contenido, str):
        contenido = contenido.encode("utf-8")

    payload = {
        "message": mensaje,
        "content": base64.b64encode(
            contenido
        ).decode("ascii"),
        "branch": GITHUB_BRANCH,
    }

    if sha:
        payload["sha"] = sha

    respuesta = requests.put(
        gh_url(path),
        headers=gh_headers(),
        json=payload,
        timeout=30,
    )

    respuesta.raise_for_status()

    return respuesta.json()


def cargar_productos():
    if GITHUB_TOKEN:
        try:
            asegurar_rama()

            productos, _ = leer_productos_github()

            if productos is not None:
                return productos

        except Exception:
            pass

    try:
        return json.loads(
            DATA_LOCAL.read_text(
                encoding="utf-8"
            )
        )

    except (FileNotFoundError, json.JSONDecodeError):
        return []


def guardar_productos(productos):
    texto = json.dumps(
        productos,
        ensure_ascii=False,
        indent=2
    ).encode("utf-8")

    if not GITHUB_TOKEN:
        DATA_LOCAL.write_bytes(texto)
        return

    asegurar_rama()

    _, sha = obtener_github("productos.json")

    guardar_github(
        "productos.json",
        texto,
        "Actualizar catálogo de MOÑOS MEREDITH",
        sha,
    )


def guardar_imagen(archivo):
    if not archivo or not archivo.filename:
        return (
            "https://placehold.co/700x700/"
            "f9dbe8/6b4358?text=MO%C3%91O+MEREDITH"
        )

    nombre = secure_filename(
        archivo.filename
    )

    if not nombre or "." not in nombre:
        return None

    extension = nombre.rsplit(
        ".",
        1
    )[-1].lower()

    if extension not in ALLOWED:
        return None

    if not GITHUB_TOKEN:
        return None

    asegurar_rama()

    base = Path(nombre).stem or "foto"

    candidato = nombre
    contador = 1

    while True:
        _, sha = obtener_github(
            f"static/uploads/{candidato}"
        )

        if sha is None:
            break

        candidato = (
            f"{base}_{contador}.{extension}"
        )

        contador += 1

    datos = archivo.read()

    guardar_github(
        f"static/uploads/{candidato}",
        datos,
        f"Agregar foto de producto: {candidato}",
    )

    return (
        "https://raw.githubusercontent.com/"
        f"{GITHUB_REPO}/"
        f"{GITHUB_BRANCH}/"
        f"static/uploads/{candidato}"
    )


@app.route("/")
def inicio():
    productos = cargar_productos()

    return render_template(
        "index.html",
        productos=productos,
        whatsapp=WHATSAPP
    )


@app.route("/admin", methods=["GET", "POST"])
@requiere_login
def admin():
    productos = cargar_productos()

    if request.method == "POST":
        imagen = guardar_imagen(
            request.files.get("foto")
        )

        if imagen is None:
            return (
                "No se pudo guardar la imagen. "
                "Revisa GITHUB_TOKEN y usa JPG, "
                "JPEG, PNG, WEBP o GIF.",
                400,
            )

        imagen_url = request.form.get(
            "imagen",
            ""
        ).strip()

        if imagen_url:
            imagen = imagen_url

        nuevo = {
            "nombre": request.form.get(
                "nombre",
                ""
            ).strip(),

            "precio": request.form.get(
                "precio",
                ""
            ).strip(),

            "categoria": request.form.get(
                "categoria",
                ""
            ).strip(),

            "descripcion": request.form.get(
                "descripcion",
                ""
            ).strip(),

            "imagen": imagen,

            "disponible": True,
        }

        productos.append(nuevo)

        guardar_productos(productos)

        return redirect(
            url_for("admin")
        )

    return render_template(
        "admin.html",
        productos=productos
    )


@app.post("/admin/eliminar/<int:indice>")
@requiere_login
def eliminar(indice):
    productos = cargar_productos()

    if 0 <= indice < len(productos):
        productos.pop(indice)
        guardar_productos(productos)

    return redirect(
        url_for("admin")
    )


if __name__ == "__main__":
    port = int(
        os.environ.get(
            "PORT",
            "5000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
