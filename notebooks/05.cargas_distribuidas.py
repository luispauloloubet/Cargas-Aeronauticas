import pandas as pd
import yaml
from src.config import dados, dados_avl, carregamentos
from src.carregamentos import (
    analises,
    carregamento_asa,
    carregamento_assimetrico_asa,
    carregamento_eh,
    carregamento_ev,
    calcular_esforcos_viga_semienvergadura,
    salvar_planilha_abas,
)
from src.graficos import (
    plotar_envelope_carregamentos,
    plotar_assimetrico_asa,
    plotar_envelope_esforcos,
    plotar_esforcos_assimetrico_asa,
)

VARIAVEIS_CARGA = ["N_prime", "T_prime", "L_prime", "M_prime_c4"]
VARIAVEIS_ESFORCO = ["V_N", "V_T", "M_F", "M_T", "M_t"]


def main():
    print("=" * 70)
    print("PROCESSAMENTO AUTOMATIZADO DE CARREGAMENTOS E ESFORÇOS SOLICITANTES")
    print("=" * 70)

    with open(dados / "parametros.yaml", "r", encoding="utf-8") as f:
        param = yaml.safe_load(f)
    rho = float(param["atmosfera"]["rho"])
    vc_ms = float(param["velocidades"]["V_c"])
    vd_ms = float(param["velocidades"]["V_d"])
    q_inf_vc = 0.5 * rho * (vc_ms ** 2)
    q_inf_vd = 0.5 * rho * (vd_ms ** 2)

    # Dicionários de abas para as planilhas consolidadas (.xlsx)
    abas_cargas = {"asa": {}, "eh": {}, "ev": {}}
    abas_esforcos = {"asa": {}, "eh": {}, "ev": {}}

    # ---------------------------------------------------------------------
    # 1. Carregamentos e Esforços Simétricos (Diagrama V-n: Casos 1 a 5)
    # ---------------------------------------------------------------------
    caminho_vn = dados / "pontos_criticos_diagramaVN.csv"
    q_inf_va = q_inf_vc
    if caminho_vn.exists():
        print("\n[1/3] Processando Casos 1 a 5 do Diagrama V-n (Asa, EH e EV)...")
        df_vn = pd.read_csv(caminho_vn, index_col=0)
        tabela_analises_vn = analises(df_vn)
        q_inf_va = float(tabela_analises_vn.loc[0, "q_inf"])

        cargas_asa = carregamento_asa(tabela_analises_vn, n_estacoes=25)
        cargas_eh = carregamento_eh(tabela_analises_vn, n_estacoes=16)
        cargas_ev = carregamento_ev(tabela_analises_vn, n_estacoes=16)

        print(f"  -> Asa Principal: {len(cargas_asa)} casos (Casos {list(cargas_asa.keys())})")
        print(f"  -> Estabilizador Horizontal (EH): {len(cargas_eh)} casos")
        print(f"  -> Estabilizador Vertical (EV): {len(cargas_ev)} casos")

        for superficie, dict_cargas in [("asa", cargas_asa), ("eh", cargas_eh), ("ev", cargas_ev)]:
            if not dict_cargas:
                continue
            for var in VARIAVEIS_CARGA:
                plotar_envelope_carregamentos(
                    dict_cargas,
                    superficie=superficie,
                    variavel=var,
                    salvar=True,
                    mostrar=False,
                )

            dict_esforcos = {
                cid: calcular_esforcos_viga_semienvergadura(df_c)
                for cid, df_c in dict_cargas.items()
            }
            for var_esf in VARIAVEIS_ESFORCO:
                plotar_envelope_esforcos(
                    dict_esforcos,
                    superficie=superficie,
                    variavel=var_esf,
                    salvar=True,
                    mostrar=False,
                )

            for cid, df_c in dict_cargas.items():
                abas_cargas[superficie][f"Caso {cid}"] = df_c
                abas_esforcos[superficie][f"Caso {cid}"] = dict_esforcos[cid]

    # ---------------------------------------------------------------------
    # 2. Caso Assimétrico da Asa (Gráficos Separados - Sem condições FAR23 da EM)
    # ---------------------------------------------------------------------
    print("\n[2/3] Processando Caso Assimétrico da Asa (VC e VA) em gráficos separados...")
    for nome_txt, q_caso, sufixo in [
        ("distribuicao_assimetrica_VC.txt", q_inf_vc, "VC"),
        ("distribuicao_assimetrica_VA.txt", q_inf_va, "VA"),
    ]:
        df_cargas_assim, df_esf_assim = carregamento_assimetrico_asa(
            nome_txt=nome_txt, q_inf=q_caso
        )
        if df_cargas_assim is not None:
            abas_cargas["asa"][f"Assimetrico_{sufixo}"] = df_cargas_assim
            abas_esforcos["asa"][f"Assimetrico_{sufixo}"] = df_esf_assim

            for var in VARIAVEIS_CARGA:
                plotar_assimetrico_asa(
                    df_cargas_assim,
                    variavel=var,
                    sufixo=sufixo.lower(),
                    salvar=True,
                    mostrar=False,
                )
            for var_esf in VARIAVEIS_ESFORCO:
                plotar_esforcos_assimetrico_asa(
                    df_esf_assim,
                    variavel=var_esf,
                    sufixo=sufixo.lower(),
                    salvar=True,
                    mostrar=False,
                )

    # ---------------------------------------------------------------------
    # 3. Carregamentos e Esforços das Empenagens (FAR 23: EV-1, EV-2, COMB, EH-2)
    # ---------------------------------------------------------------------
    caminho_matriz_far = dados_avl / "matriz_casos_empenagem_FAR23.csv"
    if caminho_matriz_far.exists():
        print("\n[3/3] Processando manobras das Empenagens e Cauda em T (FAR 23)...")
        df_far23 = pd.read_csv(caminho_matriz_far)

        q_list = [
            q_inf_va if ("VA" in str(r["descricao"]) or "EH_2" in str(r["id"])) else q_inf_vd
            for _, r in df_far23.iterrows()
        ]
        df_analises_far = pd.DataFrame({"q_inf": q_list}, index=df_far23["id"].values)

        cargas_ev_far = carregamento_ev(df_analises_far, n_estacoes=16)
        cargas_eh_far = carregamento_eh(df_analises_far, n_estacoes=16)

        for superficie, dict_cargas_far in [("ev", cargas_ev_far), ("eh", cargas_eh_far)]:
            if not dict_cargas_far:
                continue
            for var in VARIAVEIS_CARGA:
                var_nome = "M_prime" if var == "M_prime_c4" else var
                plotar_envelope_carregamentos(
                    dict_cargas_far,
                    superficie=superficie,
                    variavel=var,
                    salvar=True,
                    mostrar=False,
                    nome_arquivo_custom=f"envelope_{superficie}_{var_nome}_FAR23.png",
                )

            dict_esf_far = {
                cid: calcular_esforcos_viga_semienvergadura(df_c)
                for cid, df_c in dict_cargas_far.items()
            }
            for var_esf in VARIAVEIS_ESFORCO:
                plotar_envelope_esforcos(
                    dict_esf_far,
                    superficie=superficie,
                    variavel=var_esf,
                    salvar=True,
                    mostrar=False,
                    nome_arquivo_custom=f"esforco_{superficie}_{var_esf}_FAR23.png",
                )

            for cid, df_c in dict_cargas_far.items():
                abas_cargas[superficie][str(cid)] = df_c
                abas_esforcos[superficie][str(cid)] = dict_esf_far[cid]

    # ---------------------------------------------------------------------
    # 4. Exportação das Planilhas Consolidadas por Superfície (1 aba por caso)
    # ---------------------------------------------------------------------
    for superficie in ["asa", "eh", "ev"]:
        if abas_cargas[superficie]:
            caminho_cargas_xlsx = carregamentos / f"carregamentos_{superficie}.xlsx"
            salvar_planilha_abas(caminho_cargas_xlsx, abas_cargas[superficie])
            print(f"  [XLSX] {caminho_cargas_xlsx.name} ({len(abas_cargas[superficie])} abas)")

        if abas_esforcos[superficie]:
            caminho_esf_xlsx = carregamentos / f"esforcos_{superficie}.xlsx"
            salvar_planilha_abas(caminho_esf_xlsx, abas_esforcos[superficie])
            print(f"  [XLSX] {caminho_esf_xlsx.name} ({len(abas_esforcos[superficie])} abas)")

    print("\n[OK] Planilhas salvas em 'dados/carregamentos/' e gráficos em 'imagens/'!")


if __name__ == "__main__":
    main()
