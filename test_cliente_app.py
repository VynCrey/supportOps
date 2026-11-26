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
                return {"clientes": [{"id": 1, "nombre": "Cliente demo", "plan": "Basic"}]}
            if ruta == "/productos":
                return {"productos": [producto]}
            if ruta == "/pedidos":
                return {"pedidos": estado["pedidos"]}
            if ruta == "/reclamos":
                return {"reclamos": [{
                    "id": 4, "ticket_id": 12, "estado": "abierto",
                    "producto": None, "texto": "No encuentro mi factura ficticia",
                }]}
            if ruta == "/reclamos/12/respuesta":
                return ({"estado": "respondido", "texto": "Respuesta revisada por soporte",
                         "version": 1, "corregida": False} if estado["revisado"]
                        else {"estado": "pendiente", "texto": "BORRADOR INTERNO"})
            if ruta == "/reclamos/12/mensajes":
                mensajes = [{"autor": "cliente", "texto": "No encuentro mi factura ficticia",
                             "tipo": "inicio"}]
                if estado["mensaje_cliente"]:
                    mensajes.append({"autor": "cliente", "texto": estado["mensaje_cliente"],
                                     "tipo": "mensaje"})
                if estado["revisado"]:
                    mensajes.append({"autor": "soporte", "texto": "Respuesta revisada por soporte",
                                     "tipo": "revision"})
                return {"mensajes": mensajes}
            raise AssertionError(ruta)

        def post(ruta, cuerpo=None, **_opciones):
            if ruta == "/pedidos":
                self.assertEqual(cuerpo["producto_id"], "PR-001")
                estado["pedidos"].append({
                    "id": 7, "producto": producto["nombre"],
                    "cantidad": 1, "total": producto["precio"],
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
            next(b for b in app.button if b.label == "Comprar (simulado)").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(any("Pedido simulado #7" in x.value for x in app.success))

            app.radio[0].set_value("Mis pedidos").run()
            self.assertTrue(any("Pedido #7" in x.value for x in app.markdown))

            app.radio[0].set_value("Conversaciones").run()
            self.assertFalse(any("BORRADOR INTERNO" in x.value for x in app.markdown))
            app.chat_input[0].set_value("¿Me pueden ayudar con la factura?").run()
            self.assertEqual(estado["mensaje_cliente"], "¿Me pueden ayudar con la factura?")
            estado["revisado"] = True
            next(b for b in app.button if b.label == "Actualizar conversación").click().run()
            self.assertTrue(any("Respuesta revisada por soporte" in x.value
                                for x in app.markdown))
            self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
