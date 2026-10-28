"""Comprueba el recorrido de una consulta ficticia en el panel."""

import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class SimulacionTest(unittest.TestCase):
    def test_el_operador_revisa_antes_de_mostrar_la_respuesta(self):
        estado = {"revision": None, "llamadas": []}

        def get(ruta, **_parametros):
            if ruta == "/health":
                return {"estado": "ok", "base": "conectada"}
            if ruta == "/kpis":
                return {"tickets": 0, "abiertos": 0, "resueltos": 0}
            if ruta == "/tickets":
                return {"cantidad": 0, "tickets": []}
            if ruta == "/clientes":
                return {"clientes": [{"id": 1, "nombre": "Cliente demo", "plan": "Basic"}]}
            if ruta == "/ejecuciones/9":
                return {
                    "revision": estado["revision"],
                    "resultado": {
                        "triage": {"categoria": "facturacion"},
                        "supervision": {"decision": "revisar"},
                        "borrador": {"texto": "Borrador de prueba", "citas": []},
                        "evidencia": [],
                    },
                }
            raise AssertionError(ruta)

        def post(ruta, cuerpo=None, **_opciones):
            estado["llamadas"].append((ruta, cuerpo))
            if ruta == "/tickets":
                return {"id": 6 + sum(llamada[0] == "/tickets" for llamada in estado["llamadas"])}
            if ruta == "/tickets/7/analizar":
                return {"ejecucion_id": 9}
            if ruta == "/ejecuciones/9/revision":
                self.assertEqual(cuerpo["motivo"], "El borrador responde a la consulta ficticia")
                estado["revision"] = {
                    "id": 3,
                    "decision": cuerpo["decision"],
                    "texto_final": "Borrador de prueba",
                }
                return estado["revision"]
            raise AssertionError(ruta)

        with patch("api_client.get", side_effect=get), patch("api_client.post", side_effect=post):
            app = AppTest.from_file(Path(__file__).with_name("streamlit_app.py"))
            app.run()
            app.radio[0].set_value("Simulación").run()
            self.assertFalse(app.exception)

            app.chat_input[0].set_value("Necesito el comprobante de agosto").run()
            self.assertEqual(estado["llamadas"][0][0], "/tickets")
            self.assertEqual(len(app.chat_message), 1)

            next(b for b in app.button if b.label == "Pedir propuesta a la IA").click().run()
            self.assertEqual(estado["llamadas"][1][0], "/tickets/7/analizar")
            self.assertIsNone(estado["revision"])

            next(a for a in app.text_area if a.label == "Motivo de la decisión").set_value(
                "El borrador responde a la consulta ficticia"
            ).run()
            next(b for b in app.button if b.label == "Guardar decisión").click().run()
            self.assertEqual(estado["llamadas"][2][0], "/ejecuciones/9/revision")
            self.assertEqual(estado["revision"]["decision"], "aprobar")
            self.assertEqual(len(app.chat_message), 2)
            self.assertEqual(app.chat_message[1].markdown[0].value, "Borrador de prueba")
            self.assertEqual(len(app.chat_input), 1)
            self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
