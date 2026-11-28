"""Verifica el recorrido visible del cliente ficticio en Streamlit."""

import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class ClienteAppTest(unittest.TestCase):
    def test_compra_y_respuesta_solo_despues_de_revision(self):
        estado = {"pedidos": [], "revisado": False, "mensaje_cliente": None}
        producto = {
            "id": "PR-001", "nombre": "Auriculares Nube", "categoria": "Audio",
            "descripcion": "Producto ficticio", "precio": 34990, "stock": 4,
        }

        def get(ruta, **_parametros):
            if ruta == "/health":
                return {"estado": "ok", "base": "conectada"}
            if ruta == "/clientes":
                return {"clientes": [{"id": 1, "nombre": "Cliente demo 1", "plan": "Basic"},
                                     {"id": 497, "nombre": "Cliente sintetico 497", "plan": "Pro"}]}
            if ruta == "/productos":
                return {"productos": [producto]}
            if ruta == "/pedidos":
                return {"pedidos": estado["pedidos"]}
            if ruta == "/reclamos":
                return {"reclamos": [{
                    "id": 4, "ticket_id": 12, "estado": "abierto",
                    "producto": None, "pedido_id": 7, "texto": "No encuentro mi factura ficticia",
                }]}
            if ruta == "/reclamos/12/chat":
                self.assertEqual(_parametros["cliente_id"], 1)
                mensajes = [{"id": 1, "autor": "cliente", "texto": "No encuentro mi factura ficticia",
                             "tipo": "inicio"}]
                if estado["mensaje_cliente"]:
                    mensajes.append({"id": 2, "autor": "cliente", "texto": estado["mensaje_cliente"],
                                     "tipo": "mensaje"})
                if estado["revisado"]:
                    mensajes.append({"id": 3, "autor": "soporte", "texto": "Respuesta revisada por soporte",
                                     "tipo": "revision"})
                return {"mensajes": mensajes, "fotos": [], "ticket_id": 12,
                        "estado": "resuelto" if estado["revisado"] else "abierto"}
            raise AssertionError(ruta)

        def post(ruta, cuerpo=None, **_opciones):
            if ruta == "/pedidos":
                self.assertEqual(cuerpo["producto_id"], "PR-001")
                estado["pedidos"].append({
                    "id": 7, "producto": producto["nombre"],
                    "cantidad": 1, "total": producto["precio"],
                    "estado_envio": "en preparación",
                    "entrega_estimada": "2026-12-02T00:00:00Z",
                })
                return {"id": 7}
            if ruta == "/reclamos/12/mensajes/cliente":
                estado["mensaje_cliente"] = cuerpo["texto"]
                return {"id": 5}
            raise AssertionError(ruta)

        with patch("api_client.get", side_effect=get), patch("api_client.post", side_effect=post):
            app = AppTest.from_file(
                Path(__file__).with_name("cliente_app.py"), default_timeout=10,
            )
            app.run()
            next(b for b in app.button if b.label == "Comprar").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(any("Pedido ficticio #7" in x.value for x in app.success))

            self.assertTrue(any("Pedido #7" in x.value for x in app.subheader))

            next(b for b in app.button if b.label == "Abrir chat del pedido").click().run()
            self.assertEqual(len(app.chat_input), 1)
            app.chat_input[0].set_value("Sí").run()
            self.assertEqual(estado["mensaje_cliente"], "Sí")
            estado["revisado"] = True
            app.run()
            self.assertTrue(any("Respuesta revisada por soporte" in x.proto.body
                                for x in app.get("html")))
            self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
