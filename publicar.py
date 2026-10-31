"""
Publicador automático de Hábitos Fix Hoy.

Lee calendario.csv y publica en Instagram, Facebook y YouTube todo lo que
ya tenga la hora cumplida y siga "pendiente". Usa las APIs oficiales de
Meta y Google. Después marca cada red como publicada o con error.

Variables de entorno (se cargan como "Secrets" en GitHub):
  META_PAGE_ID, META_PAGE_TOKEN, META_IG_USER_ID
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
Opcionales:
  GRAPH_VERSION (por defecto v23.0)
  MODO_PRUEBA=1  -> no publica nada, solo muestra qué haría
"""
import csv
import mimetypes
import os
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

ZONA = ZoneInfo("America/Argentina/Buenos_Aires")
CALENDARIO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calendario.csv")
RAIZ = os.path.dirname(os.path.abspath(__file__))
GRAPH = f"https://graph.facebook.com/{os.environ.get('GRAPH_VERSION', 'v23.0')}"
MODO_PRUEBA = os.environ.get("MODO_PRUEBA") == "1"
TIMEOUT = 120

COLUMNAS = ["fecha_hora", "redes", "tipo", "archivo", "texto",
            "primer_comentario", "titulo_youtube", "instagram", "facebook", "youtube", "detalle"]
REDES = ["instagram", "facebook", "youtube"]


class ErrorPublicacion(Exception):
    pass


def env(nombre):
    valor = os.environ.get(nombre, "").strip()
    if not valor:
        raise ErrorPublicacion(f"falta configurar el secreto {nombre}")
    return valor


def revisar(resp, que):
    try:
        datos = resp.json()
    except ValueError:
        datos = {"texto": resp.text[:300]}
    if resp.status_code >= 400 or (isinstance(datos, dict) and "error" in datos):
        err = datos.get("error", datos) if isinstance(datos, dict) else datos
        if isinstance(err, dict):
            err = err.get("message", err)
        raise ErrorPublicacion(f"{que}: {err}")
    return datos


def ruta_archivo(archivo):
    ruta = os.path.join(RAIZ, archivo)
    if not os.path.isfile(ruta):
        raise ErrorPublicacion(f"no encuentro el archivo {archivo} en el repositorio")
    return ruta


def url_publica(archivo):
    """Instagram necesita las imágenes en una URL pública: usamos la del repo."""
    if archivo.startswith("http"):
        return archivo
    repo = env("GITHUB_REPOSITORY")
    rama = os.environ.get("GITHUB_REF_NAME", "main")
    return f"https://raw.githubusercontent.com/{repo}/{rama}/{archivo}"


# ---------------------------------------------------------------- INSTAGRAM
def esperar_contenedor(cid, token):
    for _ in range(60):  # hasta ~10 minutos
        r = requests.get(f"{GRAPH}/{cid}", params={"fields": "status_code,status", "access_token": token}, timeout=TIMEOUT)
        d = revisar(r, "estado del video en Instagram")
        estado = d.get("status_code")
        if estado == "FINISHED":
            return
        if estado in ("ERROR", "EXPIRED"):
            raise ErrorPublicacion(f"Instagram rechazó el archivo: {d.get('status', estado)}")
        time.sleep(10)
    raise ErrorPublicacion("Instagram tardó demasiado en procesar el video")


def publicar_instagram(fila):
    ig = env("META_IG_USER_ID")
    token = env("META_PAGE_TOKEN")
    tipo, archivo, texto = fila["tipo"], fila["archivo"], fila["texto"]

    if tipo == "reel":
        ruta = ruta_archivo(archivo)
        r = requests.post(f"{GRAPH}/{ig}/media", data={
            "media_type": "REELS", "upload_type": "resumable", "caption": texto,
            "share_to_feed": "true", "access_token": token}, timeout=TIMEOUT)
        cid = revisar(r, "crear Reel en Instagram")["id"]
        tam = os.path.getsize(ruta)
        with open(ruta, "rb") as f:
            r = requests.post(
                f"https://rupload.facebook.com/ig-api-upload/{GRAPH.rsplit('/', 1)[1]}/{cid}",
                headers={"Authorization": f"OAuth {token}", "offset": "0", "file_size": str(tam)},
                data=f, timeout=600)
        revisar(r, "subir video a Instagram")
        esperar_contenedor(cid, token)
    elif tipo == "imagen":
        r = requests.post(f"{GRAPH}/{ig}/media", data={
            "image_url": url_publica(archivo), "caption": texto, "access_token": token}, timeout=TIMEOUT)
        cid = revisar(r, "crear imagen en Instagram")["id"]
        esperar_contenedor(cid, token)
    elif tipo == "carrusel":
        hijos = []
        for parte in [a.strip() for a in archivo.split("|") if a.strip()]:
            r = requests.post(f"{GRAPH}/{ig}/media", data={
                "image_url": url_publica(parte), "is_carousel_item": "true", "access_token": token}, timeout=TIMEOUT)
            hijos.append(revisar(r, f"subir {parte} al carrusel")["id"])
        for h in hijos:
            esperar_contenedor(h, token)
        r = requests.post(f"{GRAPH}/{ig}/media", data={
            "media_type": "CAROUSEL", "children": ",".join(hijos), "caption": texto, "access_token": token}, timeout=TIMEOUT)
        cid = revisar(r, "armar carrusel en Instagram")["id"]
        esperar_contenedor(cid, token)
    else:
        raise ErrorPublicacion("Instagram no permite publicaciones de solo texto")

    r = requests.post(f"{GRAPH}/{ig}/media_publish", data={"creation_id": cid, "access_token": token}, timeout=TIMEOUT)
    media_id = revisar(r, "publicar en Instagram")["id"]

    if fila.get("primer_comentario"):
        r = requests.post(f"{GRAPH}/{media_id}/comments",
                          data={"message": fila["primer_comentario"], "access_token": token}, timeout=TIMEOUT)
        revisar(r, "primer comentario en Instagram")
    return media_id


# ---------------------------------------------------------------- FACEBOOK
def publicar_facebook(fila):
    pagina = env("META_PAGE_ID")
    token = env("META_PAGE_TOKEN")
    tipo, archivo, texto = fila["tipo"], fila["archivo"], fila["texto"]

    if tipo == "texto":
        r = requests.post(f"{GRAPH}/{pagina}/feed", data={"message": texto, "access_token": token}, timeout=TIMEOUT)
        post_id = revisar(r, "publicar en Facebook")["id"]
    elif tipo in ("imagen", "carrusel"):
        primera = archivo.split("|")[0].strip()
        ruta = ruta_archivo(primera)
        with open(ruta, "rb") as f:
            r = requests.post(f"{GRAPH}/{pagina}/photos",
                              data={"caption": texto, "access_token": token},
                              files={"source": (os.path.basename(ruta), f, mimetypes.guess_type(ruta)[0] or "image/jpeg")},
                              timeout=TIMEOUT)
        d = revisar(r, "publicar imagen en Facebook")
        post_id = d.get("post_id", d["id"])
    elif tipo == "reel":
        ruta = ruta_archivo(archivo)
        with open(ruta, "rb") as f:
            r = requests.post(f"https://graph-video.facebook.com/{GRAPH.rsplit('/', 1)[1]}/{pagina}/videos",
                              data={"description": texto, "title": fila.get("titulo_youtube") or "", "access_token": token},
                              files={"source": (os.path.basename(ruta), f, "video/mp4")}, timeout=900)
        post_id = revisar(r, "publicar video en Facebook")["id"]
    else:
        raise ErrorPublicacion(f"tipo desconocido: {tipo}")

    if fila.get("primer_comentario"):
        r = requests.post(f"{GRAPH}/{post_id}/comments",
                          data={"message": fila["primer_comentario"], "access_token": token}, timeout=TIMEOUT)
        revisar(r, "primer comentario en Facebook")
    return post_id


# ---------------------------------------------------------------- YOUTUBE
def publicar_youtube(fila):
    if fila["tipo"] != "reel":
        raise ErrorPublicacion("YouTube solo recibe videos (tipo reel)")
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": env("YT_CLIENT_ID"), "client_secret": env("YT_CLIENT_SECRET"),
        "refresh_token": env("YT_REFRESH_TOKEN"), "grant_type": "refresh_token"}, timeout=TIMEOUT)
    acceso = revisar(r, "permiso de YouTube")["access_token"]

    titulo = (fila.get("titulo_youtube") or fila["texto"].split("\n")[0]).strip()
    if "#shorts" not in titulo.lower():
        titulo = f"{titulo} #Shorts"
    titulo = titulo[:100]
    descripcion = fila["texto"]
    if fila.get("primer_comentario"):
        descripcion += "\n\n" + fila["primer_comentario"]

    meta = {
        "snippet": {"title": titulo, "description": descripcion[:4900], "categoryId": "26",
                    "defaultLanguage": "es", "tags": ["HabitosFixHoy", "habitos", "finanzas personales"]},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
    }
    ruta = ruta_archivo(fila["archivo"])
    r = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        headers={"Authorization": f"Bearer {acceso}", "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Type": "video/*", "X-Upload-Content-Length": str(os.path.getsize(ruta))},
        json=meta, timeout=TIMEOUT)
    if r.status_code >= 400:
        revisar(r, "preparar subida a YouTube")
    destino = r.headers["Location"]
    with open(ruta, "rb") as f:
        r = requests.put(destino, headers={"Authorization": f"Bearer {acceso}", "Content-Type": "video/*"},
                         data=f, timeout=900)
    d = revisar(r, "subir video a YouTube")
    privacidad = d.get("status", {}).get("privacyStatus")
    if privacidad and privacidad != "public":
        return f"{d['id']} (YouTube lo dejó {privacidad}: revisá la guía, paso de verificación)"
    return d["id"]


PUBLICADORES = {"instagram": publicar_instagram, "facebook": publicar_facebook, "youtube": publicar_youtube}


# ---------------------------------------------------------------- CALENDARIO
def leer():
    with open(CALENDARIO, newline="", encoding="utf-8-sig") as f:
        filas = list(csv.DictReader(f))
    for fila in filas:
        for c in COLUMNAS:
            fila[c] = (fila.get(c) or "").strip() if c not in ("texto", "primer_comentario") else (fila.get(c) or "")
    return filas


def guardar(filas):
    with open(CALENDARIO, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for fila in filas:
            w.writerow({c: fila.get(c, "") for c in COLUMNAS})


def hora_de(fila):
    try:
        return datetime.strptime(fila["fecha_hora"], "%Y-%m-%d %H:%M").replace(tzinfo=ZONA)
    except ValueError:
        return None


def main():
    ahora = datetime.now(ZONA)
    filas = leer()
    hechas = errores = 0

    for n, fila in enumerate(filas, start=2):
        cuando = hora_de(fila)
        if cuando is None:
            if fila["fecha_hora"]:
                fila["detalle"] = "fecha mal escrita: usá AAAA-MM-DD HH:MM"
            continue
        if cuando > ahora:
            continue
        redes = [r.strip().lower() for r in fila["redes"].replace(",", "+").split("+") if r.strip()]
        notas = []
        for red in redes:
            if red not in REDES:
                notas.append(f"{red}: red desconocida")
                continue
            if fila[red].startswith("publicado"):
                continue
            if fila[red].startswith("error") and fila[red].count("|") >= 3:
                continue  # ya falló 3 veces, no insiste más
            print(f"Fila {n} → {red}: {fila['texto'][:50]!r}")
            if MODO_PRUEBA:
                notas.append(f"{red}: (prueba) se publicaría")
                continue
            try:
                ident = PUBLICADORES[red](fila)
                fila[red] = f"publicado {datetime.now(ZONA):%Y-%m-%d %H:%M}"
                notas.append(f"{red}: {ident}")
                hechas += 1
            except (ErrorPublicacion, requests.RequestException, KeyError) as e:
                if "falta configurar" not in str(e):  # sin claves no cuenta como intento
                    previo = fila[red] if fila[red].startswith("error") else "error"
                    fila[red] = previo + "|"
                notas.append(f"{red}: {e}")
                errores += 1
                print(f"   ✖ {e}")
        if notas:
            fila["detalle"] = " · ".join(notas)[:500]

    if not MODO_PRUEBA:
        guardar(filas)
    print(f"Listo: {hechas} publicadas, {errores} con error.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
