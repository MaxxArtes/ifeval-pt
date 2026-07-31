# IFEval-pt

Benchmark de **seguimento de instrução em português do Brasil**. 308 itens, verificação
**por código** — sem juiz LLM, sem GPU, sem opinião. Roda em minutos numa CPU e dá o mesmo
número para quem repetir.

```bash
python3 ifeval_pt.py --url http://SEU-ENDPOINT/v1 --modelo NOME --saida resultado.json
python3 testes.py     # 56 verificações dos verificadores
```

Qualquer endpoint compatível com a API da OpenAI serve. Não depende de nada além da
biblioteca padrão do Python.

## O que ele mede

Uma coisa só: **o modelo obedece?** Não se a resposta é boa nem se está correta — se ele
fez o que foi pedido. "Responda em no máximo duas frases" e um programa conta as frases.
"Não use a palavra você" e o programa procura a palavra.

## Por que existe, se já há IFEval em português

Existem outros: [`amalia-llm/IFEval-mt-pt`](https://huggingface.co/datasets/amalia-llm/IFEval-mt-pt)
(541 itens, pt-PT), [`Polygl0t/IFEval-PT`](https://huggingface.co/datasets/Polygl0t/IFEval-PT)
(300), a fatia pt do [`facebook/Multi-IF`](https://huggingface.co/datasets/facebook/Multi-IF)
(524, CC-BY-NC) e [`akawaai/Portuguese-IFEval`](https://github.com/akawaai/Portuguese-IFEval)
(618).

**Todos são tradução do conjunto em inglês** — medem, portanto, inglês vertido para o
português. Este aqui testa restrições que **só existem na língua**:

| Restrição | Instrução |
|---|---|
| `ptbr:crase` / `ptbr:sem_crase` | "Use crase pelo menos uma vez" |
| `ptbr:mesoclise` | "Use uma mesóclise, como em 'dar-lhe-ei'" |
| `ptbr:proclise` | "Use próclise depois de palavra atrativa, como em 'não me diga'" |
| `ptbr:enclise` | "Use ênclise, como em 'diga-me'" |
| `ptbr:porque_ambos` | "Use 'por que' e 'porque' na mesma resposta" |
| `ptbr:cedilha` | "Use pelo menos três palavras com ç" |
| `ptbr:sem_til` | "Escreva sem usar nenhum til (ã, õ)" |
| `ptbr:so_voce` | "Trate o leitor por 'você' e nunca por 'tu'" |
| `ptbr:sem_diacritico` | "Escreva sem nenhum acento ou cedilha" |
| `ptbr:sem_digito` | "Escreva os números por extenso" |
| `ptbr:agudo_e_circunflexo` | "Uma palavra com agudo e uma com circunflexo" |

A de próclise é a mais direta: **a regra gramatical é o próprio teste** — próclise é
obrigatória depois de palavra atrativa, então o verificador procura exatamente
atrativo + pronome + verbo.

Além dessas há as genéricas herdadas do IFEval original: número de frases, número de
palavras, palavra obrigatória, palavra proibida, começar/terminar com, caixa baixa.

## Formato

Mesmas quatro colunas do [`google/IFEval`](https://huggingface.co/datasets/google/IFEval),
para funcionar de imediato com quem já avalia o original:

```json
{"key": 11,
 "prompt": "Explique o que é reciclagem. Use crase pelo menos uma vez na resposta.",
 "instruction_id_list": ["ptbr:crase"],
 "kwargs": [{}]}
```

308 itens = 14 tarefas-base × 22 restrições. O número foi escolhido por **itens por
restrição** (14), não pelo total: com 14 dá para reportar taxa por restrição com intervalo
de confiança utilizável (±5,5 pontos a 95%, contra ±9,5 se fossem 100).

## Duas notas, como no original

- **estrita** — a restrição vale no texto exatamente como veio.
- **frouxa** — vale depois de remover markdown, aspas e espaço sobrando. Modelo pequeno
  costuma errar por embrulhar a resposta, não por desobedecer.

## Como ler o resultado

| Modelo | Estrita | Frouxa |
|---|---|---|
| Pocket-LM 269M (só pré-treino, sem ajuste de instrução) | 32,8% | 32,8% |

O padrão nesse resultado é o aviso mais útil para quem for usar o benchmark: restrições
**passivas** ("não use crase") são satisfeitas por acidente quando a resposta é curta —
12/14 — enquanto as **ativas** ("use crase") falham — 1/14. **Compare pela tabela por
restrição, não pela média.**

## Armadilhas de medição já tratadas

- Abreviações comuns ("Sr.", "etc.", "p.ex.") não contam como fim de frase — sem isso a
  contagem infla e o modelo é reprovado por erro do medidor.
- Palavra proibida é detectada **com e sem acento**: proibir "você" pega também "voce".
- A contagem de palavras aceita caracteres acentuados.
- Mesóclise e ênclise não se confundem: `dar-lhe-ei` conta como mesóclise e **não** como
  ênclise.

## Licença

Apache 2.0. Construído durante o desenvolvimento do **Pocket-LM**, um modelo de linguagem
pt-BR de 269M treinado do zero para rodar offline no celular.

Contribuições bem-vindas, em especial mais tarefas-base e novas restrições da língua.
