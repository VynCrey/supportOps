"""Recuperacion de Marco sobre la base de conocimiento en PostgreSQL.

retrieve(query, category, tool) es el contrato de docs/contratos.md.
Las funciones de ranking (lexical, graph, rrf, buscar) reciben listas y no
tocan la base, asi se prueban sin PostgreSQL. Solo leer_kb() se conecta.

La contrasena no se guarda en ningun archivo. Cuando la API llama a retrieve,
psycopg la toma de la variable de entorno PGPASSWORD, que se define en la misma
terminal antes de arrancar run.py.
"""
import math
import re
import unicodedata
from collections import Counter

import psycopg
from psycopg.rows import dict_row

from settings import DB_HOST, DB_NAME, DB_PORT, DB_USER

HERRAMIENTAS = ("lexical", "grafo", "hibrido")

STOP = {'de', 'la', 'que', 'el', 'en', 'y', 'a', 'los', 'del', 'se', 'las', 'por', 'un', 'para', 'con', 'no', 'una', 'su', 
        'al', 'lo', 'como', 'más', 'pero', 'sus', 'le', 'ya', 'o', 'este', 'sí', 'porque', 'esta', 'entre', 'cuando', 'muy', 
        'sin', 'sobre', 'mi','desde','hoy','necesito','ayuda'}


def tokens(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return [w for w in re.findall(r"\w+", text) if w not in STOP]


def leer_kb(clave: str | None = None) -> tuple[list[dict], list[dict]]:
    """Lee documentos y relaciones. Sin clave usa PGPASSWORD."""
    parametros = {"host": DB_HOST, "port": DB_PORT, "dbname": DB_NAME,
                  "user": DB_USER, "row_factory": dict_row}
    if clave is not None:
        parametros["password"] = clave
    try:
        conexion = psycopg.connect(**parametros)
    except psycopg.OperationalError as error:
        # ConnectionError hace que la API responda 503 y no guarde la ejecucion.
        raise ConnectionError(
            "No se pudo leer la base de conocimiento. Defini PGPASSWORD en "
            "esta terminal antes de arrancar la API."
        ) from error
    with conexion, conexion.cursor() as cursor:
        cursor.execute(
            "SELECT id, categoria, titulo, version, texto FROM documentos ORDER BY id")
        documentos = cursor.fetchall()
        cursor.execute("SELECT origen, relacion, destino FROM relaciones")
        relaciones = cursor.fetchall()
    return documentos, relaciones


def lexical(query: str, documentos: list[dict], k: int = 3) -> list[dict]:
    """TF-IDF con coseno. Devuelve lista vacia si ninguna palabra coincide."""
    bags = [Counter(tokens(d["titulo"] + " " + d["texto"])) for d in documentos]
    df = Counter(w for bag in bags for w in bag)

    def vector(bag):
        return {w: n * (math.log((1 + len(documentos)) / (1 + df[w])) + 1)
                for w, n in bag.items() if w in df}

    def norm(v):
        return math.sqrt(sum(x * x for x in v.values())) or 1

    q = vector(Counter(tokens(query)))
    scored = []
    for d, bag in zip(documentos, bags):
        v = vector(bag)
        score = sum(x * v.get(w, 0) for w, x in q.items()) / (norm(q) * norm(v))
        if score > 0:
            scored.append(dict(d, score=round(score, 6)))
    return sorted(scored, key=lambda d: (-d["score"], d["id"]))[:k]


def graph(category: str, documentos: list[dict], relaciones: list[dict],
          k: int = 3) -> list[dict]:
    """Documentos que la categoria documenta, en orden de ID."""
    por_id = {d["id"]: d for d in documentos}
    ids = sorted(r["destino"] for r in relaciones
                 if r["origen"] == f"categoria:{category}"
                 and r["relacion"] == "documenta" and r["destino"] in por_id)
    return [dict(por_id[i], score=0.0) for i in ids[:k]]


def rrf(*rankings: list[dict], k: int = 3) -> list[dict]:
    """Reciprocal Rank Fusion: suma 1/(60+posicion) de cada ranking."""
    scores, docs = {}, {}
    for ranking in rankings:
        for rank, doc in enumerate(ranking, 1):
            key = doc["id"]
            docs[key] = doc
            scores[key] = scores.get(key, 0) + 1 / (60 + rank)
    keys = sorted(scores, key=lambda key: (-scores[key], key))[:k]
    return [dict(docs[key], fusion_score=scores[key]) for key in keys]


def buscar(query: str, category: str, tool: str, documentos: list[dict],
           relaciones: list[dict]) -> list[dict]:
    if tool == "lexical":
        return lexical(query, documentos)
    if tool == "grafo":
        return graph(category, documentos, relaciones)
    if tool == "hibrido":
        return rrf(lexical(query, documentos), graph(category, documentos, relaciones))
    raise ValueError("Herramienta no permitida")


def retrieve(query: str, category: str, tool: str) -> list[dict]:
    if tool not in HERRAMIENTAS:
        raise ValueError("Herramienta no permitida")   # antes de tocar la base
    documentos, relaciones = leer_kb()
    return buscar(query, category, tool, documentos, relaciones)
