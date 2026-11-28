"""Contratos del chat ficticio: contexto, acceso y publicación humana."""

import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import BackgroundTasks, HTTPException
from streamlit.testing.v1 import AppTest

from analysis import analyze
from main import MensajeCliente, MensajeSoporte, RectificacionMensaje, crear_app


class ChatTest(unittest.TestCase):
    def test_analisis_responde_al_ultimo_mensaje_y_no_a_la_apertura(self):
        class Datos:
            def obtener_ticket(self, _id):
                return {"texto": "El paquete ficticio llegó roto", "plan": "Basic",
                        "prioridad": "media"}

            def contexto_conversacion(self, _id):
                return {
                    "ultimo_texto_cliente": "¿Puedo cambiarlo por otro?",
                    "mensaje_cliente_id": 6, "ultimo_mensaje_id": 6,
                    "mensajes": [
                        {"id": 2, "autor": "cliente", "texto": "El paquete ficticio llegó roto"},
                        {"id": 5, "autor": "soporte", "texto": "Contanos qué producto fue"},
                        {"id": 6, "autor": "cliente", "texto": "¿Puedo cambiarlo por otro?"},
                    ],
                }

            def contexto_reclamo(self, _id):
                return None

            def guardar_ejecucion(self, _id, resultado):
                self.guardado = resultado
                return 12

        datos = Datos()

        def modelo(_instruccion, entrada, esquema):
            propiedades = esquema["properties"]
            if "categoria" in propiedades:
                self.assertEqual(entrada["texto"], "¿Puedo cambiarlo por otro?")
                self.assertEqual(entrada["historial_conversacion"][1]["autor"], "soporte")
                return {"categoria": "general", "consulta": "cambio de producto", "faltantes": []}
            if "herramienta" in propiedades:
                return {"herramienta": "lexical", "consulta": "cambio de producto",
                        "motivo": "Buscar procedimiento"}
            if "citas" in propiedades:
                return {"texto": "Podemos revisar la solicitud de cambio.",
                        "citas": [], "preguntas": []}
            return {"decision": "revisar", "motivos": ["Revisión humana"]}

        salida = analyze(9, datos, llm=modelo, recuperar=lambda *_: [])
        self.assertEqual(salida["mensaje_cliente_id"], 6)
        self.assertEqual(salida["ultimo_mensaje_id"], 6)
        self.assertEqual(datos.guardado["borrador"]["texto"],
                         "Podemos revisar la solicitud de cambio.")

    def test_api_no_muestra_otra_conversacion_y_publica_mensajes(self):
        class Datos:
            def __init__(self):
                self.mensajes = [{"id": 1, "autor": "cliente", "texto": "Consulta ficticia",
                                  "tipo": "inicio"}]

            def listar_mensajes_reclamo(self, ticket_id, cliente_id):
                return None if cliente_id not in (None, 2) else self.mensajes

            def enviar_mensaje_cliente(self, ticket_id, cliente_id, texto):
                if cliente_id != 2:
                    return None
                mensaje = {"id": 2, "autor": "cliente", "texto": texto, "tipo": "mensaje"}
                self.mensajes.append(mensaje)
                return mensaje

            def contexto_conversacion(self, ticket_id):
                ultimo = next(m for m in reversed(self.mensajes) if m["autor"] == "cliente")
                return {"ultimo_texto_cliente": ultimo["texto"],
                        "mensaje_cliente_id": ultimo["id"]}

            def contexto_reclamo(self, ticket_id):
                return {}

            def pedido_del_reclamo(self, ticket_id):
                return None

            def fotos_reclamo(self, ticket_id):
                return []

            def registrar_borrador_pendiente(self, ticket_id, mensaje_id):
                pass

            def enviar_mensaje_soporte(self, ticket_id, texto):
                mensaje = {"id": 3, "autor": "soporte", "texto": texto, "tipo": "mensaje"}
                self.mensajes.append(mensaje)
                return mensaje

            def rectificar_mensaje_soporte(self, ticket_id, mensaje_id, texto, motivo):
                self.mensajes = [m for m in self.mensajes if m["id"] != mensaje_id]
                mensaje = {"id": 4, "autor": "soporte", "texto": texto,
                           "tipo": "rectificacion"}
                self.mensajes.append(mensaje)
                return mensaje

        datos = Datos()
        with patch("main.SupportOpsDB", return_value=datos):
            app = crear_app("clave-ficticia")
        rutas = {r.path: r.endpoint for r in app.routes}
        base = "/reclamos/{ticket_id}/mensajes"
        with self.assertRaises(HTTPException) as error:
            rutas[base](7, cliente_id=3)
        self.assertEqual(error.exception.status_code, 404)
        self.assertEqual(len(rutas[base](7, cliente_id=2)["mensajes"]), 1)
        rutas[base + "/cliente"](
            7, MensajeCliente(cliente_id=2, texto="¿Podés ayudarme con esto?"),
            BackgroundTasks())
        rutas[base + "/soporte"](
            7, MensajeSoporte(texto="Sí, revisaremos el caso ficticio."))
        rutas[base + "/{mensaje_id}/rectificar"](
            7, 3, RectificacionMensaje(texto="Revisaremos el caso hoy.", motivo="Aclaración"))
        salida = rutas[base](7, cliente_id=2)["mensajes"]
        self.assertEqual([m["autor"] for m in salida], ["cliente", "cliente", "soporte"])
        self.assertEqual(salida[-1]["texto"], "Revisaremos el caso hoy.")

    def test_operador_ve_y_contesta_en_la_misma_conversacion(self):
        estado = {"mensajes": [
            {"id": 1, "autor": "cliente", "texto": "El producto ficticio llegó roto",
             "tipo": "inicio"}
        ], "enviado": None}

        def get(ruta, **_params):
            if ruta == "/health":
                return {"estado": "ok"}
            if ruta == "/kpis":
                return {"tickets": 1, "abiertos": 1, "resueltos": 0}
            if ruta == "/tickets":
                return {"cantidad": 0, "tickets": []}
            if ruta == "/reclamos":
                return {"reclamos": [{"id": 2, "ticket_id": 7,
                                      "cliente": "Cliente ficticio", "texto": "Llegó roto",
                                      "estado": "abierto", "producto": None,
                                      "pedido_id": None}]}
            if ruta == "/reclamos/7/mensajes":
                return {"mensajes": estado["mensajes"]}
            if ruta == "/reclamos/7/fotos":
                return {"fotos": []}
            if ruta == "/reclamos/7/propuesta":
                return {"estado": None}
            if ruta == "/reclamos/7/mensajes/historial":
                return {"mensajes": [
                    {**m, "creado": "2026-11-25", "vigente": True, "motivo": None}
                    for m in estado["mensajes"]
                ]}
            if ruta == "/tickets/7":
                return {"id": 7, "cliente": "Cliente ficticio", "texto": "Llegó roto"}
            if ruta == "/tickets/7/ejecuciones":
                return {"ejecuciones": [{"id": 9}]}
            if ruta == "/ejecuciones/9":
                return {"resultado": {"triage": {"categoria": "general"},
                                      "supervision": {"decision": "revisar"},
                                      "borrador": {"texto": "Propuesta interna", "citas": []},
                                      "evidencia": []},
                        "revision": None}
            raise AssertionError(ruta)

        def post(ruta, cuerpo=None, **_params):
            if ruta == "/reclamos/7/mensajes/soporte":
                estado["enviado"] = cuerpo["texto"]
                estado["mensajes"].append({"id": 2, "autor": "soporte",
                                           "texto": cuerpo["texto"], "tipo": "mensaje"})
                return {"id": 2}
            if ruta == "/tickets/7/analizar":
                estado["analisis"] = 9
                return {"ejecucion_id": 9}
            raise AssertionError(ruta)

        with patch("api_client.get", side_effect=get), patch("api_client.post", side_effect=post):
            app = AppTest.from_file(Path(__file__).with_name("streamlit_app.py"),
                                    default_timeout=10)
            app.run()
            app.radio[0].set_value("Bandeja").run()
            self.assertEqual(len(app.chat_message), 1)
            app.chat_input[0].set_value("Podemos revisar ese producto ficticio.").run()
            self.assertEqual(estado["enviado"], "Podemos revisar ese producto ficticio.")
            self.assertEqual(len(app.chat_message), 2)
            next(b for b in app.button if b.label == "Volver a preparar propuesta").click().run()
            self.assertEqual(estado["analisis"], 9)
            self.assertTrue(any("Propuesta interna" in m.value for m in app.markdown))
            self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
