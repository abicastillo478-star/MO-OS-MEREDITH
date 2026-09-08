from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import json
from pathlib import Path
from config import WHATSAPP

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
BASE_DIR = Path(__file__).resolve().parent
DATA = BASE_DIR / "productos.json"
UPLOADS = BASE_DIR / "static/uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)
ALLOWED = {"png", "jpg", "jpeg", "webp", "gif"}

def cargar_productos():
    return json.loads(DATA.read_text(encoding="utf-8"))

def guardar_productos(productos):
    DATA.write_text(json.dumps(productos, ensure_ascii=False, indent=2), encoding="utf-8")

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
    return "/" + destino.relative_to(BASE_DIR).as_posix()

@app.route("/")
def inicio():
    productos = cargar_productos()
    return render_template("index.html", productos=productos, whatsapp=WHATSAPP)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    productos = cargar_productos()
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
        productos.pop(indice)
        guardar_productos(productos)
    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
