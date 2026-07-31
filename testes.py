"""Testes dos verificadores. Rode antes de confiar em qualquer número:

    python3 testes.py

Cada caso é um texto fabricado à mão com a resposta esperada. Se um verificador aceitar
o que deveria recusar, o benchmark inteiro vira ruído — por isso os casos difíceis estão
aqui de propósito (abreviação que parece fim de frase, palavra proibida escrita com
acento, mesóclise contra ênclise).
"""
from __future__ import annotations

import sys

from ifeval_pt import VERIF, limpa_frouxo, conta_frases, conta_palavras, itens

CASOS = [
    # --- genéricos ---
    ("max_frases", {"n": 2}, "Reciclagem é reaproveitar material. Ajuda o planeta.", True),
    ("max_frases", {"n": 2}, "Uma. Duas. Três.", False),
    ("max_frases", {"n": 2}, "O Sr. João reciclou etc. hoje.", True),
    ("max_palavras", {"n": 5}, "Reciclar é bom para todos.", True),
    ("max_palavras", {"n": 3}, "Reciclar é bom para todos.", False),
    ("min_palavras", {"n": 5}, "Curta demais.", False),
    ("contem", {"palavra": "importante"}, "É muito IMPORTANTE reciclar.", True),
    ("contem", {"palavra": "água"}, "Beba água sempre.", True),
    ("contem", {"palavra": "água"}, "Beba agua sempre.", True),      # sem acento conta
    ("contem_n_vezes", {"palavra": "água", "n": 2}, "Água e água.", True),
    ("contem_n_vezes", {"palavra": "água", "n": 2}, "Só uma água.", False),
    ("nao_contem", {"palavra": "você"}, "Você deve reciclar.", False),
    ("nao_contem", {"palavra": "você"}, "Voce deve reciclar.", False),  # pega sem acento
    ("nao_contem", {"palavra": "você"}, "A pessoa deve reciclar.", True),
    ("comeca_com", {"texto": "Olha"}, "  Olha, é simples.", True),
    ("comeca_com", {"texto": "Olha"}, "Bom, olha, é simples.", False),
    ("termina_com", {"texto": "espero ter ajudado"}, "Pronto. Espero ter ajudado.", True),
    ("termina_com", {"texto": "espero ter ajudado"}, "Espero ter ajudado, viu?", False),
    ("minusculas", {}, "tudo em minúsculas aqui.", True),
    ("minusculas", {}, "Tem Maiúscula.", False),
    # --- específicos do português ---
    ("crase", {}, "Vou à feira às sete.", True),
    ("crase", {}, "Vou a feira as sete.", False),
    ("crase", {}, "Ele está à vontade.", True),
    ("sem_crase", {}, "Vou a feira cedo.", True),
    ("sem_crase", {}, "Vou à feira cedo.", False),
    ("mesoclise", {}, "Dar-lhe-ei a resposta amanhã.", True),
    ("mesoclise", {}, "Falar-se-á sobre isso.", True),
    ("mesoclise", {}, "Diga-me a verdade.", False),
    ("mesoclise", {}, "Vou dar a resposta amanhã.", False),
    ("proclise", {}, "Não me diga isso agora.", True),
    ("proclise", {}, "Quem me dera saber.", True),
    ("proclise", {}, "Diga-me isso agora.", False),
    ("enclise", {}, "Diga-me a verdade.", True),
    ("enclise", {}, "Dar-lhe-ei a resposta.", False),      # mesóclise não conta
    ("enclise", {}, "Me diga a verdade.", False),
    ("cedilha", {"n": 2}, "A produção da criação começou.", True),
    ("cedilha", {"n": 2}, "A produção começou bem.", True),
    ("cedilha", {"n": 3}, "A produção começou bem.", False),
    ("sem_til", {}, "Reciclar e bom para o planeta.", True),
    ("sem_til", {}, "Não é bom.", False),
    ("sem_til", {}, "As opções são boas.", False),
    ("porque_ambos", {}, "Por que reciclar? Porque ajuda o planeta.", True),
    ("porque_ambos", {}, "Reciclar ajuda porque limpa a cidade.", False),
    ("porque_ambos", {}, "Por que fazer isso?", False),
    ("so_voce", {}, "Você deve reciclar sempre.", True),
    ("so_voce", {}, "Você e tu devem reciclar.", False),
    ("so_voce", {}, "A pessoa deve reciclar.", False),     # não usou "você": reprova
    ("sem_diacritico", {}, "reciclar e bom para todos.", True),
    ("sem_diacritico", {}, "reciclar é bom.", False),
    ("sem_digito", {}, "Beba dois litros por dia.", True),
    ("sem_digito", {}, "Beba 2 litros por dia.", False),
    ("agudo_e_circunflexo", {}, "É importante ter atenção ao pônei.", True),
    ("agudo_e_circunflexo", {}, "É importante ter agua.", False),
]


def main() -> int:
    falhas = []
    for tipo, params, resposta, esperado in CASOS:
        obtido = bool(VERIF[tipo](resposta, params))
        if obtido != esperado:
            falhas.append((tipo, resposta, esperado, obtido))

    # a nota frouxa não pode reprovar quem só embrulhou a resposta em markdown
    if not VERIF["comeca_com"](limpa_frouxo("**Olha**, é simples."), {"texto": "Olha"}):
        falhas.append(("limpa_frouxo", "**Olha**...", True, False))

    # o conjunto tem que estar íntegro
    its = itens()
    if len(its) != 308:
        falhas.append(("itens", f"esperado 308, veio {len(its)}", 308, len(its)))
    if any(not x["prompt"].strip() or x["tipo"] not in VERIF for x in its):
        falhas.append(("itens", "item sem prompt ou com tipo desconhecido", True, False))

    for f in falhas:
        print(f"FALHOU: {f[0]} | {f[1]!r} | esperado {f[2]}, veio {f[3]}")
    print(f"{len(CASOS) + 3 - len(falhas)}/{len(CASOS) + 3} verificações passaram")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
