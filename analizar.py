import csv
import html
import math
import os
import sys
from collections import Counter
from datetime import datetime, timezone

ESTUDIANTE = "Valeria Rafaela Figueroa Camacho"
USUARIO = "Valefc"
REPO_URL = f"https://github.com/{USUARIO}/monitor-sismos-actions"
FUENTE = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_week.csv"
COLUMNAS = ["time", "mag", "place", "id", "type"]


class ErrorDatos(Exception):
    """Dato indispensable ausente o inválido."""


def parsear_fecha(texto, fila):
    try:
        fecha = datetime.fromisoformat(texto.strip().replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        raise ErrorDatos(f"Fila {fila}: fecha inválida {texto!r}")
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    return fecha.astimezone(timezone.utc)


def parsear_magnitud(texto, fila):
    try:
        magnitud = float((texto or "").strip())
    except ValueError:
        raise ErrorDatos(f"Fila {fila}: magnitud inválida {texto!r}")
    if not math.isfinite(magnitud):
        raise ErrorDatos(f"Fila {fila}: magnitud no finita {texto!r}")
    return magnitud


def leer_sismos(ruta):
    with open(ruta, newline="", encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)
        faltan = [c for c in COLUMNAS if c not in (lector.fieldnames or [])]
        if faltan:
            raise ErrorDatos("Faltan columnas obligatorias: " + ", ".join(faltan))
        sismos = []
        for n, fila in enumerate(lector, start=2):
            if (fila["type"] or "").strip() != "earthquake":
                continue
            sismos.append({
                "id": fila["id"],
                "time": parsear_fecha(fila["time"], n),
                "mag": parsear_magnitud(fila["mag"], n),
                "place": (fila["place"] or "Ubicación no indicada").strip(),
            })
    if not sismos:
        raise ErrorDatos("No hay registros con type = earthquake.")
    return sismos


def resumir(sismos):
    orden = sorted(sismos, key=lambda s: s["time"], reverse=True)
    por_fecha = Counter(s["time"].date().isoformat() for s in sismos)
    return {
        "total": len(sismos),
        "mag_max": max(s["mag"] for s in sismos),
        "reciente": orden[0]["time"],
        "inicio": min(s["time"] for s in sismos),
        "ultimos": orden[:10],
        "por_fecha": dict(sorted(por_fecha.items())),
    }


def fmt(fecha):
    return fecha.strftime("%Y-%m-%d %H:%M:%S UTC")


def grafico_svg(por_fecha):
    ancho_barra, sep, alto = 60, 12, 220
    maximo = max(por_fecha.values())
    ancho = len(por_fecha) * (ancho_barra + sep) + sep
    partes = [f'<svg viewBox="0 0 {ancho} {alto + 50}" width="100%" role="img" '
              f'aria-label="Cantidad de sismos por fecha (UTC)">']
    for i, (fecha, n) in enumerate(por_fecha.items()):
        h = n / maximo * alto
        x = sep + i * (ancho_barra + sep)
        y = 25 + alto - h
        partes.append(f'<rect x="{x}" y="{y:.1f}" width="{ancho_barra}" height="{h:.1f}" fill="#c0392b"/>')
        partes.append(f'<text x="{x + ancho_barra / 2}" y="{y - 5:.1f}" text-anchor="middle" font-size="13">{n}</text>')
        partes.append(f'<text x="{x + ancho_barra / 2}" y="{alto + 43}" text-anchor="middle" font-size="12">{fecha[5:]}</text>')
    partes.append("</svg>")
    return "".join(partes)


def generar_html(sismos, descargado):
    r = resumir(sismos)
    filas = "".join(
        f"<tr><td>{fmt(s['time'])}</td><td>{html.escape(s['place'])}</td><td>{s['mag']:.1f}</td></tr>"
        for s in r["ultimos"]
    )
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Monitor de sismos recientes</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;line-height:1.5}}
.kpis{{display:flex;gap:1rem;flex-wrap:wrap}}
.kpi{{flex:1;min-width:200px;border:1px solid #ccc;border-radius:8px;padding:1rem}}
.kpi b{{display:block;font-size:1.5rem}}
table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #ccc;padding:.4rem;text-align:left}}
</style></head><body>
<h1>Monitor de sismos recientes</h1>
<p>Estudiante: <b>{html.escape(ESTUDIANTE)}</b><br>
Fuente: <a href="{FUENTE}">USGS – sismos M2.5+ de los últimos 7 días</a></p>
<p>Descarga realizada: <b>{fmt(descargado)}</b><br>
Periodo de los datos: {fmt(r['inicio'])} a {fmt(r['reciente'])}</p>
<div class="kpis">
<div class="kpi">Sismos<b>{r['total']}</b></div>
<div class="kpi">Magnitud máxima<b>{r['mag_max']:.1f}</b></div>
<div class="kpi">Evento más reciente<b style="font-size:1rem">{fmt(r['reciente'])}</b></div>
</div>
<h2>Los 10 sismos más recientes</h2>
<table><tr><th>Fecha (UTC)</th><th>Ubicación</th><th>Magnitud</th></tr>{filas}</table>
<h2>Sismos por fecha (UTC)</h2>
{grafico_svg(r['por_fecha'])}
<p><a href="{REPO_URL}">Repositorio</a> · <a href="{REPO_URL}/actions">Ejecuciones en Actions</a></p>
</body></html>"""


def main():
    if not os.path.exists("datos.csv"):
        print("ERROR: no existe datos.csv. Ejecuta primero descargar.py")
        return 1
    try:
        sismos = leer_sismos("datos.csv")
    except ErrorDatos as error:
        print(f"ERROR: {error}")
        return 1
    descargado = datetime.fromtimestamp(os.path.getmtime("datos.csv"), tz=timezone.utc)
    os.makedirs("public", exist_ok=True)
    with open("public/index.html", "w", encoding="utf-8") as salida:
        salida.write(generar_html(sismos, descargado))
    print(f"Informe generado con {len(sismos)} sismos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())