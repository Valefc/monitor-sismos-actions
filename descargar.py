import sys
import urllib.request

URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_week.csv"


def main():
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "monitor-sismos-actions"})
        with urllib.request.urlopen(req, timeout=30) as respuesta:
            contenido = respuesta.read()
    except Exception as error:
        print(f"ERROR: no se pudo descargar el CSV del USGS: {error}")
        return 1

    if not contenido.startswith(b"time,"):
        print("ERROR: la respuesta no parece un CSV del USGS.")
        return 1

    with open("datos.csv", "wb") as archivo:  # sobrescribe en cada ejecución
        archivo.write(contenido)
    print(f"Descarga correcta: {len(contenido)} bytes guardados en datos.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())