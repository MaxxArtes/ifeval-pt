"""IFEval-pt: segue instrucao verificavel por codigo, sem juiz e sem GPU.

CORRECAO 31/07: IFEval em portugues EXISTE — amalia-llm/IFEval-mt-pt (541 itens, pt-PT,
PROPOR 2026), Polygl0t/IFEval-PT (300, traduzido por Qwen2.5-32B), a fatia pt do
facebook/Multi-IF (524, CC-BY-NC) e akawaai/Portuguese-IFEval (618). A afirmacao anterior
("nao existe") era FALSA e chegou a entrar em documento e em rascunho de candidatura.

O que de fato nao existe, e e a alegacao defensavel: (a) IFEval pt-BR NATIVO dentro do
lm-evaluation-harness; (b) dataset no HF com a tag pt-BR; (c) restricoes especificas da
LINGUA portuguesa — crase, mesoclise, enclise/proclise, "por que" vs "porque". Os que
existem sao traducao do conjunto ingles, entao testam ingles vertido, nao portugues.
E ai que este arquivo tem valor proprio; como "mais uma traducao", nao teria.

  POCKET_LM_API_KEY=... python3 ifeval_pt.py --url http://127.0.0.1:8090/v1 \
      --modelo pocket-lm-269m --saida out/ifeval.json

Duas notas, como no IFEval original (arXiv:2311.07911):
  - ESTRITA: a restricao vale no texto exatamente como veio.
  - FROUXA: vale depois de tirar marcacao de markdown, aspas e espaco sobrando —
    modelo pequeno erra por embrulhar a resposta, nao por desobedecer.

As restricoes foram escolhidas por serem verificaveis SEM ambiguidade em pt-BR. Contagem
de frase usa ponto/!/? seguidos de espaco ou fim; abreviacao comum ("Sr.", "etc.") esta
na lista de excecao, senao a contagem infla e o modelo e reprovado por erro do medidor.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
import urllib.request

ABREV = ["sr.", "sra.", "dr.", "dra.", "etc.", "ex.", "p.ex.", "n.", "av.", "prof."]


def sem_acento(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t)
                   if unicodedata.category(c) != "Mn").lower()


def limpa_frouxo(t: str) -> str:
    """Tira embrulho que nao e desobediencia: markdown, aspas, espaco sobrando."""
    t = re.sub(r"[*_`#>]+", "", t)
    t = t.strip().strip('"').strip("'").strip()
    return re.sub(r"[ \t]+", " ", t)


def conta_frases(t: str) -> int:
    t = t.strip()
    if not t:
        return 0
    marcado = t
    for a in ABREV:
        marcado = re.sub(re.escape(a), a.replace(".", "\x00"), marcado,
                         flags=re.IGNORECASE)
    partes = [p for p in re.split(r"[.!?]+(?:\s|$)", marcado) if p.strip()]
    return len(partes)


def conta_palavras(t: str) -> int:
    return len(re.findall(r"\b[\wÀ-ÿ]+\b", t))


# --- verificadores. Cada um recebe (resposta, params) e devolve bool -----------------
def v_max_frases(r, p):
    return 0 < conta_frases(r) <= p["n"]


def v_max_palavras(r, p):
    return 0 < conta_palavras(r) <= p["n"]


def v_min_palavras(r, p):
    return conta_palavras(r) >= p["n"]


def v_contem(r, p):
    return sem_acento(p["palavra"]) in sem_acento(r)


def v_contem_n_vezes(r, p):
    return sem_acento(r).count(sem_acento(p["palavra"])) >= p["n"]


def v_nao_contem(r, p):
    return sem_acento(p["palavra"]) not in sem_acento(r)


def v_comeca_com(r, p):
    return sem_acento(r.lstrip()).startswith(sem_acento(p["texto"]))


def v_termina_com(r, p):
    return sem_acento(r.rstrip().rstrip(".")).endswith(sem_acento(p["texto"]).rstrip("."))


def v_n_linhas(r, p):
    return len([l for l in r.strip().splitlines() if l.strip()]) == p["n"]


def v_minusculas(r, p):
    letras = [c for c in r if c.isalpha()]
    return bool(letras) and all(c.islower() for c in letras)


def v_so_uma_palavra(r, p):
    return conta_palavras(r) == 1




# --- restricoes da LINGUA portuguesa -------------------------------------------------
# Estas nao existem no IFEval ingles nem nas traducoes dele, e sao a razao de este
# benchmark existir. Todas verificaveis sem ambiguidade: ou o padrao esta la, ou nao.

RE_MESOCLISE = re.compile(
    r"\w+-(me|te|se|lhe|nos|vos|lhes|lo|la|los|las|o|a|os|as)-"
    r"(ei|á|ás|ão|emos|eis|ia|ias|íamos|iam|íeis)\b", re.IGNORECASE)
# proclise e OBRIGATORIA depois de palavra atrativa — a regra e o proprio teste
RE_PROCLISE = re.compile(
    r"\b(não|nunca|jamais|que|quem|quando|onde|se|também|todos|ninguém|nada)\s+"
    r"(me|te|se|lhe|nos|vos|lhes|o|a|os|as)\s+\w+", re.IGNORECASE)
RE_ENCLISE = re.compile(
    r"\w+-(me|te|se|lhe|nos|vos|lhes|lo|la|los|las)\b", re.IGNORECASE)
RE_TU = re.compile(r"\b(tu|te|ti|contigo|teu|tua|teus|tuas)\b", re.IGNORECASE)


def v_crase(r, p):
    """Exige crase. 'à'/'às' isolado ou iniciando palavra — 'à noite', 'às vezes'."""
    return bool(re.search(r"(?<![\wÀ-ÿ])[Àà]s?(?![\wÀ-ÿ])", r))


def v_sem_crase(r, p):
    return not v_crase(r, p)


def v_mesoclise(r, p):
    return bool(RE_MESOCLISE.search(r))


def v_proclise(r, p):
    return bool(RE_PROCLISE.search(r))


def v_enclise(r, p):
    """Enclise sem ser mesoclise: 'diga-me' conta, 'dar-lhe-ei' nao."""
    for m in RE_ENCLISE.finditer(r):
        if not RE_MESOCLISE.match(r[m.start():]):
            return True
    return False


def v_cedilha(r, p):
    return len([w for w in re.findall(r"[\wÀ-ÿ]+", r) if "ç" in w.lower()]) >= p["n"]


def v_sem_til(r, p):
    return not any(c in r for c in "ãõÃÕ")


def v_porque_ambos(r, p):
    b = r.lower()
    return ("por que" in b or "por quê" in b) and re.search(r"\bporque\b", b) is not None


def v_so_voce(r, p):
    """Tratamento consistente: 'você' presente e nenhuma forma de 'tu'."""
    return ("você" in r.lower() or "vocês" in r.lower()) and not RE_TU.search(r)


def v_sem_diacritico(r, p):
    return sem_acento(r) == r.lower()


def v_sem_digito(r, p):
    """Numero por extenso: nenhum algarismo na resposta."""
    return not any(c.isdigit() for c in r)


def v_agudo_e_circunflexo(r, p):
    return (any(c in r for c in "áéíóúÁÉÍÓÚ")
            and any(c in r for c in "âêôÂÊÔ"))


VERIF = {"max_frases": v_max_frases, "max_palavras": v_max_palavras,
         "min_palavras": v_min_palavras, "contem": v_contem,
         "contem_n_vezes": v_contem_n_vezes, "nao_contem": v_nao_contem,
         "comeca_com": v_comeca_com, "termina_com": v_termina_com,
         "n_linhas": v_n_linhas, "minusculas": v_minusculas,
         "so_uma_palavra": v_so_uma_palavra,
         # específicas do português
         "crase": v_crase, "sem_crase": v_sem_crase, "mesoclise": v_mesoclise,
         "proclise": v_proclise, "enclise": v_enclise, "cedilha": v_cedilha,
         "sem_til": v_sem_til, "porque_ambos": v_porque_ambos,
         "so_voce": v_so_voce, "sem_diacritico": v_sem_diacritico,
         "sem_digito": v_sem_digito, "agudo_e_circunflexo": v_agudo_e_circunflexo}

# 14 tarefas-base x 22 restricoes = 308 itens. O numero nao foi escolhido pelo total e
# sim por ITENS POR RESTRICAO: o IFEval original tem 541/25 ~ 21 por tipo, que e o que
# faz a tabela por-restricao significar alguma coisa. Com n=100 o IC 95% de uma taxa de
# 35% e +-9,5 pontos; com n=300 cai para +-5,5. E os 100 anteriores nao eram 100 itens
# independentes: eram produto cartesiano de 10x10. As tarefas sao coisas que um 269M pt-BR
# tem chance de responder; o teste e sobre OBEDECER, nao sobre saber.
TAREFAS = [
    "Explique o que é reciclagem.",
    "Fale sobre a importância de beber água.",
    "Descreva como fazer um café coado.",
    "Conte o que se faz numa feira livre.",
    "Explique por que é bom caminhar todo dia.",
    "Fale sobre o clima do Brasil.",
    "Descreva um dia de chuva na cidade.",
    "Explique para que serve uma geladeira.",
    "Fale sobre a importância de dormir cedo.",
    "Descreva como se planta uma árvore.",
    "Explique por que é bom guardar dinheiro.",
    "Fale sobre o que faz um professor.",
    "Descreva como se organiza uma mudança de casa.",
    "Explique o que acontece quando falta energia elétrica.",
]

RESTRICOES = [
    ("max_frases", {"n": 2}, "Responda em no máximo 2 frases."),
    ("max_frases", {"n": 1}, "Responda em exatamente uma frase."),
    ("max_palavras", {"n": 30}, "Use no máximo 30 palavras."),
    ("min_palavras", {"n": 40}, "Escreva pelo menos 40 palavras."),
    ("contem", {"palavra": "importante"}, "Use a palavra 'importante' na resposta."),
    ("contem_n_vezes", {"palavra": "água", "n": 2},
     "Cite a palavra 'água' pelo menos duas vezes."),
    ("nao_contem", {"palavra": "você"}, "Não use a palavra 'você' em nenhum momento."),
    ("comeca_com", {"texto": "Olha"}, "Comece a resposta exatamente com a palavra 'Olha'."),
    ("termina_com", {"texto": "espero ter ajudado"},
     "Termine a resposta com a frase 'Espero ter ajudado'."),
    ("minusculas", {}, "Escreva a resposta inteira em letras minúsculas."),
    # --- específicas do português: é aqui que este benchmark deixa de ser tradução ---
    ("crase", {}, "Use crase pelo menos uma vez na resposta."),
    ("sem_crase", {}, "Não use crase em nenhum momento."),
    ("mesoclise", {}, "Use uma mesóclise na resposta, como em 'dar-lhe-ei'."),
    ("proclise", {}, "Use próclise depois de palavra atrativa, como em 'não me diga'."),
    ("enclise", {}, "Use ênclise na resposta, como em 'diga-me'."),
    ("cedilha", {"n": 3}, "Use pelo menos três palavras com a letra ç."),
    ("sem_til", {}, "Escreva a resposta inteira sem usar nenhum til (ã, õ)."),
    ("porque_ambos", {}, "Use 'por que' e 'porque' na mesma resposta."),
    ("so_voce", {}, "Trate o leitor por 'você' e nunca por 'tu'."),
    ("sem_diacritico", {}, "Escreva a resposta inteira sem nenhum acento ou cedilha."),
    ("sem_digito", {}, "Escreva todos os números por extenso, sem algarismos."),
    ("agudo_e_circunflexo", {},
     "Use na resposta pelo menos uma palavra com acento agudo e uma com circunflexo."),
]


def itens() -> list[dict]:
    saida = []
    for i, tarefa in enumerate(TAREFAS):
        for j, (tipo, params, texto) in enumerate(RESTRICOES):
            saida.append({"id": f"{i:02d}-{j:02d}", "tipo": tipo, "params": params,
                          "prompt": f"{tarefa} {texto}"})
    return saida


def chama(url: str, modelo: str, prompt: str, chave: str, cfg: dict) -> str:
    corpo = json.dumps({"model": modelo,
                        "messages": [{"role": "user", "content": prompt}],
                        **cfg}).encode()
    cab = {"Content-Type": "application/json", "User-Agent": "pocket-lm-ifeval/1"}
    if chave:
        cab["Authorization"] = f"Bearer {chave}"
    req = urllib.request.Request(url.rstrip("/") + "/chat/completions",
                                 data=corpo, headers=cab)
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.load(r)
    return (d["choices"][0]["message"].get("content") or "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("POCKET_LM_URL",
                                                    "http://127.0.0.1:8090/v1"))
    ap.add_argument("--modelo", default="pocket-lm")
    ap.add_argument("--temp", type=float, default=0.3)
    ap.add_argument("--max-tokens", type=int, default=300)
    ap.add_argument("--saida", default=None)
    ap.add_argument("--rotulo", default="sem-rotulo")
    ap.add_argument("--limite", type=int, default=0, help="0 = todos os itens (308)")
    a = ap.parse_args()

    cfg = {"temperature": a.temp, "max_tokens": a.max_tokens, "top_p": 0.9,
           "seed": 11, "stream": False}
    chave = os.environ.get("POCKET_LM_API_KEY", "")
    lista = itens()
    if a.limite:
        lista = lista[:a.limite]

    res, erros = [], 0
    por_tipo: dict[str, list[int]] = {}
    t0 = time.time()
    for k, it in enumerate(lista):
        try:
            txt = chama(a.url, a.modelo, it["prompt"], chave, cfg)
        except Exception as e:  # noqa: BLE001
            erros += 1
            print(json.dumps({"erro": type(e).__name__, "id": it["id"]}), flush=True)
            continue
        f = VERIF[it["tipo"]]
        estrita = bool(f(txt, it["params"]))
        frouxa = estrita or bool(f(limpa_frouxo(txt), it["params"]))
        res.append({**it, "resposta": txt, "estrita": estrita, "frouxa": frouxa})
        por_tipo.setdefault(it["tipo"], []).append(int(estrita))
        if (k + 1) % 25 == 0:
            print(json.dumps({"feitos": k + 1,
                              "min": round((time.time() - t0) / 60, 1)}), flush=True)

    if not res:
        print(json.dumps({"erro": "nada avaliado", "erros": erros}))
        return 2
    resumo = {
        "rotulo": a.rotulo, "n": len(res), "erros": erros,
        "estrita": round(sum(x["estrita"] for x in res) / len(res), 4),
        "frouxa": round(sum(x["frouxa"] for x in res) / len(res), 4),
        "por_restricao": {t: f"{sum(v)}/{len(v)}" for t, v in sorted(por_tipo.items())},
        "minutos": round((time.time() - t0) / 60, 1),
    }
    if a.saida:
        os.makedirs(os.path.dirname(a.saida) or ".", exist_ok=True)
        with open(a.saida, "w", encoding="utf-8") as f:
            json.dump({"resumo": resumo, "itens": res}, f, ensure_ascii=False, indent=1)
    print(json.dumps(resumo, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
