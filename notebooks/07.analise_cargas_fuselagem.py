from pathlib import Path
import io
import re
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from src.config import dados_avl, carregamentos, imagens_fuselagem, esforcos_fuselagem
from src.carregamentos import salvar_planilha_abas
from src.graficos import plotar_curvas_fuselagem

# =============================================================================
# 1. TABELA DE CONDIÇÕES DE VOO DO DIAGRAMA V-n (CASOS 1 A 5)
# =============================================================================
TABELA_VN_MOTOR = pd.DataFrame(
    [
        {"Caso": 1, "arq_idx": 0, "V": 98.50,  "n":  3.800, "q_inf":  5647.0, "CL":  1.528, "T_max_1e4N": 2.4392},
        {"Caso": 2, "arq_idx": 1, "V": 73.46,  "n": -1.520, "q_inf":  3305.0, "CL": -1.100, "T_max_1e4N": 2.5747},
        {"Caso": 3, "arq_idx": 2, "V": 207.87, "n": -3.570, "q_inf": 26467.0, "CL": -0.339, "T_max_1e4N": 2.0539},
        {"Caso": 4, "arq_idx": 3, "V": 291.02, "n": -2.628, "q_inf": 51875.0, "CL": -0.121, "T_max_1e4N": 2.1251},
        {"Caso": 5, "arq_idx": 4, "V": 291.02, "n":  3.800, "q_inf": 51875.0, "CL":  0.175, "T_max_1e4N": 2.1251},
    ]
)
TABELA_VN_MOTOR["T_max_N"] = TABELA_VN_MOTOR["T_max_1e4N"] * 1e4

# =============================================================================
# 2. GEOMETRIA DA FUSELAGEM DE 18m E PONTOS DE JUNÇÃO ASA-FUSELAGEM
# =============================================================================
ft_to_m = 0.3048
L_fus_m = 18.0

b_asa_m  = 18.944
cr_asa_m = 2.884
cr_eh_m  = 1.690
b_eh_m   = 7.050
cr_ev_m  = 1.889

Lcabpax_m = 26.2467 * ft_to_m
Lcabpt_m  = 8.2021 * ft_to_m
Lradome_m = 3.0 * ft_to_m

W_motor_unitario_N = 4000.0

# Apoios estaticamente determinados nos pontos de junção asa-fuselagem:
#   - Apoio Dianteiro A (Pino / Apoio Fixo): x_A = 8.901 m
#   - Apoio Traseiro B (Rolete / Apoio Móvel): x_B = 11.785 m
x_apoio_A = 8.901
x_apoio_B = x_apoio_A + cr_asa_m  # 11.785 m

x_asa_m   = 9.802
z_asa_m   = -1.5 * ft_to_m

x_motor_m = x_asa_m + (14.0 * ft_to_m)  # 14.069 m
L_motor_m = 1.200                        # Comprimento de fixação do pilono do motor [m]
z_motor_m = 3.4006543 * ft_to_m

x_ev_le_m = 14.800
x_ev_te_m = x_ev_le_m + cr_ev_m          # 16.689 m
z_ca_ev_m = 9.0073894 * ft_to_m

x_eh_le_m = 16.000
x_eh_te_m = x_eh_le_m + cr_eh_m          # 17.690 m
z_eh_m    = 4.577

REGIOES_CARGA = {
    "Asa":   {"x_ini": x_apoio_A,                 "x_fim": x_apoio_B,                 "z": z_asa_m},
    "Motor": {"x_ini": x_motor_m - L_motor_m / 2, "x_fim": x_motor_m + L_motor_m / 2, "z": z_motor_m},
    "EV":    {"x_ini": x_ev_le_m,                 "x_fim": x_ev_te_m,                 "z": z_ca_ev_m},
    "EH":    {"x_ini": x_eh_le_m,                 "x_fim": x_eh_te_m,                 "z": z_eh_m},
}

x_stations_fus = np.array([0.0, Lradome_m + Lcabpt_m, Lradome_m + Lcabpt_m + Lcabpax_m, L_fus_m])
z_offsets_fus  = np.array([0.0, 1.8044619 * ft_to_m, 1.8044619 * ft_to_m, 4.3471129 * ft_to_m])
interp_Z_off   = interp1d(x_stations_fus, z_offsets_fus, kind="linear", fill_value="extrapolate")


# =============================================================================
# 3. EXTRAÇÃO DE CARGAS E MOMENTOS DE TRANSPORTE DAS TIRAS DO AVL
# =============================================================================
MAPA_SURFACES = {
    1: ("Asa (Dir)", "Asa"),
    2: ("Asa (Esq)", "Asa"),
    3: ("Empenagem Vertical (CA)", "EV"),
    4: ("Empenagem Horizontal (Dir)", "EH"),
    5: ("Empenagem Horizontal (Esq)", "EH"),
}


def _distribuir_forca_tiras(forca_total: float, pesos: np.ndarray) -> np.ndarray:
    soma = float(pesos.sum())
    if abs(soma) > 1e-9:
        return forca_total * (pesos / soma)
    n = len(pesos)
    return np.full(n, forca_total / max(n, 1))


def ler_superficies_avl(caminho_txt: Path, q_inf: float):
    texto = caminho_txt.read_text(encoding="utf-8")
    m_ref = re.search(
        r"Sref\s*=\s*([-\d.]+)\s+Cref\s*=\s*([-\d.]+)\s+Bref\s*=\s*([-\d.]+)",
        texto,
    )
    Sref = float(m_ref.group(1)) if m_ref else 35.050

    blocos_surf = re.split(r"(?=\s*Surface #\s*\d+)", texto)
    cargas_surf = {}

    for bloco in blocos_surf:
        m_surf = re.search(r"Surface #\s*(\d+)\s+([^\n]+)", bloco)
        if not m_surf:
            continue

        surf_id = int(m_surf.group(1))
        if surf_id not in MAPA_SURFACES:
            continue
        comp_nome, reg_chave = MAPA_SURFACES[surf_id]
        reg = REGIOES_CARGA[reg_chave]
        x_c = 0.5 * (reg["x_ini"] + reg["x_fim"])
        z_eixo = float(interp_Z_off(x_c))

        def buscar_coef(nome_c):
            m = re.search(rf"{nome_c}\s*=\s*([-+]?\d*\.?\d+)", bloco)
            return float(m.group(1)) if m else 0.0

        CLsurf = buscar_coef("CLsurf")
        CYsurf = buscar_coef("CYsurf")
        CDsurf = buscar_coef("CDsurf")

        Fx = q_inf * Sref * CDsurf
        Fy = q_inf * Sref * CYsurf
        Fz = q_inf * Sref * CLsurf

        linhas_bloco = bloco.splitlines()
        idx_cab = next(
            (i for i, ln in enumerate(linhas_bloco) if "Xle" in ln and "Chord" in ln),
            None,
        )

        Mt_transp, My_transp, Mz_transp = 0.0, 0.0, 0.0
        if idx_cab is not None:
            linhas_dados = [linhas_bloco[idx_cab]]
            for ln in linhas_bloco[idx_cab + 1 :]:
                s = ln.strip()
                if not s or s.startswith("---"):
                    break
                linhas_dados.append(ln)
            df_strips = pd.read_csv(io.StringIO("\n".join(linhas_dados)), sep=r"\s+")
            area_s = df_strips["Area"].to_numpy(dtype=float)
            chord_s = df_strips["Chord"].to_numpy(dtype=float)
            cl_norm_s = df_strips["cl_norm"].to_numpy(dtype=float)
            cl_s = df_strips["cl"].to_numpy(dtype=float)
            cd_s = df_strips["cd"].to_numpy(dtype=float)
            cm_c4_s = df_strips["cm_c/4"].to_numpy(dtype=float)

            x_i = df_strips["Xle"].to_numpy(dtype=float) + 0.25 * chord_s
            y_i = df_strips["Yle"].to_numpy(dtype=float)
            z_i = df_strips["Zle"].to_numpy(dtype=float)

            Mc4_int = float((q_inf * area_s * (chord_s ** 2) * cm_c4_s).sum())

            if surf_id == 3:
                Fy_i = _distribuir_forca_tiras(Fy, -area_s * cl_norm_s)
                Fz_i = _distribuir_forca_tiras(Fz, area_s * cl_s)
                Fx_i = _distribuir_forca_tiras(Fx, area_s * cd_s)
                my_c4 = 0.0
                mz_c4 = Mc4_int
            else:
                Fz_i = _distribuir_forca_tiras(Fz, area_s * cl_s)
                Fy_i = _distribuir_forca_tiras(Fy, area_s * cl_norm_s)
                Fx_i = _distribuir_forca_tiras(Fx, area_s * cd_s)
                my_c4 = Mc4_int
                mz_c4 = 0.0

            Mt_transp = float((Fz_i * y_i - Fy_i * (z_i - z_eixo)).sum())
            My_transp = float(my_c4 + (Fz_i * (x_i - x_c) + Fx_i * (z_i - z_eixo)).sum())
            Mz_transp = float(mz_c4 + (Fy_i * (x_i - x_c) - Fx_i * y_i).sum())

        cargas_surf[comp_nome] = {
            "Fx": Fx,
            "Fy": Fy,
            "Fz": Fz,
            "Mt": Mt_transp,
            "My": My_transp,
            "Mz": Mz_transp,
        }

    return cargas_surf


def montar_casos_1_a_5(fator_ultimate: float = 1.5):
    caminho_lat_ref = dados_avl / "distribuicao_caso_COMB_cauda_T.txt"
    surf_lat_ref = ler_superficies_avl(caminho_lat_ref, q_inf=1.0)

    casos = {}
    for _, row in TABELA_VN_MOTOR.iterrows():
        caso_num = int(row["Caso"])
        arq_idx  = int(row["arq_idx"])
        v_ms     = float(row["V"])
        n_val    = float(row["n"])
        q_inf    = float(row["q_inf"])
        cl_val   = float(row["CL"])
        t_max    = float(row["T_max_N"])

        q_ult = q_inf * fator_ultimate
        caminho_txt = dados_avl / f"distribuicao_caso_{arq_idx}.txt"
        c_sim = ler_superficies_avl(caminho_txt, q_ult)

        fz_asa = c_sim["Asa (Esq)"]["Fz"] + c_sim["Asa (Dir)"]["Fz"]
        fx_asa = c_sim["Asa (Esq)"]["Fx"] + c_sim["Asa (Dir)"]["Fx"]
        my_asa = c_sim["Asa (Esq)"]["My"] + c_sim["Asa (Dir)"]["My"]

        fz_motor = -2.0 * W_motor_unitario_N * n_val * fator_ultimate
        fx_motor = -t_max * fator_ultimate
        z_eixo_mot = float(interp_Z_off(x_motor_m))
        my_motor = fx_motor * (z_motor_m - z_eixo_mot)

        fz_ev = c_sim["Empenagem Vertical (CA)"]["Fz"]
        fx_ev = c_sim["Empenagem Vertical (CA)"]["Fx"] + q_ult * surf_lat_ref["Empenagem Vertical (CA)"]["Fx"]
        my_ev = c_sim["Empenagem Vertical (CA)"]["My"] + q_ult * surf_lat_ref["Empenagem Vertical (CA)"]["My"]

        fz_eh = c_sim["Empenagem Horizontal (Esq)"]["Fz"] + c_sim["Empenagem Horizontal (Dir)"]["Fz"]
        fx_eh = c_sim["Empenagem Horizontal (Esq)"]["Fx"] + c_sim["Empenagem Horizontal (Dir)"]["Fx"]
        my_eh = c_sim["Empenagem Horizontal (Esq)"]["My"] + c_sim["Empenagem Horizontal (Dir)"]["My"]

        fy_asa = c_sim["Asa (Esq)"]["Fy"] + q_ult * (
            surf_lat_ref["Asa (Esq)"]["Fy"] + surf_lat_ref["Asa (Dir)"]["Fy"]
        )
        mz_asa = c_sim["Asa (Esq)"]["Mz"] + q_ult * (
            surf_lat_ref["Asa (Esq)"]["Mz"] + surf_lat_ref["Asa (Dir)"]["Mz"]
        )
        mt_asa = q_ult * (
            surf_lat_ref["Asa (Esq)"]["Mt"] + surf_lat_ref["Asa (Dir)"]["Mt"]
        )

        fy_ev = q_ult * surf_lat_ref["Empenagem Vertical (CA)"]["Fy"]
        mz_ev = q_ult * surf_lat_ref["Empenagem Vertical (CA)"]["Mz"]
        mt_ev = q_ult * surf_lat_ref["Empenagem Vertical (CA)"]["Mt"]

        fy_eh = c_sim["Empenagem Horizontal (Dir)"]["Fy"] + q_ult * (
            surf_lat_ref["Empenagem Horizontal (Esq)"]["Fy"] + surf_lat_ref["Empenagem Horizontal (Dir)"]["Fy"]
        )
        mz_eh = c_sim["Empenagem Horizontal (Dir)"]["Mz"] + q_ult * (
            surf_lat_ref["Empenagem Horizontal (Esq)"]["Mz"] + surf_lat_ref["Empenagem Horizontal (Dir)"]["Mz"]
        )
        mt_eh = q_ult * (
            surf_lat_ref["Empenagem Horizontal (Esq)"]["Mt"] + surf_lat_ref["Empenagem Horizontal (Dir)"]["Mt"]
        )

        casos[caso_num] = {
            "meta": {
                "Caso": caso_num,
                "V": v_ms,
                "n": n_val,
                "q_inf": q_inf,
                "CL": cl_val,
                "T_max_N": t_max,
            },
            "Asa":   {"Fx": fx_asa,   "Fy": fy_asa, "Fz": fz_asa,   "My": my_asa,   "Mz": mz_asa, "Mt": mt_asa},
            "Motor": {"Fx": fx_motor, "Fy": 0.0,    "Fz": fz_motor, "My": my_motor, "Mz": 0.0,    "Mt": 0.0},
            "EV":    {"Fx": fx_ev,    "Fy": fy_ev,  "Fz": fz_ev,    "My": my_ev,    "Mz": mz_ev,  "Mt": mt_ev},
            "EH":    {"Fx": fx_eh,    "Fy": fy_eh,  "Fz": fz_eh,    "My": my_eh,    "Mz": mz_eh,  "Mt": mt_eh},
        }

    return casos


# =============================================================================
# 4. CÁLCULO DE CARGAS DISTRIBUÍDAS [N/m], REAÇÕES E ESFORÇOS INTERNOS
# =============================================================================
def calcular_reacoes_viga_biapoiada(dados_caso, x_A=x_apoio_A, x_B=x_apoio_B):
    L_ab = x_B - x_A

    sum_Fx = 0.0
    sum_Fy = 0.0
    sum_Fz = 0.0
    sum_My_A = 0.0
    sum_Mz_A = 0.0
    sum_Mt = 0.0

    for comp, reg in REGIOES_CARGA.items():
        x_c = 0.5 * (reg["x_ini"] + reg["x_fim"])
        c = dados_caso[comp]

        sum_Fx += c["Fx"]
        sum_Fy += c["Fy"]
        sum_Fz += c["Fz"]
        sum_My_A += c["Fz"] * (x_c - x_A) + c["My"]
        sum_Mz_A += c["Fy"] * (x_c - x_A) + c["Mz"]
        sum_Mt += c["Mt"]

    R_Ax = -sum_Fx
    R_Bz = -sum_My_A / L_ab
    R_Az = -sum_Fz - R_Bz

    R_By = -sum_Mz_A / L_ab
    R_Ay = -sum_Fy - R_By
    T_A  = -sum_Mt

    return {
        "x_A": x_A,
        "x_B": x_B,
        "R_Ax": R_Ax,
        "R_Ay": R_Ay,
        "R_Az": R_Az,
        "R_By": R_By,
        "R_Bz": R_Bz,
        "T_A": T_A,
    }


def avaliar_distribuicao_e_esforcos(estacoes_x, dados_caso, reacoes):
    registros = []

    for x in estacoes_x:
        qz_x = 0.0
        qx_x = 0.0
        qy_x = 0.0

        Nx, Vy, Vz, My, Mz, Mt = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

        for comp, reg in REGIOES_CARGA.items():
            x_i, x_f = reg["x_ini"], reg["x_fim"]
            L_reg = x_f - x_i

            c = dados_caso[comp]
            qz_comp = c["Fz"] / L_reg
            qx_comp = c["Fx"] / L_reg
            qy_comp = c["Fy"] / L_reg

            my_dist = c["My"] / L_reg
            mz_dist = c["Mz"] / L_reg
            mt_dist = c["Mt"] / L_reg

            if x_i <= x <= x_f:
                qz_x += qz_comp
                qx_x += qx_comp
                qy_x += qy_comp

            if x < x_f:
                s_ini = max(x, x_i)
                comp_ativo = x_f - s_ini
                s_med = 0.5 * (s_ini + x_f)
                braco_x = s_med - x

                Fz_dir = qz_comp * comp_ativo
                Fx_dir = qx_comp * comp_ativo
                Fy_dir = qy_comp * comp_ativo

                Vz += Fz_dir
                Nx += Fx_dir
                Vy += Fy_dir

                My += Fz_dir * braco_x + my_dist * comp_ativo
                Mz += Fy_dir * braco_x + mz_dist * comp_ativo
                Mt += mt_dist * comp_ativo

        if reacoes["x_A"] > x:
            dx_A = reacoes["x_A"] - x
            Nx += reacoes["R_Ax"]
            Vy += reacoes["R_Ay"]
            Vz += reacoes["R_Az"]
            My += reacoes["R_Az"] * dx_A
            Mz += reacoes["R_Ay"] * dx_A
            Mt += reacoes["T_A"]

        if reacoes["x_B"] > x:
            dx_B = reacoes["x_B"] - x
            Vy += reacoes["R_By"]
            Vz += reacoes["R_Bz"]
            My += reacoes["R_Bz"] * dx_B
            Mz += reacoes["R_By"] * dx_B

        registros.append(
            {
                "x_m": float(x),
                "q_z": qz_x,
                "q_x": qx_x,
                "q_y": qy_x,
                "V_z": Vz,
                "M_y": My,
                "N_x": Nx,
                "V_y": Vy,
                "M_z": Mz,
                "M_t": Mt,
            }
        )

    return pd.DataFrame(registros)


# =============================================================================
# 5. EXECUÇÃO E GERAÇÃO DOS GRÁFICOS SEPARADOS
#    - Cargas distribuídas -> imagens/carregamentos/fuselagem/
#    - Esforços solicitantes -> imagens/esforços/fuselagem/
# =============================================================================
def main():
    carregamentos.mkdir(parents=True, exist_ok=True)
    imagens_fuselagem.mkdir(parents=True, exist_ok=True)
    esforcos_fuselagem.mkdir(parents=True, exist_ok=True)

    casos = montar_casos_1_a_5()

    pontos_transicao = []
    for reg in REGIOES_CARGA.values():
        pontos_transicao.extend(
            [
                reg["x_ini"] - 1e-4,
                reg["x_ini"] + 1e-4,
                reg["x_fim"] - 1e-4,
                reg["x_fim"] + 1e-4,
            ]
        )
    pontos_transicao.extend([0.0, L_fus_m])
    estacoes_x = np.unique(np.concatenate([np.linspace(0.0, L_fus_m, 400), pontos_transicao]))

    dict_dfs_casos = {}
    linhas_reacoes = []
    dfs_para_csv = []

    for caso_id, dados_caso in casos.items():
        meta = dados_caso["meta"]
        reacoes = calcular_reacoes_viga_biapoiada(dados_caso)
        df_caso = avaliar_distribuicao_e_esforcos(estacoes_x, dados_caso, reacoes)

        dict_dfs_casos[caso_id] = df_caso

        df_csv = df_caso.copy()
        df_csv.insert(0, "Caso", caso_id)
        dfs_para_csv.append(df_csv)

        linhas_reacoes.append(
            {
                "Caso": caso_id,
                "V [m/s]": meta["V"],
                "n": meta["n"],
                "q_inf [Pa]": meta["q_inf"],
                "CL": meta["CL"],
                "T_max [N]": meta["T_max_N"],
                "Fz_Asa [N]": round(dados_caso["Asa"]["Fz"], 2),
                "My_transp_Asa [Nm]": round(dados_caso["Asa"]["My"], 2),
                "Fz_EH [N]": round(dados_caso["EH"]["Fz"], 2),
                "Fz_Motor [N]": round(dados_caso["Motor"]["Fz"], 2),
                "Fy_EV [N]": round(dados_caso["EV"]["Fy"], 2),
                "Mz_transp_EV [Nm]": round(dados_caso["EV"]["Mz"], 2),
                "R_Ax [N]": round(reacoes["R_Ax"], 2),
                "R_Az [N]": round(reacoes["R_Az"], 2),
                "R_Bz [N]": round(reacoes["R_Bz"], 2),
                "R_Ay [N]": round(reacoes["R_Ay"], 2),
                "R_By [N]": round(reacoes["R_By"], 2),
            }
        )

    df_reacoes = pd.DataFrame(linhas_reacoes)

    # Preserva as abas de resultantes já salvas por 06.forca_resultante_fuselagem.py
    caminho_cargas_fus_xlsx = carregamentos / "carregamentos_fuselagem.xlsx"
    abas_cargas_fus = {}
    if caminho_cargas_fus_xlsx.exists():
        abas_cargas_fus.update(pd.read_excel(caminho_cargas_fus_xlsx, sheet_name=None))

    abas_esf_fus = {"Reacoes_Apoio_VN": df_reacoes}
    for caso_id, df_c in dict_dfs_casos.items():
        abas_cargas_fus[f"Caso {caso_id}"] = df_c[["x_m", "q_z", "q_x", "q_y"]].copy()
        abas_esf_fus[f"Caso {caso_id}"] = df_c[["x_m", "V_z", "M_y", "N_x", "V_y", "M_z", "M_t"]].copy()

    salvar_planilha_abas(caminho_cargas_fus_xlsx, abas_cargas_fus)
    caminho_esf_fus_xlsx = carregamentos / "esforcos_fuselagem.xlsx"
    salvar_planilha_abas(caminho_esf_fus_xlsx, abas_esf_fus)

    # A) GRÁFICOS DE CARGAS DISTRIBUÍDAS -> imagens/carregamentos/fuselagem/
    graficos_cargas = [
        ("q_z", "Carga Vertical Distribuída $q_z$ [N/m]",     "carga_vertical_fuselagem.png"),
        ("q_x", "Carga Longitudinal Distribuída $q_x$ [N/m]", "carga_longitudinal_fuselagem.png"),
        ("q_y", "Carga Lateral Distribuída $q_y$ [N/m]",      "carga_lateral_fuselagem.png"),
    ]
    for var, ylabel, fname in graficos_cargas:
        plotar_curvas_fuselagem(
            dict_dfs_casos,
            variavel=var,
            rotulo_y=ylabel,
            nome_arquivo=fname,
            pasta_destino=imagens_fuselagem,
            salvar=True,
            mostrar=False,
        )

    # B) GRÁFICOS DE ESFORÇOS INTERNOS SOLICITANTES -> imagens/esforços/fuselagem/
    graficos_esforcos = [
        ("V_z", "Esforço Cortante Vertical $V_z$ [N]",       "esforco_cortante_vertical_fuselagem.png"),
        ("M_y", "Momento Fletor Longitudinal $M_y$ [Nm]",    "momento_fletor_longitudinal_fuselagem.png"),
        ("N_x", "Esforço Normal Longitudinal $N_x$ [N]",     "esforco_normal_longitudinal_fuselagem.png"),
        ("V_y", "Esforço Cortante Lateral $V_y$ [N]",        "esforco_cortante_lateral_fuselagem.png"),
        ("M_z", "Momento Fletor Lateral $M_z$ [Nm]",         "momento_fletor_lateral_fuselagem.png"),
        ("M_t", "Momento Torsor $M_t$ [Nm]",                 "momento_torsor_fuselagem.png"),
    ]
    for var, ylabel, fname in graficos_esforcos:
        # Remove cópia antiga na pasta de carregamentos se existir
        arq_antigo_carg = imagens_fuselagem / fname
        if arq_antigo_carg.exists():
            arq_antigo_carg.unlink()

        plotar_curvas_fuselagem(
            dict_dfs_casos,
            variavel=var,
            rotulo_y=ylabel,
            nome_arquivo=fname,
            pasta_destino=esforcos_fuselagem,
            salvar=True,
            mostrar=False,
        )

    print("=" * 95)
    print("CARREGAMENTOS E ESFORÇOS DA FUSELAGEM DE 18m (ATUALIZADO COM NOVA GEOMETRIA AVL)")
    print("=" * 95)
    print(df_reacoes.to_string(index=False))
    print("-" * 95)
    print(f"[OK] Cargas salvas em:   {imagens_fuselagem}")
    print(f"[OK] Esforços salvos em: {esforcos_fuselagem}")


if __name__ == "__main__":
    main()
