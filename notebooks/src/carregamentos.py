import pandas as pd
import numpy as np
from src.config import dados, carregamentos
import yaml

caminho_yaml = dados / "parametros.yaml"

with open(caminho_yaml, "r", encoding="utf-8") as f:
    param = yaml.safe_load(f)

for grupo in param.values():
    globals().update(grupo)

def analises(df_vn):
    """
    Recebe DataFrame com colunas ['V', 'n'].
    Calcula CL alvo e pressão dinâmica para cada ponto da envolvente.
    """
    df = df_vn.copy()

    df['q_inf'] = 0.5 * rho * (df['V'] ** 2)
    df['CL'] = (df['n'] * W) / (df['q_inf'] * S)

    df.to_csv(dados / 'CLs para analise.csv', index=False)
    
    return df


def carregamento_asa(df_analises, n_estacoes=50):
    """
    Lê a saída FS do AVL para cada caso da tabela df_analises, calcula as forças
    lineares [N/m] normais (N') e tangenciais (T') à corda local, além de L',
    exportando apenas as colunas solicitadas.
    """
    pasta_carregamentos = dados / 'carregamentos'
    pasta_carregamentos.mkdir(parents=True, exist_ok=True)

    pasta_saida = carregamentos / 'asa'
    pasta_saida.mkdir(parents=True, exist_ok=True)
    
    resultados = {}

    for caso in df_analises.index:
        q_inf = df_analises.loc[caso, 'q_inf']
        caminho_txt = pasta_carregamentos / f"distribuicao_caso_{caso}.txt"
        
        if not caminho_txt.exists():
            print(f"[Aviso] Ficheiro não encontrado: {caminho_txt.name}")
            continue

        # Leitura direta das estações da semi-asa no relatório do AVL
        df_avl = pd.read_csv(
            caminho_txt,
            sep=r'\s+',
            skiprows=21,
            nrows=n_estacoes
        )

        chord = df_avl['Chord']
        cl_norm = df_avl['cl_norm']
        cl = df_avl['cl']
        cd = df_avl['cd']
        ai = df_avl['ai']  # radianos

        # Forças distribuídas seccionais [N/m]
        df_avl['N_prime'] = q_inf * chord * cl_norm
        df_avl['T_prime'] = q_inf * chord * (cd - (cl * ai))
        df_avl['L_prime'] = q_inf * df_avl['c_cl']

        # Renomeia e filtra as colunas
        df_avl = df_avl.rename(columns={'Yle': 'semienvergadura'})
        colunas_finais = ['j', 'semienvergadura', 'N_prime', 'T_prime', 'L_prime']
        df_saida = df_avl[colunas_finais].copy()

        # Salva o arquivo CSV
        arquivo_csv = pasta_saida / f'carregamento asa [envergadura] caso {caso}.csv'
        df_saida.to_csv(arquivo_csv, index=False)
        
        resultados[caso] = df_saida

    return resultados


def carregamento_ev(df_analises, n_estacoes=16):
    """
    Lê a saída FS do AVL para o estabilizador vertical (Surface # 3), calcula a força
    lateral seccional distribuída (N'), a tangencial (T') e L' [N/m] ao longo da altura Z.
    """
    pasta_carregamentos = dados / "carregamentos"
    pasta_carregamentos.mkdir(parents=True, exist_ok=True)

    pasta_saida = carregamentos / 'ev'
    pasta_saida.mkdir(parents=True, exist_ok=True)

    resultados = {}

    for caso in df_analises.index:
        q_inf = df_analises.loc[caso, "q_inf"]
        caminho_txt = pasta_carregamentos / f"distribuicao_caso_{caso}.txt"

        if not caminho_txt.exists():
            print(f"[Aviso] Ficheiro não encontrado: {caminho_txt.name}")
            continue

        # Leitura da Vertical Tail (Surface # 3: j = 51 a 66)
        df_avl = pd.read_csv(
            caminho_txt,
            sep=r"\s+",
            skiprows=105,
            nrows=n_estacoes,
        )

        chord = df_avl["Chord"]
        cl_norm = df_avl["cl_norm"]
        cl = df_avl["cl"]
        cd = df_avl["cd"]
        ai = df_avl["ai"]

        # Forças distribuídas seccionais [N/m] (N' atua na direção lateral Y)
        df_avl["N_prime"] = q_inf * chord * cl_norm
        df_avl["T_prime"] = q_inf * chord * (cd - (cl * ai))
        df_avl["L_prime"] = q_inf * df_avl["c_cl"]

        # Renomeia Zle para altura e filtra colunas
        df_avl = df_avl.rename(columns={"Zle": "altura"})
        colunas_finais = ["j", "altura", "N_prime", "T_prime", "L_prime"]
        df_saida = df_avl[colunas_finais].copy()

        # Salva o arquivo CSV
        arquivo_csv = pasta_saida / f"carregamento EV [altura] caso {caso}.csv"
        df_saida.to_csv(arquivo_csv, index=False)

        resultados[caso] = df_saida

    return resultados


def carregamento_eh(df_analises, n_estacoes=16):
    """
    Lê a saída FS do AVL para a semi-envergadura do estabilizador horizontal (Surface # 4),
    calculando as forças normais (N'), tangenciais (T') e L' [N/m] ao longo de Y.
    """
    pasta_carregamentos = dados / "carregamentos"
    pasta_carregamentos.mkdir(parents=True, exist_ok=True)

    pasta_saida = carregamentos / 'eh'
    pasta_saida.mkdir(parents=True, exist_ok=True)

    resultados = {}

    for caso in df_analises.index:
        q_inf = df_analises.loc[caso, "q_inf"]
        caminho_txt = pasta_carregamentos / f"distribuicao_caso_{caso}.txt"

        if not caminho_txt.exists():
            print(f"[Aviso] Ficheiro não encontrado: {caminho_txt.name}")
            continue

        # Leitura da Horizontal Tail (Surface # 4: j = 67 a 82)
        df_avl = pd.read_csv(
            caminho_txt,
            sep=r"\s+",
            skiprows=138,
            nrows=n_estacoes,
        )

        chord = df_avl["Chord"]
        cl_norm = df_avl["cl_norm"]
        cl = df_avl["cl"]
        cd = df_avl["cd"]
        ai = df_avl["ai"]

        # Forças distribuídas seccionais [N/m]
        df_avl["N_prime"] = q_inf * chord * cl_norm
        df_avl["T_prime"] = q_inf * chord * (cd - (cl * ai))
        df_avl["L_prime"] = q_inf * df_avl["c_cl"]

        # Renomeia e filtra as colunas
        df_avl = df_avl.rename(columns={"Yle": "semienvergadura"})
        colunas_finais = ["j", "semienvergadura", "N_prime", "T_prime", "L_prime"]
        df_saida = df_avl[colunas_finais].copy()

        # Salva o arquivo CSV
        arquivo_csv = pasta_saida / f"carregamento EH [envergadura] caso {caso}.csv"
        df_saida.to_csv(arquivo_csv, index=False)

        resultados[caso] = df_saida

    return resultados