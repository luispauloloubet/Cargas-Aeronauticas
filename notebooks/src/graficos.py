import matplotlib.pyplot as plt
from src.config import (
    imagens_asa,
    imagens_eh,
    imagens_ev,
    imagens_fuselagem,
    esforcos_asa,
    esforcos_eh,
    esforcos_ev,
    esforcos_fuselagem,
)

# Dicionários de roteamento de diretórios
PASTAS_CARREGAMENTOS = {
    "asa": imagens_asa,
    "eh": imagens_eh,
    "ev": imagens_ev,
    "fuselagem": imagens_fuselagem,
}

PASTAS_ESFORCOS = {
    "asa": esforcos_asa,
    "eh": esforcos_eh,
    "ev": esforcos_ev,
    "fuselagem": esforcos_fuselagem,
}

LABELS_CARREGAMENTOS = {
    "N_prime": "Força Normal Distribuída $N'$ [N/m]",
    "T_prime": "Força Tangencial Distribuída $T'$ [N/m]",
    "L_prime": "Sustentação Distribuída $L'$ [N/m]",
    "M_prime_c4": "Momento Distribuído $M'_{c/4}$ [Nm/m]",
}

LABELS_ESFORCOS = {
    "V_N": "Esforço Cortante Normal $V_N$ [N]",
    "V_T": "Esforço Cortante Tangencial $V_T$ [N]",
    "M_F": "Momento Fletor Normal $M_F$ [Nm]",
    "M_T": "Momento Fletor Tangencial $M_T$ [Nm]",
    "M_t": "Momento Torsor $M_t$ [Nm]",
}


def configurar_estilo():
    plt.rcParams["font.sans-serif"] = "DejaVu Sans"
    plt.rcParams["axes.edgecolor"] = "#2D3748"
    plt.rcParams["axes.linewidth"] = 0.8


MAPA_LEGENDAS_CURTAS = {
    "EV_1_rudder_kick": "EV-1",
    "EV_2_overshoot": "EV-2",
    "COMB_cauda_T": "Cauda-T",
    "EH_2_manobra_pitch": "EH-2",
}


def _rotulo_legenda(caso_id) -> str:
    chave = str(caso_id).split(":")[0].strip()
    return MAPA_LEGENDAS_CURTAS.get(chave, chave)


def _obter_coluna_e_rotulo_span(df, superficie: str):
    col = "semienvergadura" if "semienvergadura" in df.columns else "altura"
    rotulo_x = (
        "Envergadura Z [m]"
        if superficie.lower() == "ev"
        else "Semi-envergadura Y [m]"
    )
    return col, rotulo_x


def plotar_distribuicao_caso(
    df,
    superficie="asa",
    caso_id="1",
    variavel="N_prime",
    salvar=True,
    mostrar=False,
):
    configurar_estilo()
    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)

    eixo_span, rotulo_x = _obter_coluna_e_rotulo_span(df, superficie)
    rotulo_y = LABELS_CARREGAMENTOS.get(variavel, f"{variavel} [N/m]")

    ax.plot(
        df[eixo_span],
        df[variavel],
        marker="o",
        markersize=3,
        linewidth=1.5,
        color="#2B6CB0",
        label=f"{caso_id}",
    )
    ax.fill_between(df[eixo_span], df[variavel], alpha=0.15, color="#2B6CB0")
    ax.axhline(0, color="black", linewidth=1.5, linestyle="-", alpha=0.5)

    ax.set_xlabel(rotulo_x, fontsize=10)
    ax.set_ylabel(rotulo_y, fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="best", frameon=True)

    plt.tight_layout()

    if salvar:
        pasta_destino = PASTAS_CARREGAMENTOS.get(
            superficie.lower(), imagens_asa.parent
        )
        pasta_destino.mkdir(parents=True, exist_ok=True)
        nome_img = f"distribuicao_{superficie.lower()}_{variavel}_caso_{caso_id}.png"
        fig.savefig(pasta_destino / nome_img, dpi=300, bbox_inches="tight")

    if mostrar:
        plt.show()
    else:
        plt.close(fig)


def plotar_envelope_carregamentos(
    dict_dfs,
    superficie="asa",
    variavel="N_prime",
    titulo_custom=None,
    salvar=True,
    mostrar=False,
    nome_arquivo_custom=None,
):
    configurar_estilo()
    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)

    primeiro_df = next(iter(dict_dfs.values()))
    eixo_span, rotulo_x = _obter_coluna_e_rotulo_span(primeiro_df, superficie)
    rotulo_y = LABELS_CARREGAMENTOS.get(variavel, f"{variavel} [N/m]")

    for caso_id, df in dict_dfs.items():
        ax.plot(
            df[eixo_span],
            df[variavel],
            marker="o",
            markersize=3,
            linewidth=1.5,
            label=_rotulo_legenda(caso_id),
        )

    ax.axhline(0, color="black", linewidth=1.5, linestyle="-", alpha=0.5)
    ax.set_xlabel(rotulo_x, fontsize=10)
    ax.set_ylabel(rotulo_y, fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="best", frameon=True, fontsize=8.5)

    plt.tight_layout()

    if salvar:
        pasta_destino = PASTAS_CARREGAMENTOS.get(
            superficie.lower(), imagens_asa.parent
        )
        pasta_destino.mkdir(parents=True, exist_ok=True)
        nome_img = (
            nome_arquivo_custom
            if nome_arquivo_custom
            else f"envelope_{superficie.lower()}_{variavel}.png"
        )
        fig.savefig(pasta_destino / nome_img, dpi=300, bbox_inches="tight")

    if mostrar:
        plt.show()
    else:
        plt.close(fig)


def plotar_assimetrico_asa(
    df_cargas,
    variavel="N_prime",
    sufixo="vc",
    salvar=True,
    mostrar=False,
):
    """
    Plota a distribuição ao longo da envergadura completa [-b/2, +b/2] para os casos
    assimétricos da asa em gráficos separados.
    """
    configurar_estilo()
    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)

    rotulo_y = LABELS_CARREGAMENTOS.get(variavel, "Carregamento [N/m]")

    ax.plot(
        df_cargas["Envergadura"],
        df_cargas[variavel],
        marker="o",
        markersize=3,
        linewidth=1.5,
    )
    ax.axhline(0, color="black", linewidth=1.5, linestyle="-", zorder=0, alpha=0.5)
    ax.axvline(0, color="black", linewidth=1.5, linestyle="-", zorder=0, alpha=0.5)
    ax.set_ylabel(rotulo_y, fontsize=10)
    ax.set_xlabel("Envergadura Y [m]", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()

    if salvar:
        imagens_asa.mkdir(parents=True, exist_ok=True)
        var_curto = "M_prime" if variavel == "M_prime_c4" else variavel
        nome_img = f"assimetricos_{sufixo.lower()}_{var_curto}.png"
        fig.savefig(imagens_asa / nome_img, dpi=300, bbox_inches="tight")

    if mostrar:
        plt.show()
    else:
        plt.close(fig)


def plotar_envelope_esforcos(
    dict_dfs_esforcos,
    superficie="asa",
    variavel="V_N",
    salvar=True,
    mostrar=False,
    nome_arquivo_custom=None,
):
    """
    Plota os esforços solicitantes (V_N, V_T, M_F, M_T, M_t) das superfícies
    aerodinâmicas (asa, eh, ev) e salva na pasta 'imagens/esforços/<superficie>/'.
    """
    configurar_estilo()
    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)

    primeiro_df = next(iter(dict_dfs_esforcos.values()))
    eixo_span, rotulo_x = _obter_coluna_e_rotulo_span(primeiro_df, superficie)
    rotulo_y = LABELS_ESFORCOS.get(variavel, variavel)

    for caso_id, df in dict_dfs_esforcos.items():
        ax.plot(
            df[eixo_span],
            df[variavel],
            marker="o",
            markersize=3,
            linewidth=1.5,
            label=_rotulo_legenda(caso_id),
        )

    ax.axhline(0, color="black", linewidth=1.5, linestyle="-", alpha=0.5)
    ax.set_xlabel(rotulo_x, fontsize=10)
    ax.set_ylabel(rotulo_y, fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="best", frameon=True, fontsize=8.5)

    plt.tight_layout()

    if salvar:
        pasta_destino = PASTAS_ESFORCOS.get(superficie.lower(), esforcos_asa)
        pasta_destino.mkdir(parents=True, exist_ok=True)
        nome_img = (
            nome_arquivo_custom
            if nome_arquivo_custom
            else f"esforco_{superficie.lower()}_{variavel}.png"
        )
        fig.savefig(pasta_destino / nome_img, dpi=300, bbox_inches="tight")

    if mostrar:
        plt.show()
    else:
        plt.close(fig)


def plotar_esforcos_assimetrico_asa(
    df_esforcos,
    variavel="V_N",
    sufixo="vc",
    salvar=True,
    mostrar=False,
):
    """
    Plota os esforços solicitantes da asa completa [-b/2, +b/2] para o caso
    assimétrico e salva em 'imagens/esforços/asa/'.
    """
    configurar_estilo()
    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)

    rotulo_y = LABELS_ESFORCOS.get(variavel, variavel)

    ax.plot(
        df_esforcos["Envergadura"],
        df_esforcos[variavel],
        marker="o",
        markersize=3,
        linewidth=1.5,
    )
    ax.axhline(0, color="black", linewidth=1.5, linestyle="-", zorder=0, alpha=0.5)
    ax.axvline(0, color="black", linewidth=1.5, linestyle="-", zorder=0, alpha=0.5)
    ax.set_ylabel(rotulo_y, fontsize=10)
    ax.set_xlabel("Envergadura Y [m]", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()

    if salvar:
        esforcos_asa.mkdir(parents=True, exist_ok=True)
        nome_img = f"esforco_asa_assimetrico_{sufixo.lower()}_{variavel}.png"
        fig.savefig(esforcos_asa / nome_img, dpi=300, bbox_inches="tight")

    if mostrar:
        plt.show()
    else:
        plt.close(fig)


def plotar_curvas_fuselagem(
    dict_dfs,
    variavel,
    rotulo_y,
    nome_arquivo,
    rotulo_x="Posição Longitudinal X [m]",
    pasta_destino=None,
    salvar=True,
    mostrar=False,
):
    """
    Plota as curvas ao longo da fuselagem (cargas distribuídas em imagens/carregamentos/fuselagem
    ou esforços internos em imagens/esforços/fuselagem) para os casos 1 a 5.
    """
    configurar_estilo()
    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)

    for caso_id, df in dict_dfs.items():
        ax.plot(
            df["x_m"],
            df[variavel],
            linewidth=1.5,
            label=f"{caso_id}",
        )

    ax.axhline(0, color="black", linewidth=1.5, linestyle="-", alpha=0.5)
    ax.set_xlabel(rotulo_x, fontsize=10)
    ax.set_ylabel(rotulo_y, fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="best", frameon=True)

    plt.tight_layout()

    if salvar:
        destino = pasta_destino if pasta_destino is not None else imagens_fuselagem
        destino.mkdir(parents=True, exist_ok=True)
        fig.savefig(destino / nome_arquivo, dpi=300, bbox_inches="tight")

    if mostrar:
        plt.show()
    else:
        plt.close(fig)
