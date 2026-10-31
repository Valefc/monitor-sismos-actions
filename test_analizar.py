import os
import tempfile
import unittest
from datetime import datetime, timezone

import analizar

CSV_OK = """time,mag,place,id,type
2026-10-30T10:00:00.000Z,4.0,"10 km N de Lima, Peru",a1,earthquake
2026-10-30T15:30:00.000Z,5.5,"Costa de Chile",a2,earthquake
2026-10-31T01:00:00.000Z,3.0,"Cantera",a3,quarry blast
2026-10-31T02:00:00.000Z,2.5,"Alaska",a4,earthquake
"""


def escribir_csv(texto):
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
    f.write(texto)
    f.close()
    return f.name


class PruebasAnalizar(unittest.TestCase):
    def test_calculo_conocido(self):
        ruta = escribir_csv(CSV_OK)
        self.addCleanup(os.remove, ruta)
        r = analizar.resumir(analizar.leer_sismos(ruta))
        self.assertEqual(r["total"], 3)          # ignora la explosión de cantera
        self.assertEqual(r["mag_max"], 5.5)
        self.assertEqual(r["por_fecha"], {"2026-10-30": 2, "2026-10-31": 1})

    def test_rechaza_magnitud_invalida(self):
        ruta = escribir_csv("time,mag,place,id,type\n2026-10-30T10:00:00Z,abc,X,b1,earthquake\n")
        self.addCleanup(os.remove, ruta)
        with self.assertRaises(analizar.ErrorDatos):
            analizar.leer_sismos(ruta)

    def test_detecta_columna_ausente(self):
        ruta = escribir_csv("time,place,id,type\n2026-10-30T10:00:00Z,X,c1,earthquake\n")
        self.addCleanup(os.remove, ruta)
        with self.assertRaises(analizar.ErrorDatos) as ctx:
            analizar.leer_sismos(ruta)
        self.assertIn("mag", str(ctx.exception))

    def test_genera_informe(self):
        ruta = escribir_csv(CSV_OK)
        self.addCleanup(os.remove, ruta)
        sismos = analizar.leer_sismos(ruta)
        descarga = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
        pagina = analizar.generar_html(sismos, descarga)
        self.assertIn("2026-10-31 12:00:00 UTC", pagina)
        self.assertIn("Costa de Chile", pagina)
        self.assertIn("<svg", pagina)
        self.assertIn("/actions", pagina)


if __name__ == "__main__":
    unittest.main()