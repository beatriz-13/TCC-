# -*- coding: utf-8 -*-
from pathlib import Path
import re
import unicodedata
import warnings

import numpy as np
import pandas as pd
from scipy import stats

from difflib import SequenceMatcher

import matplotlib
matplotlib.use("Agg")  
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings("ignore", category=FutureWarning)

# ============================================================
# 1. ARQUIVOS E CONFIGURAÇÕES
# ============================================================

PASTA = Path(__file__).resolve().parent

ARQ_P1 = PASTA / "OSIERDP 20242-Resolução de Questão - Parte 1-notas.csv"
ARQ_P2 = PASTA / "OSIERDP 20242-Resolução de questões - Parte 2-notas.csv"
ARQ_INICIAL = PASTA / "Formulário Inicial.csv"
ARQ_FINAL = PASTA / "Formulário Final.xlsx"

SAIDA = PASTA / "resultados_oficina_ia"
SAIDA.mkdir(exist_ok=True)

# Escolha qual nota representa o desempenho principal:
# "max" = melhor tentativa finalizada (padrão)
# "first" = primeira tentativa finalizada
# "last" = última tentativa finalizada
# "mean" = média das tentativas finalizadas

METRICA_PRINCIPAL = "max"

ARQUIVOS = [ARQ_P1, ARQ_P2, ARQ_INICIAL, ARQ_FINAL]
faltantes = [str(p) for p in ARQUIVOS if not p.exists()]
if faltantes:
    raise FileNotFoundError(
        "Não encontrei estes arquivos. Coloque-os na mesma pasta do script:\n"
        + "\n".join(faltantes)
    )

sns.set_theme(style="whitegrid", context="notebook")


# ============================================================
# 2. FUNÇÕES GERAIS
# ============================================================

def normalizar_texto(valor):
    if pd.isna(valor):
        return ""
    s = str(valor).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9@._\s-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def normalizar_email(valor):
    return normalizar_texto(valor).replace(" ", "")


def numero(valor):
    """Converte números com vírgula decimal sem transformar ausências em zero."""
    if pd.isna(valor):
        return np.nan
    if isinstance(valor, (int, float, np.number)):
        return float(valor)
    s = str(valor).strip()
    if not s or s.lower() in {"nan", "none", "-", "—"}:
        return np.nan
    s = s.replace("%", "").strip()
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return pd.to_numeric(s, errors="coerce")


def localizar_coluna(df, termos, obrigatoria=False, rotulo=""):
    """
    Procura coluna por trecho do nome, ignorando acentos/maiúsculas.
    'termos' pode ser uma string ou lista de alternativas.
    """
    if isinstance(termos, str):
        termos = [termos]
    colunas = {c: normalizar_texto(c) for c in df.columns}
    for termo in termos:
        t = normalizar_texto(termo)
        for original, normalizada in colunas.items():
            if t and t in normalizada:
                return original
    if obrigatoria:
        raise KeyError(
            f"Não encontrei a coluna necessária ({rotulo or termos}).\n"
            f"Colunas disponíveis:\n- " + "\n- ".join(map(str, df.columns))
        )
    return None


def ler_csv_flexivel(caminho):
    """Tenta detectar separador e codificação comuns de CSV exportado."""
    erros = []
    for encoding in ("utf-8-sig", "utf-8", "latin1"):
        try:
            return pd.read_csv(
                caminho, sep=None, engine="python", encoding=encoding,
                decimal=","
            )
        except Exception as exc:
            erros.append(f"{encoding}: {exc}")
    raise RuntimeError(
        f"Não consegui ler {caminho.name}.\n" + "\n".join(erros)
    )


def mapear_escala_1a5(valor):
    """Mapeia respostas textuais de escala ordinal para 1 a 5."""
    if pd.isna(valor):
        return np.nan
    n = numero(valor)
    if pd.notna(n):
        return n if 1 <= n <= 5 else np.nan
    s = normalizar_texto(valor)
    mapa = {
        "pessimo": 1, "muito ruim": 1,
        "ruim": 2,
        "mediano": 3, "regular": 3, "medio": 3,
        "bom": 4,
        "excelente": 5, "muito bom": 5,
    }
    return mapa.get(s, np.nan)


def mapear_sim_nao(valor):
    if pd.isna(valor):
        return np.nan
    s = normalizar_texto(valor)
    if s.startswith("sim"):
        return 1
    if s.startswith("nao"):
        return 0
    return np.nan


def mapear_habilidade(valor):
    if pd.isna(valor):
        return np.nan
    s = normalizar_texto(valor)
    mapa = {
        "insuficiente": 1, "muito baixa": 1,
        "ruim": 2, "baixa": 2,
        "regular": 3, "mediana": 3,
        "bom": 4, "boa": 4,
        "excelente": 5, "muito boa": 5,
    }
    return mapa.get(s, numero(valor))


def mapear_confianca(valor):
    if pd.isna(valor):
        return np.nan
    s = normalizar_texto(valor)
    mapa = {
        "nao totalmente": 1,
        "um pouco": 2,
        "com certeza": 3,
    }
    return mapa.get(s, numero(valor))


def mapear_verificacao(valor):
    if pd.isna(valor):
        return np.nan
    s = normalizar_texto(valor)
    if "nao" in s and ("somente" in s or "suficiente" in s):
        return 0
    if "nem sempre" in s or "as vezes" in s:
        return 1
    if "sim" in s or "sites" in s or "livros" in s or "artigos" in s:
        return 2
    return np.nan


def chave_participante(email, nome):
    e = normalizar_email(email)
    n = normalizar_texto(nome)
    return f"email:{e}" if e else (f"nome:{n}" if n else "")


# ============================================================
# 3. LEITURA E PREPARAÇÃO DAS NOTAS P1 E P2
# ============================================================

def carregar_notas(caminho, etapa):
    df = ler_csv_flexivel(caminho)
    df.columns = [str(c).strip() for c in df.columns]

    col_nome = localizar_coluna(df, "Nome", obrigatoria=True, rotulo="Nome")
    col_sobrenome = localizar_coluna(df, "Sobrenome", obrigatoria=True,
                                     rotulo="Sobrenome")
    col_email = localizar_coluna(df, "Endereço de e-mail",
                                 obrigatoria=True, rotulo="e-mail")
    col_nota = localizar_coluna(df, ["Nota/10", "Nota"], obrigatoria=True,
                                rotulo="Nota/10")
    col_situacao = localizar_coluna(df, "Situação", obrigatoria=True,
                                    rotulo="Situação")
    col_inicio = localizar_coluna(df, "Iniciado")

    df["nome_exibicao"] = (
        df[col_nome].fillna("").astype(str).str.strip() + " " +
        df[col_sobrenome].fillna("").astype(str).str.strip()
    ).str.strip()
    df["email_norm"] = df[col_email].map(normalizar_email)
    df["nome_norm"] = df["nome_exibicao"].map(normalizar_texto)
    df["chave"] = [
        chave_participante(e, n)
        for e, n in zip(df["email_norm"], df["nome_norm"])
    ]
    df["nota"] = df[col_nota].map(numero)

    # --- Exclui linhas-resumo do Moodle e mantém somente tentativas finalizadas.--- 
    df = df[
        ~df[col_sobrenome].astype(str).str.contains(
            "Média geral|Media geral", case=False, na=False
        )
    ].copy()
    df = df[
        df[col_situacao].astype(str).str.contains(
            "Finalizada|Finished", case=False, na=False
        )
    ].copy()
    df = df[df["chave"].ne("") & df["nota"].notna()].copy()

    if col_inicio:
        df["_data"] = pd.to_datetime(
    df[col_inicio],
    errors="coerce",
    dayfirst=True,
    format="mixed"
)
    else:
        df["_data"] = pd.NaT

    # --- Mantém também as notas individuais por questão, se existirem.--- 
    colunas_questoes = []
    for c in df.columns:
        if normalizar_texto(c).startswith("q "):
            novo = "questao_" + re.sub(r"\W+", "_", normalizar_texto(c)).strip("_")
            df[novo] = df[c].map(numero)
            colunas_questoes.append(novo)

    df = df.sort_values(["chave", "_data"], na_position="last")
    return df, colunas_questoes


def resumir_etapa(df, etapa, colunas_questoes):
    if df.empty:
        return pd.DataFrame(columns=[
            "chave", f"{etapa}_nome", f"{etapa}_email",
            f"{etapa}_n_tentativas", f"{etapa}_first",
            f"{etapa}_last", f"{etapa}_mean", f"{etapa}_max"
        ])

    agregacoes = {
        "nome": ("nome_exibicao", "first"),
        "email": ("email_norm", "first"),
        "n_tentativas": ("nota", "size"),
        "first": ("nota", "first"),
        "last": ("nota", "last"),
        "mean": ("nota", "mean"),
        "max": ("nota", "max"),
    }
    # --- Guarda também o desempenho em cada questão, não apenas a nota total.--- 
    for q in colunas_questoes:
        agregacoes[f"{q}_max"] = (q, "max")
        agregacoes[f"{q}_mean"] = (q, "mean")

    resumo = df.groupby("chave", as_index=False).agg(**agregacoes)
    resumo = resumo.rename(columns={
        c: f"{etapa}_{c}" for c in resumo.columns if c != "chave"
    })
    return resumo


p1_raw, questoes_p1 = carregar_notas(ARQ_P1, "p1")
p2_raw, questoes_p2 = carregar_notas(ARQ_P2, "p2")

p1 = resumir_etapa(p1_raw, "p1", questoes_p1)
p2 = resumir_etapa(p2_raw, "p2", questoes_p2)

notas = p1.merge(p2, on="chave", how="outer")
notas["nome"] = notas.get("p1_nome", pd.Series(index=notas.index, dtype=object)).combine_first(
    notas.get("p2_nome", pd.Series(index=notas.index, dtype=object))
)
notas["email"] = notas.get("p1_email", pd.Series(index=notas.index, dtype=object)).combine_first(
    notas.get("p2_email", pd.Series(index=notas.index, dtype=object))
)

coluna_metrica = {
    "max": "max", "first": "first", "last": "last", "mean": "mean"
}.get(METRICA_PRINCIPAL)
if coluna_metrica is None:
    raise ValueError("METRICA_PRINCIPAL deve ser max, first, last ou mean.")

notas["P1"] = notas[f"p1_{coluna_metrica}"]
notas["P2"] = notas[f"p2_{coluna_metrica}"]
notas["delta_P2_menos_P1"] = notas["P2"] - notas["P1"]
notas["situacao_comparacao"] = np.select(
    [
        notas["delta_P2_menos_P1"] > 0,
        notas["delta_P2_menos_P1"] < 0,
        notas["delta_P2_menos_P1"] == 0,
    ],
    ["Maior nota na Parte 2", "Maior nota na Parte 1", "Notas iguais"],
    default="Sem par de notas"
)

print("\n=== PARTICIPANTES NAS ATIVIDADES ===")
print(f"Parte 1: {p1['chave'].nunique()} participantes com tentativa finalizada.")
print(f"Parte 2: {p2['chave'].nunique()} participantes com tentativa finalizada.")
print(f"Com notas nas duas partes: {notas[['P1', 'P2']].dropna().shape[0]}.")


# ============================================================
# 4. FORMULÁRIO INICIAL
# ============================================================

ini = ler_csv_flexivel(ARQ_INICIAL)
ini.columns = [str(c).strip() for c in ini.columns]

c_nome_ini = localizar_coluna(
    ini, ["Digite seu nome completo", "Nome completo"], obrigatoria=True,
    rotulo="nome do formulário inicial"
)
c_email_ini = localizar_coluna(ini, "Endereço de e-mail")
c_email_inst = localizar_coluna(ini, "E-mail Institucional")

c_familiaridade = localizar_coluna(ini, "escala de 1 a 5")
c_frequencia = localizar_coluna(ini, "frequência que você utiliza")
c_habilidade = localizar_coluna(ini, "habilidades matemáticas")
c_confianca = localizar_coluna(ini, "sejam confiáveis")
c_verifica = localizar_coluna(ini, "outras fontes")
c_usa_cola = localizar_coluna(ini, "usou o ia para cola")
c_acha_ajuda = localizar_coluna(ini, "ChatGPT possa ajudar")

ini["nome_norm"] = ini[c_nome_ini].map(normalizar_texto)
ini["email_norm"] = ini[c_email_ini].map(normalizar_email) if c_email_ini else ""
ini["email_inst_norm"] = ini[c_email_inst].map(normalizar_email) if c_email_inst else ""

def valor_coluna(df, coluna):
    return df[coluna] if coluna and coluna in df.columns else pd.Series(np.nan, index=df.index)

ini["chave_email"] = [
    chave_participante(e, n) if e else ""
    for e, n in zip(ini["email_norm"], ini["nome_norm"])
]
ini["chave_inst"] = [
    chave_participante(e, n) if e else ""
    for e, n in zip(ini["email_inst_norm"], ini["nome_norm"])
]
ini["chave_nome"] = ini["nome_norm"].map(lambda n: f"nome:{n}" if n else "")
ini["chave"] = ini["chave_email"]
ini.loc[ini["chave"].eq(""), "chave"] = ini.loc[ini["chave"].eq(""), "chave_inst"]
ini.loc[ini["chave"].eq(""), "chave"] = ini.loc[ini["chave"].eq(""), "chave_nome"]

ini["familiaridade"] = valor_coluna(ini, c_familiaridade).map(numero)
ini["frequencia_uso"] = valor_coluna(ini, c_frequencia).map(numero)
ini["habilidade_matematica"] = valor_coluna(ini, c_habilidade).map(mapear_habilidade)
ini["confianca_IA"] = valor_coluna(ini, c_confianca).map(mapear_confianca)
ini["verifica_outras_fontes"] = valor_coluna(ini, c_verifica).map(mapear_verificacao)
ini["ja_usou_IA_para_cola"] = valor_coluna(ini, c_usa_cola).map(mapear_sim_nao)
ini["acha_que_ChatGPT_ajuda"] = valor_coluna(ini, c_acha_ajuda).map(mapear_sim_nao)

ini = ini[ini["chave"].ne("")].drop_duplicates("chave", keep="first").copy()

variaveis_ini = [
    "familiaridade", "frequencia_uso", "habilidade_matematica",
    "confianca_IA", "verifica_outras_fontes",
    "ja_usou_IA_para_cola", "acha_que_ChatGPT_ajuda"
]


# ============================================================
# 5. FORMULÁRIO FINAL
# ============================================================


_amostra = pd.read_excel(ARQ_FINAL, header=None)
_linha_cabecalho = None
for i in range(min(15, len(_amostra))):
    valores = _amostra.iloc[i].astype(str).map(normalizar_texto)
    if valores.str.contains(r"^nome:?$", regex=True).any():
        _linha_cabecalho = i
        break
if _linha_cabecalho is None:
    fin = pd.read_excel(ARQ_FINAL)
else:
    fin = pd.read_excel(ARQ_FINAL, header=_linha_cabecalho)
fin.columns = [str(c).strip() for c in fin.columns]

c_nome_fin = localizar_coluna(fin, ["Nome:", "Nome"], obrigatoria=True,
                               rotulo="nome do formulário final")
c_comp_p1 = localizar_coluna(fin, ["mais especificamente", "Resolução de Questões"])
c_questionando = localizar_coluna(fin, "Questionando o uso de IA")
c_aprendendo = localizar_coluna(fin, "Aprendendo com")
c_possivel = localizar_coluna(fin, "possível aprender Matemática")
c_aplicar = localizar_coluna(fin, "Pretende tentar aplicar")

fin["nome_norm"] = fin[c_nome_fin].map(normalizar_texto)
fin["chave"] = fin["nome_norm"].map(lambda n: f"nome:{n}" if n else "")


fin["avaliacao_P1_form"] = valor_coluna(fin, c_comp_p1).map(mapear_escala_1a5)
fin["avaliacao_questionando_IA"] = valor_coluna(fin, c_questionando).map(mapear_escala_1a5)
fin["avaliacao_aprendendo_com_IA"] = valor_coluna(fin, c_aprendendo).map(mapear_escala_1a5)
fin["acredita_ser_possivel_aprender_com_IA"] = valor_coluna(fin, c_possivel).map(mapear_sim_nao)
fin["pretende_aplicar_o_que_aprendeu"] = valor_coluna(fin, c_aplicar).map(mapear_sim_nao)

variaveis_fin = [
    "avaliacao_P1_form", "avaliacao_questionando_IA",
    "avaliacao_aprendendo_com_IA",
    "acredita_ser_possivel_aprender_com_IA",
    "pretende_aplicar_o_que_aprendeu"
]

fin = fin[fin["chave"].ne("")].drop_duplicates("chave", keep="first").copy()


# ============================================================
# 6. CRUZAMENTO CONSERVADOR DOS DADOS
# ============================================================

def indexar_unico(df, coluna_chave):
    d = df[df[coluna_chave].astype(str).ne("")].copy()
    duplicadas = d[d.duplicated(coluna_chave, keep=False)]
    if not duplicadas.empty:
        print(f"Aviso: {len(duplicadas)} linhas em chaves duplicadas ({coluna_chave}); "
              "será mantida a primeira resposta.")
    return d.drop_duplicates(coluna_chave, keep="first").set_index(coluna_chave)


ini_por_chave = indexar_unico(ini, "chave")
fin_por_chave = indexar_unico(fin, "chave")

def adicionar_formulario(master, formulario, prefixo, chaves_alternativas):
    form = formulario.copy()
    saida = master.copy()
    for col in chaves_alternativas:
        if col not in saida:
            continue
        candidatos = form[~form.index.duplicated(keep="first")]
        # ---A coluna de chave alternativa precisa existir no formulário.---
        chave_form = col
        if chave_form not in candidatos.columns:
            continue
        mapa = candidatos.set_index(chave_form)
        for variavel in [c for c in form.columns if c not in {"chave"}]:
            if variavel not in saida.columns:
                saida[f"{prefixo}_{variavel}"] = saida[col].map(mapa[variavel])
            else:
                nova = saida[col].map(mapa[variavel])
                saida[f"{prefixo}_{variavel}"] = saida[f"{prefixo}_{variavel}"].combine_first(nova)
    return saida
    
    

# Prepara chaves auxiliares nas notas.
notas["chave_email"] = notas["email"].map(
    lambda e: f"email:{normalizar_email(e)}" if pd.notna(e) and normalizar_email(e) else ""
)
notas["chave_nome"] = notas["nome"].map(
    lambda n: f"nome:{normalizar_texto(n)}" if pd.notna(n) and normalizar_texto(n) else ""
)



# --- Para o formulário inicial, indexa por e-mail e, em segundo lugar, por nome.--- 
ini_email = ini.copy()
ini_email["chave_email"] = ini_email["email_norm"].map(
    lambda e: f"email:{e}" if e else ""
)
ini_nome = ini.copy()
ini_nome["chave_nome"] = ini_nome["nome_norm"].map(
    lambda n: f"nome:{n}" if n else ""
)

master = notas.copy()
for prefixo, form, chave_master, chave_form in [
    ("ini", ini_email, "chave_email", "chave_email"),
    ("ini", ini_nome, "chave_nome", "chave_nome"),
]:
    form = form[form[chave_form].ne("")].drop_duplicates(chave_form).set_index(chave_form)
    for c in variaveis_ini:
        nova = master[chave_master].map(form[c]) if c in form.columns else np.nan
        nome_col = f"ini_{c}"
        master[nome_col] = master[nome_col].combine_first(nova) if nome_col in master else nova
        
        

# --- Formulário final: pelo nome exato normalizado.--- 
fin_nome = fin.copy()
fin_nome["chave_nome"] = fin_nome["nome_norm"].map(
    lambda n: f"nome:{n}" if n else ""
)
fin_nome = fin_nome[fin_nome["chave_nome"].ne("")].drop_duplicates(
    "chave_nome"
).set_index("chave_nome")
for c in variaveis_fin:
    master[f"fin_{c}"] = master["chave_nome"].map(fin_nome[c]) if c in fin_nome.columns else np.nan



# Auditoria de correspondência aproximada: sugere candidatos, mas NÃO os aplica.
nomes_fin = fin["nome_norm"].dropna().loc[lambda s: s.ne("")].unique().tolist()
nomes_ini = ini["nome_norm"].dropna().loc[lambda s: s.ne("")].unique().tolist()

def melhor_sugestao(nome, escolhas):
    if not nome or not escolhas:
        return "", 0.0
    melhor = max(escolhas, key=lambda x: SequenceMatcher(None, nome, x).ratio())
    return melhor, SequenceMatcher(None, nome, melhor).ratio()

auditoria = []
for _, linha in master.iterrows():
    nome = normalizar_texto(linha.get("nome", ""))
    if not nome:
        continue
    for etapa, escolhas in [("formulario_inicial", nomes_ini), ("formulario_final", nomes_fin)]:
        sugestao, score = melhor_sugestao(nome, escolhas)
        if score >= 0.82:
            auditoria.append({
                "nome_na_planilha_de_notas": linha.get("nome", ""),
                "fonte": etapa,
                "candidato_sugerido": sugestao,
                "similaridade": round(score, 3),
                "revisar_manualmente": "SIM - não foi associado automaticamente"
            })

pd.DataFrame(auditoria).to_csv(
    SAIDA / "revisar_correspondencias_de_nomes.csv",
    index=False, encoding="utf-8-sig"
)



# IDs anônimos para tabelas por participante.
master = master.reset_index(drop=True)
master.insert(0, "id_participante", [f"P{i:03d}" for i in range(1, len(master) + 1)])

print("\n=== CRUZAMENTO DOS FORMULÁRIOS ===")
print("Com pelo menos uma variável inicial:",
      master[[f"ini_{c}" for c in variaveis_ini]].notna().any(axis=1).sum())
print("Com pelo menos uma variável final:",
      master[[f"fin_{c}" for c in variaveis_fin]].notna().any(axis=1).sum())


# ============================================================
# 7. TABELAS DESCRITIVAS
# ============================================================

def tabela_descritiva(serie):
    x = pd.to_numeric(serie, errors="coerce").dropna()
    if x.empty:
        return {
            "n": 0, "media": np.nan, "desvio_padrao": np.nan,
            "mediana": np.nan, "q1": np.nan, "q3": np.nan,
            "minimo": np.nan, "maximo": np.nan
        }
    return {
        "n": len(x),
        "media": x.mean(),
        "desvio_padrao": x.std(),
        "mediana": x.median(),
        "q1": x.quantile(0.25),
        "q3": x.quantile(0.75),
        "minimo": x.min(),
        "maximo": x.max()
    }


linhas_desc = []
for col, rotulo in [
    ("P1", "Parte 1 — uso livre da IA"),
    ("P2", "Parte 2 — uso de prompt orientador"),
    ("delta_P2_menos_P1", "Diferença P2 − P1")
]:
    linha = {"variavel": rotulo, **tabela_descritiva(master[col])}
    linhas_desc.append(linha)

pd.DataFrame(linhas_desc).round(3).to_csv(
    SAIDA / "01_descritiva_notas.csv", index=False, encoding="utf-8-sig"
)



# Resumo das tentativas: importante para avaliar se houve várias submissões.
tentativas = master[[
    "id_participante", "p1_n_tentativas", "p2_n_tentativas",
    "p1_first", "p1_last", "p1_mean", "p1_max",
    "p2_first", "p2_last", "p2_mean", "p2_max"
]].copy()
tentativas.to_csv(
    SAIDA / "02_tentativas_por_participante.csv",
    index=False, encoding="utf-8-sig"
)



# Resumo por questão, preservando a escala de cada questão.
linhas_questoes = []
for etapa, colunas in [("Parte 1 — uso livre", questoes_p1),
                       ("Parte 2 — prompt orientador", questoes_p2)]:
    prefixo = "p1_" if etapa.startswith("Parte 1") else "p2_"
    for q in colunas:
        col = prefixo + q + "_max"
        if col in master.columns:
            d = pd.to_numeric(master[col], errors="coerce").dropna()
            linhas_questoes.append({
                "etapa": etapa,
                "questao": q,
                **tabela_descritiva(d)
            })
pd.DataFrame(linhas_questoes).round(3).to_csv(
    SAIDA / "02b_descritiva_por_questao.csv",
    index=False, encoding="utf-8-sig"
)



# Tabelas de frequências das respostas iniciais e finais.
for col in variaveis_ini:
    c = f"ini_{col}"
    if c in master:
        freq = master[c].value_counts(dropna=False).rename_axis("resposta").reset_index(name="frequencia")
        freq["porcentagem_validos"] = (
            freq["frequencia"] / master[c].notna().sum() * 100
        ).round(2)
        freq.to_csv(SAIDA / f"frequencia_inicial_{col}.csv",
                    index=False, encoding="utf-8-sig")

for col in variaveis_fin:
    c = f"fin_{col}"
    if c in master:
        freq = master[c].value_counts(dropna=False).rename_axis("resposta").reset_index(name="frequencia")
        freq["porcentagem_validos"] = (
            freq["frequencia"] / master[c].notna().sum() * 100
        ).round(2)
        freq.to_csv(SAIDA / f"frequencia_final_{col}.csv",
                    index=False, encoding="utf-8-sig")


# ============================================================
# 8. COMPARAÇÃO PAREADA P1 × P2
# ============================================================

pares = master[["P1", "P2", "delta_P2_menos_P1"]].dropna().copy()
if len(pares) >= 2:
    try:
        w, p_w = stats.wilcoxon(pares["P1"], pares["P2"], alternative="two-sided")
    except ValueError:
        w, p_w = np.nan, np.nan
else:
    w, p_w = np.nan, np.nan

comparacao = pd.DataFrame([{
    "n_pares": len(pares),
    "mediana_P1": pares["P1"].median() if len(pares) else np.nan,
    "mediana_P2": pares["P2"].median() if len(pares) else np.nan,
    "mediana_diferenca_P2_menos_P1": pares["delta_P2_menos_P1"].median() if len(pares) else np.nan,
    "media_diferenca": pares["delta_P2_menos_P1"].mean() if len(pares) else np.nan,
    "n_P2_maior": int((pares["delta_P2_menos_P1"] > 0).sum()),
    "n_iguais": int((pares["delta_P2_menos_P1"] == 0).sum()),
    "n_P1_maior": int((pares["delta_P2_menos_P1"] < 0).sum()),
    "wilcoxon_W": w,
    "wilcoxon_p": p_w,
    "metrica_usada": METRICA_PRINCIPAL
}])
comparacao.round(4).to_csv(
    SAIDA / "03_comparacao_pareada_P1_P2.csv",
    index=False, encoding="utf-8-sig"
)


# ============================================================
# 9. BOXplots P1/P2 E PERFIL INICIAL/IMPRESSÕES FINAIS
# ============================================================

def salvar_boxplot_p1_p2(df):
    d = df[["P1", "P2"]].dropna()
    if d.empty:
        return
    longo = d.melt(var_name="Etapa", value_name="Nota")
    longo["Etapa"] = longo["Etapa"].map({
        "P1": "Parte 1\nuso livre",
        "P2": "Parte 2\nprompt orientador"
    })
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.boxplot(data=longo, x="Etapa", y="Nota", ax=ax, width=0.5)
    sns.stripplot(data=longo, x="Etapa", y="Nota", ax=ax,
                  color="black", alpha=0.35, jitter=0.12, size=3)
    ax.set_title(f"Notas nas duas etapas (mesmos participantes; n={len(d)})")
    ax.set_xlabel("")
    ax.set_ylabel("Nota (0 a 10)")
    ax.set_ylim(0, 10)
    fig.tight_layout()
    fig.savefig(SAIDA / "boxplot_01_P1_versus_P2.png", dpi=220)
    plt.close(fig)


def salvar_boxplot_por_grupo(df, coluna_grupo, titulo, arquivo,
                             coluna_nota="P2", ordem=None):
    dados = df[[coluna_grupo, coluna_nota]].dropna().copy()

    if len(dados) < 3 or dados[coluna_grupo].nunique() < 2:
        return

    if ordem:
        dados[coluna_grupo] = pd.Categorical(
            dados[coluna_grupo], categories=ordem, ordered=True
        )
        dados = dados.dropna(subset=[coluna_grupo])

    n_categorias = dados[coluna_grupo].nunique()

    # Uma cor diferente para cada categoria.
    paleta = sns.color_palette("husl", n_colors=n_categorias)

    fig, ax = plt.subplots(
        figsize=(max(7, n_categorias * 1.5), 5)
    )

    sns.boxplot(
    data=dados,
    x=coluna_grupo,
    y=coluna_nota,
    hue=coluna_grupo,
    palette="husl",
    dodge=False,
    ax=ax,
    width=0.6,
    legend=False
)

    # Remove a legenda duplicada.
    if ax.legend_ is not None:
        ax.legend_.remove()

    sns.stripplot(
        data=dados,
        x=coluna_grupo,
        y=coluna_nota,
        ax=ax,
        color="black",
        alpha=0.35,
        jitter=0.15,
        size=3
    )

    ax.set_title(f"{titulo} — {coluna_nota} (n={len(dados)})")
    ax.set_xlabel("")

    ax.set_ylabel(
        "Nota (0 a 10)"
        if coluna_nota != "delta_P2_menos_P1"
        else "Diferença P2 − P1"
    )

    if coluna_nota == "delta_P2_menos_P1":
        ax.axhline(
            0, color="gray", linestyle="--", linewidth=1
        )

    ax.tick_params(axis="x", rotation=15)

    fig.tight_layout()
    fig.savefig(SAIDA / arquivo, dpi=220)
    plt.close(fig)
    dados = df[[coluna_grupo, coluna_nota]].dropna().copy()
    if len(dados) < 3 or dados[coluna_grupo].nunique() < 2:
        return
    if ordem:
        dados[coluna_grupo] = pd.Categorical(
            dados[coluna_grupo], categories=ordem, ordered=True
        )
        dados = dados.dropna(subset=[coluna_grupo])
    fig, ax = plt.subplots(figsize=(max(7, dados[coluna_grupo].nunique() * 1.5), 5))
    sns.boxplot(data=dados, x=coluna_grupo, y=coluna_nota, ax=ax, width=0.6)
    sns.stripplot(data=dados, x=coluna_grupo, y=coluna_nota, ax=ax,
                  color="black", alpha=0.35, jitter=0.15, size=3)
    ax.set_title(f"{titulo} — {coluna_nota} (n={len(dados)})")
    ax.set_xlabel("")
    ax.set_ylabel("Nota (0 a 10)" if coluna_nota != "delta_P2_menos_P1" else "Diferença P2 − P1")
    if coluna_nota == "delta_P2_menos_P1":
        ax.axhline(0, color="gray", linestyle="--", linewidth=1)
    ax.tick_params(axis="x", rotation=15)
    fig.tight_layout()
    fig.savefig(SAIDA / arquivo, dpi=220)
    plt.close(fig)


salvar_boxplot_p1_p2(master)




# --- Variáveis do formulário inicial: perfil prévio do estudante.--- 
titulos_ini = {
    "familiaridade": "Familiaridade inicial com o ChatGPT",
    "frequencia_uso": "Frequência inicial de uso do ChatGPT",
    "habilidade_matematica": "Habilidade matemática autodeclarada",
    "confianca_IA": "Confiança nas respostas da IA",
    "verifica_outras_fontes": "Busca de outras fontes além da IA",
    "ja_usou_IA_para_cola": "Já usou IA para obter respostas/cola",
    "acha_que_ChatGPT_ajuda": "Acredita que o ChatGPT pode ajudar"
}

for var, titulo in titulos_ini.items():
    col = f"ini_{var}"
    for nota_col, sufixo in [
        ("P1", "P1"), ("P2", "P2"),
        ("delta_P2_menos_P1", "diferenca_P2_P1")
    ]:
        salvar_boxplot_por_grupo(
            master, col, titulo,
            f"boxplot_inicial_{var}_{sufixo}.png",
            coluna_nota=nota_col
        )



# --- Formulário final: percepções sobre as etapas e a oficina. São análises de associação/descritivas, não medidas objetivas de aprendizagem.--- 
titulos_fin = {
    "avaliacao_questionando_IA": "Avaliação da etapa Questionando o uso de IA",
    "avaliacao_aprendendo_com_IA": "Avaliação da etapa Aprendendo com IA",
    "acredita_ser_possivel_aprender_com_IA": "Acredita ser possível aprender Matemática com IA",
    "pretende_aplicar_o_que_aprendeu": "Pretende aplicar o que aprendeu"
}

for var, titulo in titulos_fin.items():
    col = f"fin_{var}"
    for nota_col, sufixo in [
        ("P1", "P1"), ("P2", "P2"),
        ("delta_P2_menos_P1", "diferenca_P2_P1")
    ]:
        salvar_boxplot_por_grupo(
            master, col, titulo,
            f"boxplot_final_{var}_{sufixo}.png",
            coluna_nota=nota_col
        )




# ============================================================
# 10. TABELAS POR GRUPO E CORRELAÇÕES DE SPEARMAN
# ============================================================

def tabela_por_grupo(df, grupo, rotulo):
    linhas = []
    for categoria, bloco in df.groupby(grupo, dropna=True):
        for var, nome in [
            ("P1", "Parte 1 — uso livre"),
            ("P2", "Parte 2 — prompt orientador"),
            ("delta_P2_menos_P1", "Diferença P2 − P1")
        ]:
            d = bloco[var].dropna()
            linhas.append({
                "variavel_grupo": rotulo,
                "categoria": categoria,
                "nota_analisada": nome,
                **tabela_descritiva(d)
            })
    return pd.DataFrame(linhas)


for var, titulo in {**titulos_ini, **titulos_fin}.items():
    prefixo = "ini_" if var in titulos_ini else "fin_"
    col = prefixo + var
    if col in master and master[col].nunique(dropna=True) >= 2:
        tab = tabela_por_grupo(master, col, titulo)
        tab.round(3).to_csv(
            SAIDA / f"tabela_grupos_{var}.csv",
            index=False, encoding="utf-8-sig"
        )

# --- Spearman apenas para variáveis ordinais/numéricas codificadas. Não usada correlação para categorias nominais como sexo, curso ou região.--- 
variaveis_correlacao = [
    f"ini_{v}" for v in [
        "familiaridade", "frequencia_uso", "habilidade_matematica",
        "confianca_IA", "verifica_outras_fontes"
    ]
] + [
    f"fin_{v}" for v in [
        "avaliacao_questionando_IA", "avaliacao_aprendendo_com_IA"
    ]
]

resultados_corr = []
for x in variaveis_correlacao:
    if x not in master:
        continue
    for y in ["P1", "P2", "delta_P2_menos_P1"]:
        d = master[[x, y]].apply(pd.to_numeric, errors="coerce").dropna()
        if len(d) < 5 or d[x].nunique() < 2 or d[y].nunique() < 2:
            continue
        rho, p = stats.spearmanr(d[x], d[y])
        resultados_corr.append({
            "variavel": x,
            "resultado": y,
            "n": len(d),
            "rho_spearman": rho,
            "p_valor": p
        })

pd.DataFrame(resultados_corr).round(4).to_csv(
    SAIDA / "04_correlacoes_spearman.csv",
    index=False, encoding="utf-8-sig"
)


# ============================================================
# 11. GRÁFICO DA VARIAÇÃO INDIVIDUAL E RESUMO DE MELHORA
# ============================================================

if len(pares):
    contagem = pd.Series({
        "P2 maior": int((pares["delta_P2_menos_P1"] > 0).sum()),
        "Iguais": int((pares["delta_P2_menos_P1"] == 0).sum()),
        "P1 maior": int((pares["delta_P2_menos_P1"] < 0).sum())
    })
    contagem.rename_axis("resultado").reset_index(name="frequencia").to_csv(
        SAIDA / "05_resultado_comparacao_notas.csv",
        index=False, encoding="utf-8-sig"
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.histplot(pares["delta_P2_menos_P1"], bins=12, ax=ax)
    ax.axvline(0, color="red", linestyle="--", label="Sem diferença")
    ax.axvline(pares["delta_P2_menos_P1"].median(), color="black",
               linestyle=":", label=f"Mediana = {pares['delta_P2_menos_P1'].median():.2f}")
    ax.set_title("Distribuição das diferenças individuais (P2 − P1)")
    ax.set_xlabel("Diferença entre notas")
    ax.set_ylabel("Número de estudantes")
    ax.legend()
    fig.tight_layout()
    fig.savefig(SAIDA / "boxplot_02_distribuicao_diferencas.png", dpi=220)
    plt.close(fig)


# ============================================================
# 12. EXPORTAR BASE CONSOLIDADA ANONIMIZADA E DIAGNÓSTICO
# ============================================================

colunas_exportar = [
    "id_participante", "P1", "P2", "delta_P2_menos_P1",
    "situacao_comparacao", "p1_n_tentativas", "p2_n_tentativas"
] + [f"ini_{v}" for v in variaveis_ini] + [f"fin_{v}" for v in variaveis_fin]
colunas_exportar = [c for c in colunas_exportar if c in master.columns]

master[colunas_exportar].to_csv(
    SAIDA / "06_base_consolidada_anonimizada.csv",
    index=False, encoding="utf-8-sig"
)

diagnostico = pd.DataFrame([
    {"indicador": "Participantes com P1", "n": int(master["P1"].notna().sum())},
    {"indicador": "Participantes com P2", "n": int(master["P2"].notna().sum())},
    {"indicador": "Participantes com P1 e P2", "n": int(master[["P1", "P2"]].dropna().shape[0])},
    {"indicador": "Com formulário inicial associado", "n": int(master[[f"ini_{v}" for v in variaveis_ini]].notna().any(axis=1).sum())},
    {"indicador": "Com formulário final associado", "n": int(master[[f"fin_{v}" for v in variaveis_fin]].notna().any(axis=1).sum())},
    {"indicador": "Com P1, P2 e formulário inicial", "n": int(master[["P1", "P2"] + [f"ini_{v}" for v in variaveis_ini]].notna().all(axis=1).sum())},
    {"indicador": "Com P1, P2 e formulário final", "n": int(master[["P1", "P2"] + [f"fin_{v}" for v in variaveis_fin]].notna().all(axis=1).sum())},
])
diagnostico.to_csv(SAIDA / "00_diagnostico_amostra.csv",
                   index=False, encoding="utf-8-sig")

print("\n" + "=" * 65)
print("ANÁLISE CONCLUÍDA")
print("Pasta de resultados:", SAIDA.resolve())
print("Métrica principal usada:", METRICA_PRINCIPAL)
print("Pares válidos P1/P2:", len(pares))
print("Wilcoxon p-valor:", p_w)
print("\nArquivos principais:")
for arquivo in sorted(SAIDA.iterdir()):
    print(" -", arquivo.name)

print(
    "\nLEITURA DOS RESULTADOS:\n"
    "• P1 e P2 são atividades distintas, realizadas em condições diferentes.\n"
    "• Uma diferença positiva em P2 − P1 indica nota maior na Parte 2, "
    "não prova isoladamente que o prompt causou melhora.\n"
    "• O formulário final registra impressões/autopercepções dos estudantes; "
    "não deve ser tratado como teste objetivo de aprendizagem.\n"
    "• Confira revisar_correspondencias_de_nomes.csv. O script não associa "
    "nomes parecidos automaticamente.\n"
    "• Confira 00_diagnostico_amostra.csv antes de interpretar qualquer gráfico."
)

# ============================================================
# REUNIR TODAS AS TABELAS EM UM ÚNICO ARQUIVO EXCEL
# ============================================================

from pathlib import Path
import pandas as pd
import re

PASTA_SAIDA = SAIDA

ARQUIVO_EXCEL = PASTA_SAIDA / "tabelas_oficina_ia.xlsx"

arquivos_csv = sorted(PASTA_SAIDA.glob("*.csv"))

with pd.ExcelWriter(ARQUIVO_EXCEL, engine="openpyxl") as writer:
    for arquivo in arquivos_csv:
        try:
            tabela = pd.read_csv(arquivo, encoding="utf-8-sig")

            if tabela.empty and len(tabela.columns) == 0:
                print(f"Arquivo vazio ignorado: {arquivo.name}")
                continue

            nome_aba = arquivo.stem[:31]
            tabela.to_excel(writer, sheet_name=nome_aba, index=False)

        except pd.errors.EmptyDataError:
            print(f"Arquivo sem dados ignorado: {arquivo.name}")
            continue

print("\nPlanilha de tabelas criada em:")
print(ARQUIVO_EXCEL)

