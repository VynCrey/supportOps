"""Evaluacion de la recuperacion (P7): Hit@3, MRR@3 y abstencion por herramienta.
Uso:  python evaluar.py            las tres herramientas
      python evaluar.py lexical    solo una

Lee docs/eval/consultas.csv y kb.json, y escribe docs/eval/resultados.csv con una
fila por consulta y herramienta. No necesita PostgreSQL: usa las mismas funciones
de ranking que retrieve(), sobre la misma KB que se carga en la base.
"""
import csv
import hashlib
import sys
from datetime import date
from pathlib import Path

from cargar_kb import KB, leer_archivo
from retrieval import buscar

RAIZ = Path(__file__).resolve().parent
HERRAMIENTAS = ("lexical", "grafo", "hibrido")
K = 3
ENTRADA = RAIZ / "docs" / "eval" / "consultas.csv"
SALIDA = RAIZ / "docs" / "eval" / "resultados.csv"
# Como se escribieron en P6 (commit 2bbfd46): E01-E10 normales, E11-E15 sinonimos.
SINONIMOS = {"E11", "E12", "E13", "E14", "E15"}


def cargar(path=ENTRADA):
    with open(path, encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    for r in filas:
        r["fuentes"] = {s.strip() for s in r["fuentes_aceptables"].split("|") if s.strip()}
        r["abstencion"] = r["abstencion"].strip().lower() in ("si", "sí", "true", "1")
    return filas


def medir(filas, tool, documentos, relaciones, k=K):
    detalle, fallos = [], []
    for r in filas:
        # El grafo recibe la categoria esperada, no la del triage: su resultado es
        # un techo. En el sistema real depende de que el triage acierte.
        docs = buscar(r["texto"], r["categoria_esperada"], tool, documentos, relaciones)[:k]
        ids = [d["id"] for d in docs]
        if r["abstencion"]:
            # Abstenerse = no ofrecer ningun procedimiento especifico. Devolver solo
            # politicas generales (o nada) cuenta como abstencion.
            acierto, posicion = all(d["categoria"] == "general" for d in docs), ""
            tipo = "abstencion"
        else:
            posiciones = [i for i, x in enumerate(ids, 1) if x in r["fuentes"]]
            acierto, posicion = bool(posiciones), (min(posiciones) if posiciones else "")
            tipo = "sinonimo" if r["id"] in SINONIMOS else "normal"
        if not acierto:
            fallos.append((r["id"], tipo, r["texto"], ids or ["(vacio)"]))
        detalle.append({"herramienta": tool, "id": r["id"], "tipo": tipo,
                        "devuelto": "|".join(ids), "acierto": acierto, "posicion": posicion})
    return detalle, fallos


def resumir(detalle, tipos):
    filas = [d for d in detalle if d["tipo"] in tipos]
    n = len(filas) or 1
    hit = sum(d["acierto"] for d in filas) / n
    mrr = sum(1 / d["posicion"] for d in filas if d["posicion"]) / n
    return len(filas), hit, mrr


def main(tools=HERRAMIENTAS):
    filas = cargar()
    kb = leer_archivo()
    huella = hashlib.sha256(KB.read_bytes()).hexdigest()[:8]
    con_respuesta = sum(not r["abstencion"] for r in filas)
    print(f"{date.today():%d/%m/%Y} · KB: {len(kb['documentos'])} documentos, "
          f"{len(kb['relaciones'])} relaciones (kb.json {huella}) · k={K}")
    print(f"{len(filas)} consultas: {con_respuesta} con respuesta esperada "
          f"({con_respuesta - len(SINONIMOS & {r['id'] for r in filas})} normales, "
          f"{len(SINONIMOS & {r['id'] for r in filas})} sinonimos), "
          f"{len(filas) - con_respuesta} de abstencion\n")
    print(f"{'herramienta':12s} {'Hit@3':>7} {'MRR@3':>7} {'Hit@3 norm.':>12} "
          f"{'Hit@3 sinon.':>13} {'abstiene':>9}")
    todo, todos_fallos = [], {}
    for tool in tools:
        detalle, fallos = medir(filas, tool, kb["documentos"], kb["relaciones"])
        todo += detalle
        todos_fallos[tool] = fallos
        _, hit, mrr = resumir(detalle, {"normal", "sinonimo"})
        _, hit_n, _ = resumir(detalle, {"normal"})
        _, hit_s, _ = resumir(detalle, {"sinonimo"})
        _, abst, _ = resumir(detalle, {"abstencion"})
        print(f"{tool:12s} {hit:>7.2f} {mrr:>7.2f} {hit_n:>12.2f} {hit_s:>13.2f} {abst:>8.0%}")
    for tool, fallos in todos_fallos.items():
        if fallos:
            print(f"\nfallos de {tool}:")
            for cid, tipo, texto, ids in fallos:
                print(f"  {cid} ({tipo})  \"{texto}\"  ->  {', '.join(ids)}")
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with open(SALIDA, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["herramienta", "id", "tipo", "devuelto",
                                          "acierto", "posicion"])
        w.writeheader()
        w.writerows(todo)
    print(f"\ndetalle por consulta en {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main(tuple(sys.argv[1:]) or HERRAMIENTAS)
