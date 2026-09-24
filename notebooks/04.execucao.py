import pandas as pd
from pathlib import Path
from src.config import dados
from src.carregamentos import analises, carregamento_asa, carregamento_eh, carregamento_ev
from src.graficos import plotar_distribuicao_caso,plotar_envelope_carregamentos


def main():
    print("=" * 65)
    print("PROCESSAMENTO DE CARREGAMENTOS E DISTRIBUIÇÕES SECCIONAIS")
    print("=" * 65)

    # ---------------------------------------------------------------------
    # 1. Carregamentos Longitudinais Simétricos (Diagrama V-n)
    # ---------------------------------------------------------------------
    caminho_vn = dados / "pontos_criticos_diagramaVN.csv"
    if caminho_vn.exists():
        print("\n[1/3] Processando casos simétricos do Diagrama V-n...")
        df_vn = pd.read_csv(caminho_vn, index_col=0)
        tabela_analises_vn = analises(df_vn)

        # Extração de cargas para cada superfície
        cargas_asa = carregamento_asa(tabela_analises_vn, n_estacoes=25)
        cargas_eh = carregamento_eh(tabela_analises_vn, n_estacoes=16)
        cargas_ev = carregamento_ev(tabela_analises_vn, n_estacoes=16)

        print(
            f"  -> {len(cargas_asa)} casos calculados para a Asa Principal."
        )
        print(
            f"  -> {len(cargas_eh)} casos calculados para o Estabilizador Horizontal."
        )

        # Gráficos Envoltórias (V-n)
        if cargas_asa:
            plotar_envelope_carregamentos(
                cargas_asa,
                superficie="asa",
                variavel="N_prime",
                titulo_custom="Envelope de Carga Normal N' - Asa Principal (Casos V-n)",
                salvar=True,
                mostrar=False,
            )
        if cargas_eh:
            plotar_envelope_carregamentos(
                cargas_eh,
                superficie="eh",
                variavel="N_prime",
                titulo_custom="Envelope de Carga Normal N' - Estabilizador Horizontal (Casos V-n)",
                salvar=True,
                mostrar=False,
            )

    # ---------------------------------------------------------------------
    # 2. Carregamentos Laterais e Cauda em T (FAR 23: EV-1, EV-2, COMB, EH-2)
    # ---------------------------------------------------------------------
    caminho_matriz_far = (
        dados / "carregamentos" / "matriz_casos_empenagem_FAR23.csv"
    )
    if caminho_matriz_far.exists():
        print(
            "\n[2/3] Processando manobras assimétricas e cauda em T (FAR 23)..."
        )
        df_far23 = pd.read_csv(caminho_matriz_far)

        # Estima q_inf na velocidade de mergulho VD para os casos da EV
        # (Ajuste o valor de VD e rho se necessário)
        rho = 1.225
        vd_ms = 145.0  # Velocidade de mergulho [m/s]
        q_inf_vd = 0.5 * rho * (vd_ms**2)

        df_analises_far = pd.DataFrame(
            {"q_inf": [q_inf_vd] * len(df_far23)}, index=df_far23["id"].values
        )

        # Extração de cargas para EV e EH nos casos assimétricos
        cargas_ev = carregamento_ev(df_analises_far, n_estacoes=16)
        cargas_eh_far = carregamento_eh(df_analises_far, n_estacoes=16)

        print(
            f"  -> {len(cargas_ev)} casos calculados para o Estabilizador Vertical."
        )

        # Gráficos dedicados para manobras da Empenagem Vertical
        if cargas_ev:
            plotar_envelope_carregamentos(
                cargas_ev,
                superficie="ev",
                variavel="N_prime",
                titulo_custom="Distribuição de Força Lateral N' - Estabilizador Vertical (FAR 23)",
                salvar=True,
                mostrar=False,
            )

    # ---------------------------------------------------------------------
    # 3. Gráficos seccionais individuais de exemplo
    # ---------------------------------------------------------------------
    print("\n[3/3] Gerando curvas detalhadas de casos críticos...")
    if "cargas_asa" in locals() and 0 in cargas_asa:
        plotar_distribuicao_caso(
            cargas_asa[0],
            superficie="asa",
            caso_id="0",
            variavel="N_prime",
            salvar=True,
            mostrar=False,
        )

    if "cargas_ev" in locals() and "EV_2_overshoot" in cargas_ev:
        plotar_distribuicao_caso(
            cargas_ev["EV_2_overshoot"],
            superficie="ev",
            caso_id="EV_2_overshoot",
            variavel="N_prime",
            salvar=True,
            mostrar=False,
        )

    print(
        "\nProcessamento concluído com sucesso! Gráficos salvos em 'imagens/carregamentos/'."
    )


if __name__ == "__main__":
    main()