import matplotlib.pyplot as plt
from src.config import imagens_asa, imagens_eh, imagens_ev

# Dicionário de roteamento de diretórios
PASTAS_SUPERFICIES = {
    "asa": imagens_asa,
    "eh": imagens_eh,
    "ev": imagens_ev,
}


def configurar_estilo():
    plt.rcParams["font.sans-serif"] = "DejaVu Sans"
    plt.rcParams["axes.edgecolor"] = "#2D3748"
    plt.rcParams["axes.linewidth"] = 0.8


def plotar_distribuicao_caso(
    df,
    superficie="asa",
    caso_id="0",
    variavel="N_prime",
    salvar=True,
    mostrar=True,
):
    configurar_estilo()
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)

    eixo_span = "altura" if superficie.lower() == "ev" else "semienvergadura"
    rotulo_x = (
        "Altura Z [m]"
        if superficie.lower() == "ev"
        else "Semi-envergadura Y [m]"
    )

    labels_var = {
        "N_prime": "Força Normal Distribuída $N'$ [N/m]",
        "T_prime": "Força Tangencial Distribuída $T'$ [N/m]",
        "L_prime": "Sustentação Distribuída $L'$ [N/m]",
    }
    rotulo_y = labels_var.get(variavel, f"{variavel} [N/m]")

    ax.plot(
        df[eixo_span],
        df[variavel],
        marker="o",
        markersize=4,
        linewidth=1.8,
        color="#2B6CB0",
        label=f"Caso {caso_id}",
    )
    ax.fill_between(df[eixo_span], df[variavel], alpha=0.15, color="#2B6CB0")

    ax.set_title(
        f"Distribuição de {variavel} - {superficie.upper()} (Caso {caso_id})",
        fontsize=12,
        fontweight="bold",
        pad=10,
    )
    ax.set_xlabel(rotulo_x, fontsize=10)
    ax.set_ylabel(rotulo_y, fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(frameon=True)

    plt.tight_layout()

    if salvar:
        pasta_destino = PASTAS_SUPERFICIES.get(
            superficie.lower(), imagens_asa.parent
        )
        nome_img = f"distribuicao_{superficie.lower()}_{variavel}_caso_{caso_id}.png"
        fig.savefig(pasta_destino / nome_img, dpi=300)

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
    mostrar=True,
):
    configurar_estilo()
    fig, ax = plt.subplots(figsize=(9, 5), dpi=150)

    eixo_span = "altura" if superficie.lower() == "ev" else "semienvergadura"
    rotulo_x = (
        "Altura Z [m]"
        if superficie.lower() == "ev"
        else "Semi-envergadura Y [m]"
    )

    labels_var = {
        "N_prime": "Força Normal Distribuída $N'$ [N/m]",
        "T_prime": "Força Tangencial Distribuída $T'$ [N/m]",
        "L_prime": "Sustentação Distribuída $L'$ [N/m]",
    }
    rotulo_y = labels_var.get(variavel, f"{variavel} [N/m]")

    for caso_id, df in dict_dfs.items():
        ax.plot(
            df[eixo_span],
            df[variavel],
            marker="s",
            markersize=3,
            linewidth=1.5,
            label=f"Caso {caso_id}",
        )

    titulo = (
        titulo_custom
        if titulo_custom
        else f"Envelope de {variavel} - {superficie.upper()}"
    )
    ax.set_title(titulo, fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel(rotulo_x, fontsize=10)
    ax.set_ylabel(rotulo_y, fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(bbox_to_anchor=(1.04, 1), loc="upper left", frameon=True)

    plt.tight_layout()

    if salvar:
        pasta_destino = PASTAS_SUPERFICIES.get(
            superficie.lower(), imagens_asa.parent
        )
        nome_img = f"envelope_{superficie.lower()}_{variavel}.png"
        fig.savefig(pasta_destino / nome_img, dpi=300, bbox_inches="tight")

    if mostrar:
        plt.show()
    else:
        plt.close(fig)