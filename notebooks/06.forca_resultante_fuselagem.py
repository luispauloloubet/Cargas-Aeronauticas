from pathlib import Path
import re
import io
import pandas as pd
import numpy as np
import yaml
from src.config import dados, dados_avl, carregamentos
from src.carregamentos import salvar_planilha_abas

# =============================================================================
# 1. LEITURA DE PARÂMETROS E POSIÇÕES DO SCRIPT Estruturas_Fuselagem.py
# =============================================================================
caminho_yaml = dados / "parametros.yaml"
with open(caminho_yaml, "r", encoding="utf-8") as f:
    param = yaml.safe_load(f)

rho = float(param["atmosfera"]["rho"])
V_c = float(param["velocidades"]["V_c"])
V_d = float(param["velocidades"]["V_d"])
W = float(param["geometria_peso"]["W"])
S_yaml = float(param["geometria_peso"]["S"])

# Geometria e pontos de aplicação idênticos ao Estruturas_Fuselagem.py
ft_to_m = 0.3048
lenght_m = 59.17751644 * ft_to_m
b_asa_m = 18.94
cr_ev_m = 6.1975 * ft_to_m
b_eh_m = 7.05
D_motor_m = 0.74
Lenght_fus_motor_m = 17.614 * ft_to_m
R_fus_motor_m = Lenght_fus_motor_m / (2.0 * np.pi)
y_asa_motor_m = (D_motor_m / 2.0) + R_fus_motor_m

x_asa_m = lenght_m - (22.37100657 * ft_to_m) - (cr_ev_m * 3.0 / 4.0)
z_asa_m = -1.5 * ft_to_m

x_eh_m = x_asa_m + (23.67100657 * ft_to_m)
z_eh_m = 12.7413735 * ft_to_m

x_ev_m = x_asa_m + (22.37100657 * ft_to_m)
z_ca_ev_m = 9.0073894 * ft_to_m

x_motor_m = x_asa_m + (14.0 * ft_to_m)
z_motor_m = 3.4006543 * ft_to_m

POSICOES_ESTRUTURAS = {
    "Asa (Esq)":                  (x_asa_m,  -b_asa_m / 4.0, z_asa_m),
    "Asa (Dir)":                  (x_asa_m,   b_asa_m / 4.0, z_asa_m),
    "Motor (Esq)":                (x_motor_m, -y_asa_motor_m, z_motor_m),
    "Motor (Dir)":                (x_motor_m,  y_asa_motor_m, z_motor_m),
    "Empenagem Horizontal (Esq)": (x_eh_m,   -b_eh_m / 4.0,  z_eh_m),
    "Empenagem Horizontal (Dir)": (x_eh_m,    b_eh_m / 4.0,  z_eh_m),
    "Empenagem Vertical (CA)":    (x_ev_m,    0.0,           z_ca_ev_m),
}

# Tabela dos casos simétricos (02.automacao_AERONAVE.py / Diagrama V-n)
caminho_trim_csv = dados_avl / "tabela_trimagem_casos.csv"
df_trim = pd.read_csv(caminho_trim_csv)

V_a = float(df_trim.loc[df_trim["Caso"] == 0, "V"].iloc[0])
q_inf_va = 0.5 * rho * (V_a ** 2)
q_inf_vc = 0.5 * rho * (V_c ** 2)
q_inf_vd = 0.5 * rho * (V_d ** 2)

MAPA_COMPONENTES = {
    1: "Asa (Dir)",
    2: "Asa (Esq)",
    3: "Empenagem Vertical (CA)",
    4: "Empenagem Horizontal (Dir)",
    5: "Empenagem Horizontal (Esq)",
}

ORDEM_COMPONENTES = [
    "Asa (Esq)",
    "Asa (Dir)",
    "Empenagem Horizontal (Esq)",
    "Empenagem Horizontal (Dir)",
    "Empenagem Vertical (CA)",
]


def _distribuir_forca_nas_tiras(forca_total: float, pesos: np.ndarray) -> np.ndarray:
    soma = float(pesos.sum())
    if abs(soma) > 1e-9:
        return forca_total * (pesos / soma)
    n = len(pesos)
    return np.full(n, forca_total / max(n, 1))


# =============================================================================
# 2. EXTRAÇÃO DE FORÇAS E MOMENTOS DE TRANSPORTE PARA OS PONTOS DE APLICAÇÃO
# =============================================================================
def extrair_forcas_avl(caminho_txt: Path, q_inf: float, fator_seguranca: float = 1.0):
    """
    Lê um arquivo FS (Surface and Strip Forces) do AVL e calcula para cada
    componente:
      - Fx, Fy, Fz [N]: Forças resultantes
      - x_cp, y_cp, z_cp [m]: Centro de pressão real das tiras no AVL
      - Mt [N.m]: Momento torsor/rolamento (Mx) de transporte para o ponto P de Estruturas_Fuselagem.py
      - My [N.m]: Momento de arfagem/flexão longitudinal (Mc/4 + transporte de Fz e Fx para P)
      - Mz [N.m]: Momento de guinada/flexão lateral (transporte de Fy e Fx para P)
    """
    texto = caminho_txt.read_text(encoding="utf-8")

    m_ref = re.search(
        r"Sref\s*=\s*([-\d.]+)\s+Cref\s*=\s*([-\d.]+)\s+Bref\s*=\s*([-\d.]+)",
        texto,
    )
    Sref = float(m_ref.group(1)) if m_ref else S_yaml
    Cref = float(m_ref.group(2)) if m_ref else 1.850
    Bref = float(m_ref.group(3)) if m_ref else 18.944

    blocos_surf = re.split(r"(?=\s*Surface #\s*\d+)", texto)
    registros = []

    for bloco in blocos_surf:
        m_surf = re.search(r"Surface #\s*(\d+)\s+([^\n]+)", bloco)
        if not m_surf:
            continue

        surf_id = int(m_surf.group(1))
        surf_nome_avl = m_surf.group(2).strip()
        comp_nome = MAPA_COMPONENTES.get(surf_id, surf_nome_avl)

        def buscar_coef(nome_c):
            m = re.search(rf"{nome_c}\s*=\s*([-+]?\d*\.?\d+)", bloco)
            return float(m.group(1)) if m else 0.0

        CLsurf = buscar_coef("CLsurf")
        CYsurf = buscar_coef("CYsurf")
        CDsurf = buscar_coef("CDsurf")
        Clsurf = buscar_coef("Clsurf")
        Cmsurf = buscar_coef("Cmsurf")
        Cnsurf = buscar_coef("Cnsurf")

        q_fs = q_inf * fator_seguranca
        Fx = q_fs * Sref * CDsurf
        Fy = q_fs * Sref * CYsurf
        Fz = q_fs * Sref * CLsurf

        x_P, y_P, z_P = POSICOES_ESTRUTURAS[comp_nome]

        linhas_bloco = bloco.splitlines()
        idx_cabecalho = next(
            (i for i, ln in enumerate(linhas_bloco) if "Xle" in ln and "Yle" in ln and "Chord" in ln),
            None,
        )

        N_int, T_int, Mc4_int = 0.0, 0.0, 0.0
        Mt_transp, My_transp, Mz_transp = 0.0, 0.0, 0.0
        x_cp, y_cp, z_cp = x_P, y_P, z_P

        if idx_cabecalho is not None:
            linhas_dados = [linhas_bloco[idx_cabecalho]]
            for linha in linhas_bloco[idx_cabecalho + 1 :]:
                linha_str = linha.strip()
                if not linha_str or linha_str.startswith("---"):
                    break
                linhas_dados.append(linha)

            df_strips = pd.read_csv(io.StringIO("\n".join(linhas_dados)), sep=r"\s+")
            area_s = df_strips["Area"].to_numpy(dtype=float)
            chord_s = df_strips["Chord"].to_numpy(dtype=float)
            cl_norm_s = df_strips["cl_norm"].to_numpy(dtype=float)
            cl_s = df_strips["cl"].to_numpy(dtype=float)
            cd_s = df_strips["cd"].to_numpy(dtype=float)
            ai_s = df_strips["ai"].to_numpy(dtype=float)
            cm_c4_s = df_strips["cm_c/4"].to_numpy(dtype=float)

            # Posição de c/4 de cada tira no AVL
            x_i = df_strips["Xle"].to_numpy(dtype=float) + 0.25 * chord_s
            y_i = df_strips["Yle"].to_numpy(dtype=float)
            z_i = df_strips["Zle"].to_numpy(dtype=float)

            N_int = float((q_fs * area_s * cl_norm_s).sum())
            T_int = float((q_fs * area_s * (cd_s - cl_s * ai_s)).sum())
            Mc4_int = float((q_fs * area_s * (chord_s ** 2) * cm_c4_s).sum())

            # Distribuição consistente das forças Fx, Fy, Fz nas tiras
            if surf_id == 3:
                # Empenagem Vertical: força dominante é lateral (Fy ~ -cl_norm)
                pesos_principais = area_s * np.abs(cl_norm_s)
                Fy_i = _distribuir_forca_nas_tiras(Fy, -area_s * cl_norm_s)
                Fz_i = _distribuir_forca_nas_tiras(Fz, area_s * cl_s)
                Fx_i = _distribuir_forca_nas_tiras(Fx, area_s * cd_s)
                my_c4_total = 0.0
                mz_c4_total = Mc4_int
            else:
                # Asa e Empenagem Horizontal: força dominante é vertical (Fz ~ cl)
                pesos_principais = area_s * np.abs(cl_norm_s)
                Fz_i = _distribuir_forca_nas_tiras(Fz, area_s * cl_s)
                Fy_i = _distribuir_forca_nas_tiras(Fy, area_s * cl_norm_s)
                Fx_i = _distribuir_forca_nas_tiras(Fx, area_s * cd_s)
                my_c4_total = Mc4_int
                mz_c4_total = 0.0

            if float(pesos_principais.sum()) > 1e-9:
                x_cp = float((x_i * pesos_principais).sum() / pesos_principais.sum())
                y_cp = float((y_i * pesos_principais).sum() / pesos_principais.sum())
                z_cp = float((z_i * pesos_principais).sum() / pesos_principais.sum())
            else:
                x_cp = float(x_i.mean())
                y_cp = float(y_i.mean())
                z_cp = float(z_i.mean())

            # Momentos de transporte equivalentes no ponto P = (x_P, y_P, z_P) de Estruturas_Fuselagem.py:
            # 1) Torção/Rolamento (Mx / Mt): soma de Fz_i*(y_i - y_P) - Fy_i*(z_i - z_P)
            Mt_transp = float((Fz_i * (y_i - y_P) - Fy_i * (z_i - z_P)).sum())

            # 2) Arfagem/Flexão Longitudinal (My): Mc/4 + soma de Fz_i*(x_i - x_P) + Fx_i*(z_i - z_P)
            My_transp = float(my_c4_total + (Fz_i * (x_i - x_P) + Fx_i * (z_i - z_P)).sum())

            # 3) Guinada/Flexão Lateral (Mz): Mc/4_vert + soma de Fy_i*(x_i - x_P) - Fx_i*(y_i - y_P)
            Mz_transp = float(mz_c4_total + (Fy_i * (x_i - x_P) - Fx_i * (y_i - y_P)).sum())

        Mx_ref = q_fs * Sref * Bref * Clsurf
        My_ref = q_fs * Sref * Cref * Cmsurf
        Mz_ref = q_fs * Sref * Bref * Cnsurf

        registros.append(
            {
                "Surface_ID": surf_id,
                "Superficie_AVL": surf_nome_avl,
                "Componente": comp_nome,
                "x_P": round(x_P, 4),
                "y_P": round(y_P, 4),
                "z_P": round(z_P, 4),
                "x_CP": round(x_cp, 4),
                "y_CP": round(y_cp, 4),
                "z_CP": round(z_cp, 4),
                "Fx": Fx,
                "Fy": Fy,
                "Fz": Fz,
                "Mt": Mt_transp,
                "My": My_transp,
                "Mz": Mz_transp,
                "Mc4_aero": Mc4_int,
                "N_resultante": N_int,
                "T_resultante": T_int,
                "Mx_ref": Mx_ref,
                "My_ref": My_ref,
                "Mz_ref": Mz_ref,
                "CLsurf": CLsurf,
                "CYsurf": CYsurf,
                "CDsurf": CDsurf,
            }
        )

    df_out = pd.DataFrame(registros)
    df_out["Componente"] = pd.Categorical(
        df_out["Componente"], categories=ORDEM_COMPONENTES, ordered=True
    )
    return df_out.sort_values("Componente").reset_index(drop=True)


# =============================================================================
# 3. CATÁLOGO DOS CASOS (CASOS 1 A 5 DO V-n E CASOS FAR 23)
# =============================================================================
catalogo_casos = []

# Empuxo total T_max [N] por Caso do Diagrama V-n (conforme tabela de motor: 10^4 N)
T_MAX_VN_POR_CASO = {
    0: 2.4392e4,
    1: 2.5747e4,
    2: 2.0539e4,
    3: 2.1251e4,
    4: 2.1251e4,
}

# 3.1 Casos 1 a 5 do Diagrama V-n (arquivos distribuicao_caso_0..4.txt)
for _, row in df_trim.iterrows():
    arq_idx = int(row["Caso"])
    caso_num = arq_idx + 1  # Numerados de 1 a 5
    catalogo_casos.append(
        {
            "Caso_ID": f"Caso {caso_num} (V-n)",
            "Chave_Dict": f"Caso {caso_num}: V-n Simétrico (n={row['n']:.2f}, V={row['V']:.1f} m/s)",
            "Origem": "02.automacao_AERONAVE.py",
            "Arquivo": f"distribuicao_caso_{arq_idx}.txt",
            "V_ms": float(row["V"]),
            "n": float(row["n"]),
            "CL_alvo": float(row["CL_alvo"]),
            "q_inf": float(row["q_inf"]),
            "T_max_N": T_MAX_VN_POR_CASO.get(arq_idx, 2.1251e4),
        }
    )

# 3.2 Casos de Empenagem FAR 23 (03.automacao_EMPENAGENS_FAR23.py)
caminho_far_csv = dados_avl / "matriz_casos_empenagem_FAR23.csv"
if caminho_far_csv.exists():
    df_far = pd.read_csv(caminho_far_csv)
    for _, row in df_far.iterrows():
        cid = str(row["id"])
        desc = str(row["descricao"])
        if "VA" in desc or "EH_2" in cid:
            v_caso, q_caso, t_max_caso = V_a, q_inf_va, T_MAX_VN_POR_CASO[0]
        else:
            v_caso, q_caso, t_max_caso = V_d, q_inf_vd, T_MAX_VN_POR_CASO[4]
        n_caso = (float(row["cl_alvo"]) * q_caso * S_yaml) / W

        catalogo_casos.append(
            {
                "Caso_ID": cid,
                "Chave_Dict": f"{cid}: {desc}",
                "Origem": "03.automacao_EMPENAGENS_FAR23.py",
                "Arquivo": f"distribuicao_caso_{cid}.txt",
                "V_ms": v_caso,
                "n": n_caso,
                "CL_alvo": float(row["cl_alvo"]),
                "q_inf": q_caso,
                "T_max_N": t_max_caso,
            }
        )


# =============================================================================
# 4. PROCESSAMENTO E EXPORTAÇÃO DAS TABELAS E DO ARQUIVO CASOS_CARGA
# =============================================================================
def processar_todos_os_casos(fator_seguranca: float = 1.0):
    tabelas = []
    casos_carga_dict = {}

    for meta in catalogo_casos:
        caminho_txt = dados_avl / meta["Arquivo"]
        if not caminho_txt.exists():
            print(f"[AVISO] Arquivo não encontrado: {caminho_txt}")
            continue

        df_forca = extrair_forcas_avl(
            caminho_txt, q_inf=meta["q_inf"], fator_seguranca=fator_seguranca
        )

        for col in ["Caso_ID", "Chave_Dict", "Origem", "Arquivo", "V_ms", "n", "CL_alvo", "q_inf"]:
            df_forca[col] = meta[col]

        tabelas.append(df_forca)

        comp_zero = {"Fx": 0.0, "Fy": 0.0, "Fz": 0.0, "Mt": 0.0, "My": 0.0, "Mz": 0.0}
        fx_mot = round((-meta["T_max_N"] / 2.0) * fator_seguranca, 2)
        fz_mot = round((-4000.0 * meta["n"]) * fator_seguranca, 2)

        entrada_caso = {
            "delta_P": 50000.0,
            "Asa (Esq)": dict(comp_zero),
            "Asa (Dir)": dict(comp_zero),
            "NLG (Trem de Nariz)": dict(comp_zero),
            "MLG (Trem Principal - Esq)": dict(comp_zero),
            "MLG (Trem Principal - Dir)": dict(comp_zero),
            "Motor (Esq)": {"Fx": fx_mot, "Fy": 0.0, "Fz": fz_mot, "Mt": 0.0, "My": 0.0, "Mz": 0.0},
            "Motor (Dir)": {"Fx": fx_mot, "Fy": 0.0, "Fz": fz_mot, "Mt": 0.0, "My": 0.0, "Mz": 0.0},
            "Empenagem Horizontal (Esq)": dict(comp_zero),
            "Empenagem Horizontal (Dir)": dict(comp_zero),
            "Empenagem Vertical (CA)": dict(comp_zero),
        }

        for _, r in df_forca.iterrows():
            comp = str(r["Componente"])
            entrada_caso[comp] = {
                "Fx": round(float(r["Fx"]), 2),
                "Fy": round(float(r["Fy"]), 2),
                "Fz": round(float(r["Fz"]), 2),
                "Mt": round(float(r["Mt"]), 2),
                "My": round(float(r["My"]), 2),
                "Mz": round(float(r["Mz"]), 2),
            }

        casos_carga_dict[meta["Chave_Dict"]] = entrada_caso

    df_consolidado = pd.concat(tabelas, ignore_index=True)
    colunas_ordem = [
        "Caso_ID",
        "Origem",
        "Chave_Dict",
        "V_ms",
        "n",
        "q_inf",
        "Componente",
        "x_P",
        "y_P",
        "z_P",
        "x_CP",
        "y_CP",
        "z_CP",
        "Fx",
        "Fy",
        "Fz",
        "Mt",
        "My",
        "Mz",
        "Mc4_aero",
        "N_resultante",
        "T_resultante",
        "Mx_ref",
        "My_ref",
        "Mz_ref",
        "CLsurf",
        "CYsurf",
        "CDsurf",
    ]
    return df_consolidado[colunas_ordem], casos_carga_dict


def salvar_dicionario_python(casos_dict: dict, caminho_py: Path):
    """Gera o módulo casos_carga_fuselagem.py com Fx, Fy, Fz, Mt, My, Mz em condição ULTIMATE (FS=1.5)."""
    linhas = [
        "# Dicionário gerado automaticamente a partir dos resultados do AVL",
        "# Cargas e momentos já na condição ULTIMATE (Fator de Segurança = 1.5 aplicado)",
        "# Inclui forças (Fx, Fy, Fz) e momentos de transporte (Mt, My, Mz)",
        "# referenciados exatamente aos pontos de aplicação de 08.estruturas_fuselagem.py",
        "CASOS_CARGA = {",
    ]
    for nome_caso, comps in casos_dict.items():
        linhas.append(f"    {nome_caso!r}: {{")
        linhas.append(f"        'delta_P': {comps['delta_P']:.1f},")
        for k, v in comps.items():
            if k == "delta_P":
                continue
            chave_pad = f"'{k}':".ljust(30)
            linhas.append(
                f"        {chave_pad} {{'Fx': {v['Fx']:10.2f}, 'Fy': {v['Fy']:10.2f}, 'Fz': {v['Fz']:11.2f}, "
                f"'Mt': {v['Mt']:10.2f}, 'My': {v['My']:10.2f}, 'Mz': {v['Mz']:10.2f}}},"
            )
        linhas.append("    },")
    linhas.append("}\n")
    caminho_py.write_text("\n".join(linhas), encoding="utf-8")


if __name__ == "__main__":
    df_limite, dict_limite = processar_todos_os_casos(fator_seguranca=1.0)
    df_ultimate, dict_ultimate = processar_todos_os_casos(fator_seguranca=1.5)

    resumo_superficies = []
    for caso_id, grp in df_limite.groupby("Caso_ID", sort=False):
        asa = grp[grp["Componente"].astype(str).str.startswith("Asa")]
        eh = grp[grp["Componente"].astype(str).str.startswith("Empenagem Horizontal")]
        ev = grp[grp["Componente"].astype(str).str.startswith("Empenagem Vertical")]

        for nome_s, sub in [("Asa Total (Esq+Dir)", asa), ("EH Total (Esq+Dir)", eh), ("EV (CA)", ev)]:
            resumo_superficies.append(
                {
                    "Caso_ID": caso_id,
                    "Origem": sub["Origem"].iloc[0],
                    "Superficie": nome_s,
                    "V_ms": sub["V_ms"].iloc[0],
                    "q_inf": sub["q_inf"].iloc[0],
                    "Fx_Limite [N]": round(sub["Fx"].sum(), 2),
                    "Fy_Limite [N]": round(sub["Fy"].sum(), 2),
                    "Fz_Limite [N]": round(sub["Fz"].sum(), 2),
                    "Mt_Limite [N.m]": round(sub["Mt"].sum(), 2),
                    "My_Limite [N.m]": round(sub["My"].sum(), 2),
                    "Mz_Limite [N.m]": round(sub["Mz"].sum(), 2),
                    "Fx_Ultimate [N]": round(sub["Fx"].sum() * 1.5, 2),
                    "Fy_Ultimate [N]": round(sub["Fy"].sum() * 1.5, 2),
                    "Fz_Ultimate [N]": round(sub["Fz"].sum() * 1.5, 2),
                    "Mt_Ultimate [N.m]": round(sub["Mt"].sum() * 1.5, 2),
                    "My_Ultimate [N.m]": round(sub["My"].sum() * 1.5, 2),
                    "Mz_Ultimate [N.m]": round(sub["Mz"].sum() * 1.5, 2),
                }
            )

    df_resumo = pd.DataFrame(resumo_superficies)

    # Salva abas de forças resultantes na planilha carregamentos_fuselagem.xlsx
    caminho_xlsx_fus = carregamentos / "carregamentos_fuselagem.xlsx"
    abas_resultantes = {
        "Resumo_Asa_EH_EV": df_resumo,
        "Resultantes_Limite": df_limite,
        "Resultantes_Ultimate": df_ultimate,
    }
    salvar_planilha_abas(caminho_xlsx_fus, abas_resultantes)

    caminho_dict_py = carregamentos / "casos_carga_fuselagem.py"
    salvar_dicionario_python(dict_ultimate, caminho_dict_py)

    print(f"[OK] Planilha de forças resultantes salva em: {caminho_xlsx_fus}")
    print(f"[OK] Dicionário Python CASOS_CARGA (ULTIMATE, FS=1.5) salvo em: {caminho_dict_py}")
