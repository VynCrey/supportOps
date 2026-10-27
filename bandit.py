"""P10: bandit contextual que elige la herramienta de busqueda, con cinco semillas,
comparado contra la MEJOR politica fija.
Uso:  python bandit.py            usa las latencias guardadas (o las mide si no hay)
      python bandit.py --medir    vuelve a medir las latencias y las guarda

Entrenamiento: los titulos de los procedimientos de kb.json (sin "Guia operador"
ni "FAQ cliente"). Prueba: las 15 consultas con respuesta de docs/eval/consultas.csv,
que se escribieron antes de medir y no se usan para entrenar.
Recompensa: 1 si el documento correcto esta en el top-3, menos el costo de la
herramienta. El costo sale de la latencia medida en esta maquina, no de un numero
elegido a mano. La medicion se guarda en docs/eval/latencias.json y se reutiliza,
porque entre lexical e hibrido la diferencia esta dentro del ruido: medir de nuevo en
cada corrida podia cambiar el resultado. Guarda todo en docs/eval/bandit_semillas.json.
"""
import json
import random
import sys
import time
from pathlib import Path
from statistics import mean, pstdev

from cargar_kb import leer_archivo
from evaluar import ENTRADA, cargar
from retrieval import buscar

RAIZ = Path(__file__).resolve().parent
SALIDA = RAIZ / "docs" / "eval" / "bandit_semillas.json"
LATENCIAS = RAIZ / "docs" / "eval" / "latencias.json"
ACCIONES = ("lexical", "grafo", "hibrido")
SEMILLAS = (1, 7, 13, 42, 99)
EPISODIOS = 500
EXPLORACION = 0.2
# El costo maximo queda muy por debajo de un acierto (1): la latencia solo desempata.
COSTO_MAXIMO = 0.05


def casos_entrenamiento(kb):
    """Un caso por procedimiento: el titulo como consulta y sus versiones como respuesta."""
    retirados = {r["destino"] for r in kb["relaciones"] if r["relacion"] == "reemplaza_a"}
    por_titulo = {}
    for d in kb["documentos"]:
        if d["categoria"] == "general" or d["id"] in retirados:
            continue
        titulo = d["titulo"].split(" - ")[0]
        por_titulo.setdefault((titulo, d["categoria"]), set()).add(d["id"])
    return [(titulo, cat, ids) for (titulo, cat), ids in sorted(por_titulo.items())]


def casos_prueba():
    return [(r["texto"], r["categoria_esperada"], r["fuentes"])
            for r in cargar(ENTRADA) if not r["abstencion"]]


def medir_latencias(casos, kb, repeticiones=20, rondas=7):
    """Milisegundos por consulta de cada herramienta, en esta maquina.
    Una vuelta de calentamiento y despues varias rondas, cada una en otro orden; de
    cada herramienta se queda el minimo, que es la medida menos contaminada por otras
    tareas de la maquina. Medir una sola vez y en orden fijo hacia que la primera
    herramienta saliera mas lenta solo por ir primera."""
    def una_vez(accion):
        inicio = time.perf_counter()
        for _ in range(repeticiones):
            for texto, cat, _ids in casos:
                buscar(texto, cat, accion, kb["documentos"], kb["relaciones"])
        return (time.perf_counter() - inicio) * 1000 / (repeticiones * len(casos))

    for accion in ACCIONES:
        una_vez(accion)                       # calentamiento, no se cuenta
    ms = {a: float("inf") for a in ACCIONES}
    for ronda in range(rondas):
        orden = ACCIONES[ronda % 3:] + ACCIONES[:ronda % 3]
        for accion in orden:
            ms[accion] = min(ms[accion], una_vez(accion))
    return ms


def estado(texto, categoria):
    return categoria + ("::codigo" if any(c.isdigit() for c in texto) else "::texto")


def entrenar(semilla, casos, kb, costo):
    rng = random.Random(semilla)
    q, cuenta = {}, {}
    for _ in range(EPISODIOS):
        texto, cat, esperados = rng.choice(casos)
        s = estado(texto, cat)
        q.setdefault(s, {a: 0.0 for a in ACCIONES})
        if rng.random() < EXPLORACION:
            accion = rng.choice(ACCIONES)
        else:
            accion = max(ACCIONES, key=lambda a: q[s][a])
        docs = buscar(texto, cat, accion, kb["documentos"], kb["relaciones"])[:3]
        recompensa = float(bool(esperados & {d["id"] for d in docs})) - costo[accion]
        clave = (s, accion)
        cuenta[clave] = cuenta.get(clave, 0) + 1
        # Media incremental de la recompensa de esa accion en ese estado.
        q[s][accion] += (recompensa - q[s][accion]) / cuenta[clave]
    return q


def politica(q):
    def elegir(texto, cat):
        fila = q.get(estado(texto, cat))
        return max(ACCIONES, key=lambda a: fila[a]) if fila else "hibrido"
    return elegir


def evaluar_politica(elegir, casos, kb, costo):
    aciertos, reciproco, recompensa, acciones = 0, 0.0, 0.0, []
    for texto, cat, esperados in casos:
        accion = elegir(texto, cat)
        ids = [d["id"] for d in buscar(texto, cat, accion, kb["documentos"], kb["relaciones"])[:3]]
        posiciones = [i for i, x in enumerate(ids, 1) if x in esperados]
        aciertos += bool(posiciones)
        reciproco += 1 / min(posiciones) if posiciones else 0
        recompensa += float(bool(posiciones)) - costo[accion]
        acciones.append(accion)
    n = len(casos)
    return {"hit_at_3": aciertos / n, "mrr_at_3": reciproco / n,
            "recompensa_media": recompensa / n, "acciones": acciones}


def main():
    kb = leer_archivo()
    entrenamiento, prueba = casos_entrenamiento(kb), casos_prueba()
    if LATENCIAS.exists() and "--medir" not in sys.argv:
        ms = json.loads(LATENCIAS.read_text(encoding="utf-8"))["ms"]
        origen = f"guardadas en {LATENCIAS.relative_to(RAIZ)}"
    else:
        ms = medir_latencias(prueba, kb)
        LATENCIAS.write_text(json.dumps({"ms": ms, "metodo": "minimo de 7 rondas de 20 "
                             "repeticiones, orden rotado, con calentamiento"}, indent=2),
                             encoding="utf-8")
        origen = f"medidas ahora y guardadas en {LATENCIAS.relative_to(RAIZ)}"
    costo = {a: COSTO_MAXIMO * ms[a] / max(ms.values()) for a in ACCIONES}
    print(f"entrenamiento: {len(entrenamiento)} procedimientos · prueba: {len(prueba)} consultas")
    print(f"latencia (ms por consulta), {origen}, y costo:")
    for a in ACCIONES:
        print(f"  {a:8s} {ms[a]:7.3f} ms   costo {costo[a]:.4f}")
    margen = (ms["hibrido"] - ms["lexical"]) / ms["lexical"]
    print(f"  hibrido vs lexical: {margen:+.1%}")
    if abs(margen) < 0.05:
        print("  AVISO: menos del 5 % de diferencia. Si las dos aciertan igual en el "
              "entrenamiento, el desempate entre ellas depende del ruido de la medicion.")

    fijas = {a: evaluar_politica(lambda t, c, a=a: a, prueba, kb, costo) for a in ACCIONES}
    print("\npoliticas fijas (no dependen de la semilla)")
    for a, m in fijas.items():
        print(f"  {a:8s} hit@3={m['hit_at_3']:.4f}  mrr@3={m['mrr_at_3']:.4f}  "
              f"recompensa={m['recompensa_media']:.4f}")
    mejor = max(fijas, key=lambda a: (fijas[a]["hit_at_3"], fijas[a]["recompensa_media"]))
    print(f"  mejor politica fija: {mejor}\n")

    corridas = []
    for semilla in SEMILLAS:
        q = entrenar(semilla, entrenamiento, kb, costo)
        m = evaluar_politica(politica(q), prueba, kb, costo)
        m["semilla"], m["tabla_q"] = semilla, q
        corridas.append(m)
        usadas = {a: m["acciones"].count(a) for a in ACCIONES if a in m["acciones"]}
        print(f"semilla {semilla:>3}: hit@3={m['hit_at_3']:.4f}  "
              f"recompensa={m['recompensa_media']:.4f}  acciones={usadas}")

    print("\nbandit sobre 5 semillas (media +/- desvio)")
    for clave in ("hit_at_3", "mrr_at_3", "recompensa_media"):
        vals = [m[clave] for m in corridas]
        print(f"  {clave:17s} {mean(vals):.4f} +/- {pstdev(vals):.4f}")
    delta = mean(m["hit_at_3"] for m in corridas) - fijas[mejor]["hit_at_3"]
    print(f"\ndiferencia de Hit@3 contra la mejor politica fija ({mejor}): {delta:+.4f}")
    print("Si es 0 o negativa, el bandit NO mejora, y se reporta asi.")

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps({
        "semillas": list(SEMILLAS), "episodios": EPISODIOS, "exploracion": EXPLORACION,
        "n_entrenamiento": len(entrenamiento), "n_prueba": len(prueba),
        "latencia_ms": ms, "costo": costo,
        "margen_hibrido_vs_lexical": (ms["hibrido"] - ms["lexical"]) / ms["lexical"], "mejor_politica_fija": mejor,
        "fijas": {a: {k: v for k, v in m.items() if k != "acciones"} for a, m in fijas.items()},
        "bandit": corridas, "diferencia_hit_at_3": delta,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"guardado en {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
