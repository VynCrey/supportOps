import unittest
from urllib.error import URLError

from pydantic import ValidationError

from analysis import TicketNoEncontrado, analyze, aplicar_gate
from db import SupportOpsDB
from main import NuevaRevision
from safety import pide_credenciales


class DatosDePrueba:
    def __init__(self, ticket=True):
        self.ticket = {
            "id": 3,
            "texto": "La API devuelve error 401 con el token",
            "plan": "Enterprise",
            "prioridad": "alta",
            "categoria_real": "api",
            "familia": "api-demo",
        } if ticket else None
        self.guardados = []

    def obtener_ticket(self, ticket_id):
        return self.ticket

    def guardar_ejecucion(self, ticket_id, resultado):
        self.guardados.append(resultado)
        return len(self.guardados)


class AnalisisTest(unittest.TestCase):
    def test_flujo_guarda_traza_sin_filtrar_etiqueta_real(self):
        datos = DatosDePrueba()
        entradas = []

        def llm(rol, payload, esquema):
            entradas.append(payload)
            claves = set(esquema["properties"])
            if "categoria" in claves:
                return {"categoria": "api", "consulta": "error 401", "faltantes": []}
            if "herramienta" in claves:
                return {"herramienta": "lexical", "consulta": "error 401", "motivo": "Codigo exacto"}
            if "citas" in claves:
                return {
                    "texto": "Revisar el error sin compartir el token.",
                    "citas": ["KB-013"],
                    "preguntas": [],
                }
            return {"decision": "listo", "motivos": []}

        def recuperar(query, category, tool):
            self.assertEqual((query, category, tool), ("error 401", "api", "lexical"))
            return [{"id": "KB-013", "titulo": "Error 401", "texto": "Revisar el error."}]

        resultado = analyze(3, datos, llm=llm, recuperar=recuperar)
        self.assertEqual(resultado["ejecucion_id"], 1)
        self.assertEqual(len(resultado["traza"]), 5)
        self.assertEqual(resultado["supervision"]["decision"], "listo")
        self.assertNotIn("ejecucion_id", datos.guardados[0])
        self.assertTrue(all("categoria_real" not in str(entrada) for entrada in entradas))
        self.assertTrue(all("familia" not in str(entrada) for entrada in entradas))

    def test_sin_evidencia_obliga_revision(self):
        self.assertEqual(
            aplicar_gate(
                {"texto": "Necesito mas datos", "citas": []},
                [],
                "api",
                {"decision": "listo", "motivos": []},
            )["decision"],
            "revisar",
        )

    def test_cita_inventada_bloquea(self):
        self.assertEqual(
            aplicar_gate(
                {"texto": "Hacer algo", "citas": ["KB-INVENTADA"]},
                [{"id": "KB-013"}],
                "api",
                {"decision": "listo", "motivos": []},
            )["decision"],
            "bloquear",
        )

    def test_pedido_de_token_del_modelo_real_bloquea(self):
        borrador = {
            "texto": "La API devuelve error 401 con el token",
            "citas": [],
            "preguntas": [
                "¿Puede proporcionar el ID de la API y el token que está utilizando?"
            ],
        }
        gate = aplicar_gate(
            borrador, [], "general", {"decision": "revisar", "motivos": []},
            ["token específico"],
        )
        self.assertEqual(gate["decision"], "bloquear")
        self.assertIn("credenciales", gate["motivos"][0])

    def test_advertencia_de_no_compartir_token_es_segura(self):
        self.assertFalse(pide_credenciales({
            "texto": "No compartas tu token. Indicá la hora del error.",
            "preguntas": ["¿A qué hora ocurrió el error 401?"],
        }))

    def test_mencionar_token_para_diagnostico_no_bloquea(self):
        borrador = {
            "texto": "Revisar vencimiento del token y entorno configurado.",
            "citas": ["KB-013"],
            "preguntas": ["Revisar vencimiento del token y entorno configurado."],
        }
        faltantes = ["Estado del token, sin compartir su valor"]
        self.assertFalse(pide_credenciales(borrador, faltantes))
        resultado = aplicar_gate(
            borrador, [{"id": "KB-013"}], "api",
            {"decision": "revisar", "motivos": []}, faltantes,
        )
        self.assertEqual(resultado["decision"], "revisar")

    def test_pedido_explicito_de_token_sigue_bloqueado(self):
        self.assertTrue(pide_credenciales({
            "texto": "Consultar el error 401.",
            "preguntas": ["Enviame tu token."],
        }))
        self.assertTrue(pide_credenciales(
            {"texto": "Consultar el error 401.", "preguntas": []},
            ["Solicitar la clave de acceso"],
        ))

    def test_otras_formas_de_pedir_secretos_bloquean(self):
        pedidos = [
            "¿Cuál es tu token?",
            "Decime tu token",
            "Compartí tu token conmigo",
            "Escribí acá tu clave",
            "¿Me das el código de verificación?",
        ]

        for pedido in pedidos:
            with self.subTest(pedido=pedido):
                self.assertTrue(pide_credenciales({
                    "texto": "Estamos revisando el problema.",
                    "preguntas": [pedido],
                }))

        self.assertFalse(pide_credenciales({
            "texto": "Revisar vencimiento del token.",
            "preguntas": [],
        }))

    def test_motivo_de_ejemplo_se_rechaza(self):
        with self.assertRaises(ValidationError):
            NuevaRevision(decision="rechazar", motivo=" string ")

    def test_ejecucion_antigua_insegura_no_puede_aprobarse(self):
        resultado = {
            "supervision": {"decision": "revisar"},
            "triage": {"faltantes": ["token específico"]},
            "borrador": {
                "texto": "La API devuelve error 401",
                "preguntas": ["¿Puede proporcionar el token que utiliza?"],
            },
        }

        class ConexionFalsa:
            def __init__(self):
                self.consultas = []

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def cursor(self):
                return self

            def execute(self, consulta, parametros):
                self.consultas.append(consulta)

            def fetchone(self):
                return {"resultado": resultado} if len(self.consultas) == 1 else None

        conexion = ConexionFalsa()
        datos = SupportOpsDB("clave-falsa")
        datos.conectar = lambda: conexion

        with self.assertRaisesRegex(ValueError, "solo puede rechazarse"):
            datos.guardar_revision(1, "aprobar", "", "Revisado")
        self.assertFalse(any("INSERT INTO revisiones" in sql for sql in conexion.consultas))

    def test_ejecucion_antigua_muestra_alerta_al_consultarla(self):
        respuestas = iter([
            {
                "id": 1,
                "resultado": {
                    "triage": {"faltantes": ["token específico"]},
                    "borrador": {"preguntas": ["¿Puede proporcionar el token?"]},
                },
            },
            None,
        ])

        class ConexionFalsa:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def cursor(self): return self
            def execute(self, consulta, parametros): pass
            def fetchone(self): return next(respuestas)

        datos = SupportOpsDB("clave-falsa")
        datos.conectar = ConexionFalsa
        ejecucion = datos.obtener_ejecucion(1)
        self.assertIn("solo puede rechazarse", ejecucion["alerta_seguridad"])

    def test_ticket_inexistente_no_llama_modelo_ni_guarda(self):
        datos = DatosDePrueba(ticket=False)

        def llm(*args):
            self.fail("No debe llamar al modelo")

        with self.assertRaises(TicketNoEncontrado):
            analyze(999, datos, llm=llm)
        self.assertEqual(datos.guardados, [])

    def test_modelo_caido_no_guarda_una_ejecucion_ficticia(self):
        datos = DatosDePrueba()

        def llm(*args):
            raise URLError("Servicio local apagado")

        with self.assertRaises(URLError):
            analyze(3, datos, llm=llm)
        self.assertEqual(datos.guardados, [])

    def test_salida_invalida_no_guarda(self):
        datos = DatosDePrueba()

        def llm(*args):
            return {"categoria": "api"}

        with self.assertRaises(ValueError):
            analyze(3, datos, llm=llm)
        self.assertEqual(datos.guardados, [])


if __name__ == "__main__":
    unittest.main()