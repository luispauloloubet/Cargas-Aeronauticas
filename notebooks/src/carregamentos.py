from pathlib import Path
import pandas as pd
import numpy as np
from src.config import dados, dados_avl
import yaml

caminho_yaml = dados / "parametros.yaml"

with open(caminho_yaml, "r", encoding="utf-8") as f:
    param = yaml.safe_load(f)

for grupo in param.values():
    globals().update(grupo)


def salvar_planilha_abas(caminho_xlsx: Path, abas_dict: dict):
    """
    Salva um dicionário {nome_aba: DataFrame} em um único arquivo Excel (.xlsx),
    onde cada chave do dicionário corresponde a uma aba da planilha.
    """
    caminho_xlsx.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(caminho_xlsx, engine="openpyxl") as writer:
        for nome_aba, df_aba in abas_dict.items():
            aba_limpa = str(nome_aba)[:31]
            df_aba.to_excel(writer, sheet_name=aba_limpa, index=False)


def analises(df_vn):
    """
    Recebe DataFrame com colunas ['V', 'n'].
    Calcula CL alvo e pressão dinâmica para cada ponto da envolvente.
    """
    df = df_vn.copy()
    df["q_inf"] = 0.5 * rho * (df["V"] ** 2)
    df["CL"] = (df["n"] * W) / (df["q_inf"] * S)
    df.to_csv(dados / "CLs para analise.csv", index=False)
    return df


def calcular_esforcos_viga_semienvergadura(df_cargas: pd.DataFrame, s_raiz: float = 0.0) -> pd.DataFrame:
    """
    Integra as cargas distribuídas seccionais (N_prime, T_prime, M_prime_c4)
    da ponta da superfície até cada estação s (incluindo a raiz s = s_raiz),
    obtendo os esforços solicitantes internos:
      - V_N [N]:  Esforço Cortante Normal
      - V_T [N]:  Esforço Cortante Tangencial
      - M_F [Nm]: Momento Fletor Normal
      - M_T [Nm]: Momento Fletor Tangencial
      - M_t [Nm]: Momento Torsor Seccional
    """
    df_ord = df_cargas.sort_values("semienvergadura").reset_index(drop=True)
    s_vals = df_ord["semienvergadura"].to_numpy(dtype=float)
    n_vals = df_ord["N_prime"].to_numpy(dtype=float)
    t_vals = df_ord["T_prime"].to_numpy(dtype=float)
    m_vals = df_ord["M_prime_c4"].to_numpy(dtype=float)

    # Inclui a estação exata da raiz (s = 0.0) se ainda não estiver presente
    if s_vals[0] > s_raiz + 1e-5:
        s_ext = np.concatenate([[s_raiz], s_vals])
        n_ext = np.concatenate([[n_vals[0]], n_vals])
        t_ext = np.concatenate([[t_vals[0]], t_vals])
        m_ext = np.concatenate([[m_vals[0]], m_vals])
    else:
        s_ext, n_ext, t_ext, m_ext = s_vals, n_vals, t_vals, m_vals

    num_pts = len(s_ext)
    V_N = np.zeros(num_pts)
    V_T = np.zeros(num_pts)
    M_F = np.zeros(num_pts)
    M_T = np.zeros(num_pts)
    M_t = np.zeros(num_pts)

    for i in range(num_pts):
        s_sub = s_ext[i:]
        n_sub = n_ext[i:]
        t_sub = t_ext[i:]
        m_sub = m_ext[i:]
        bracos = s_sub - s_ext[i]

        V_N[i] = np.trapezoid(n_sub, s_sub)
        V_T[i] = np.trapezoid(t_sub, s_sub)
        M_F[i] = np.trapezoid(n_sub * bracos, s_sub)
        M_T[i] = np.trapezoid(t_sub * bracos, s_sub)
        M_t[i] = np.trapezoid(m_sub, s_sub)

    return pd.DataFrame(
        {
            "semienvergadura": s_ext,
            "V_N": V_N,
            "V_T": V_T,
            "M_F": M_F,
            "M_T": M_T,
            "M_t": M_t,
        }
    )


def _chave_legenda_caso(caso):
    """Converte índices numéricos 0..4 em 1..5 para os casos do diagrama V-n."""
    if isinstance(caso, (int, np.integer)) or (isinstance(caso, str) and caso.isdigit()):
        return int(caso) + 1
    return caso


def carregamento_asa(df_analises, n_estacoes=25):
    """
    Lê a saída FS do AVL em dados/avl/ para cada caso da tabela df_analises, calcula as forças
    lineares [N/m] normais (N') e tangenciais (T') à corda local, além de L' e Mc/4.
    Retorna dicionário indexado de 1 a 5 para os casos do diagrama V-n.
    """
    resultados = {}

    for caso in df_analises.index:
        q_inf = df_analises.loc[caso, "q_inf"]
        caminho_txt = dados_avl / f"distribuicao_caso_{caso}.txt"

        if not caminho_txt.exists():
            print(f"[Aviso] Ficheiro não encontrado: {caminho_txt.name}")
            continue

        df_avl = pd.read_csv(
            caminho_txt,
            sep=r"\s+",
            skiprows=21,
            nrows=n_estacoes,
        )

        fator_ultimate = 1.5
        chord = df_avl["Chord"]
        cl_norm = df_avl["cl_norm"]
        cl = df_avl["cl"]
        cd = df_avl["cd"]
        ai = df_avl["ai"]
        cm = df_avl["cm_c/4"]

        df_avl["N_prime"] = fator_ultimate * q_inf * chord * cl_norm
        df_avl["T_prime"] = fator_ultimate * q_inf * chord * (cd - (cl * ai))
        df_avl["L_prime"] = fator_ultimate * q_inf * df_avl["c_cl"]
        df_avl["M_prime_c4"] = fator_ultimate * q_inf * cm * (chord ** 2)

        df_avl = df_avl.rename(columns={"Yle": "semienvergadura"})
        colunas_finais = ["j", "semienvergadura", "N_prime", "T_prime", "L_prime", "M_prime_c4"]
        df_saida = df_avl[colunas_finais].copy()

        chave = _chave_legenda_caso(caso)
        resultados[chave] = df_saida

    return resultados


def carregamento_assimetrico_asa(nome_txt="distribuicao_assimetrica_VC.txt", q_inf=26467.003):
    """
    Lê as duas semi-asas (Surface #1 e Surface #2) de um caso assimétrico de rolamento
    e calcula tanto as cargas distribuídas [N/m] quanto os esforços solicitantes
    ao longo da envergadura completa y in [-b/2, +b/2].
    """
    caminho_txt = dados_avl / nome_txt
    if not caminho_txt.exists():
        return None, None

    df_dir = pd.read_csv(caminho_txt, sep=r"\s+", skiprows=21, nrows=25)
    df_esq = pd.read_csv(caminho_txt, sep=r"\s+", skiprows=63, nrows=25)
    df_full = pd.concat([df_esq, df_dir], ignore_index=True).sort_values(by="Yle").reset_index(drop=True)

    fu = 1.5
    chord = df_full["Chord"]
    cl_norm = df_full["cl_norm"]
    cl = df_full["cl"]
    cd = df_full["cd"]
    ai = df_full["ai"]
    cm = df_full["cm_c/4"]

    df_full["N_prime"] = fu * q_inf * chord * cl_norm
    df_full["T_prime"] = fu * q_inf * chord * (cd - (cl * ai))
    df_full["L_prime"] = fu * q_inf * df_full["c_cl"]
    df_full["M_prime_c4"] = fu * q_inf * cm * (chord ** 2)

    df_full = df_full.rename(columns={"Yle": "Envergadura"})
    colunas_finais = ["Envergadura", "N_prime", "T_prime", "L_prime", "M_prime_c4"]
    df_cargas = df_full[colunas_finais].copy()

    # Calcula esforços solicitantes em cada semi-asa (da ponta até a raiz y = 0)
    df_esq_sub = df_cargas[df_cargas["Envergadura"] < 0].copy()
    df_esq_sub["semienvergadura"] = df_esq_sub["Envergadura"].abs()
    esf_esq = calcular_esforcos_viga_semienvergadura(df_esq_sub, s_raiz=0.0)
    esf_esq["Envergadura"] = -esf_esq["semienvergadura"]
    # Na semi-asa esquerda (y < 0), o corte da ponta até y tem normal oposta em y
    esf_esq["V_N"] = -esf_esq["V_N"]
    esf_esq["V_T"] = -esf_esq["V_T"]

    df_dir_sub = df_cargas[df_cargas["Envergadura"] > 0].copy()
    df_dir_sub["semienvergadura"] = df_dir_sub["Envergadura"]
    esf_dir = calcular_esforcos_viga_semienvergadura(df_dir_sub, s_raiz=0.0)
    esf_dir["Envergadura"] = esf_dir["semienvergadura"]

    df_esforcos = (
        pd.concat([esf_esq.iloc[1:][::-1], esf_dir], ignore_index=True)
        .sort_values("Envergadura")
        .reset_index(drop=True)
    )
    df_esforcos = df_esforcos[["Envergadura", "V_N", "V_T", "M_F", "M_T", "M_t"]]

    return df_cargas, df_esforcos


def carregamento_ev(df_analises, n_estacoes=16, z_raiz_ev=2.186):
    """
    Lê a saída FS do AVL para o estabilizador vertical (Surface # 3), convertendo
    a coordenada Zle para a envergadura da EV (Zle - z_raiz_ev) [m] a partir da raiz,
    de modo a ficar coerente com as demais superfícies.
    """
    resultados = {}

    for caso in df_analises.index:
        q_inf = df_analises.loc[caso, "q_inf"]
        caminho_txt = dados_avl / f"distribuicao_caso_{caso}.txt"

        if not caminho_txt.exists():
            print(f"[Aviso] Ficheiro não encontrado: {caminho_txt.name}")
            continue

        df_avl = pd.read_csv(
            caminho_txt,
            sep=r"\s+",
            skiprows=105,
            nrows=n_estacoes,
        )

        fator_ultimate = 1.5
        chord = df_avl["Chord"]
        cl_norm = df_avl["cl_norm"]
        cl = df_avl["cl"]
        cd = df_avl["cd"]
        ai = df_avl["ai"]
        cm = df_avl["cm_c/4"]

        df_avl["N_prime"] = fator_ultimate * q_inf * chord * cl_norm
        df_avl["T_prime"] = fator_ultimate * q_inf * chord * (cd - (cl * ai))
        df_avl["L_prime"] = fator_ultimate * q_inf * df_avl["c_cl"]
        df_avl["M_prime_c4"] = fator_ultimate * q_inf * cm * (chord ** 2)

        # Converte a altura absoluta Zle para a envergadura da EV a partir da raiz (0 m na raiz)
        z_base = min(float(z_raiz_ev), float(df_avl["Zle"].min()))
        df_avl["semienvergadura"] = df_avl["Zle"] - z_base

        colunas_finais = ["j", "semienvergadura", "N_prime", "T_prime", "L_prime", "M_prime_c4"]
        df_saida = df_avl[colunas_finais].copy()

        chave = _chave_legenda_caso(caso)
        resultados[chave] = df_saida

    return resultados


def carregamento_eh(df_analises, n_estacoes=16):
    """
    Lê a saída FS do AVL para a semi-envergadura do estabilizador horizontal (Surface # 4),
    calculando as forças normais (N'), tangenciais (T'), L' e Mc/4 ao longo de Y.
    """
    resultados = {}

    for caso in df_analises.index:
        q_inf = df_analises.loc[caso, "q_inf"]
        caminho_txt = dados_avl / f"distribuicao_caso_{caso}.txt"

        if not caminho_txt.exists():
            print(f"[Aviso] Ficheiro não encontrado: {caminho_txt.name}")
            continue

        df_avl = pd.read_csv(
            caminho_txt,
            sep=r"\s+",
            skiprows=138,
            nrows=n_estacoes,
        )

        fator_ultimate = 1.5
        chord = df_avl["Chord"]
        cl_norm = df_avl["cl_norm"]
        cl = df_avl["cl"]
        cd = df_avl["cd"]
        ai = df_avl["ai"]
        cm = df_avl["cm_c/4"]

        df_avl["L_prime"] = fator_ultimate * q_inf * df_avl["c_cl"]
        df_avl["T_prime"] = fator_ultimate * q_inf * chord * (cd - (cl * ai))
        df_avl["N_prime"] = fator_ultimate * q_inf * chord * cl_norm
        df_avl["M_prime_c4"] = fator_ultimate * q_inf * cm * (chord ** 2)

        df_avl = df_avl.rename(columns={"Yle": "semienvergadura"})
        colunas_finais = ["j", "semienvergadura", "N_prime", "T_prime", "L_prime", "M_prime_c4"]
        df_saida = df_avl[colunas_finais].copy()

        chave = _chave_legenda_caso(caso)
        resultados[chave] = df_saida

    return resultados
