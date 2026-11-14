import subprocess
from pathlib import Path
import pandas as pd
from src.config import dados_avl

# -------------------------------------------------------------------------
# 1. Definição dos Caminhos e Diretórios
# -------------------------------------------------------------------------
caminho_avl = Path(r"C:\Users\paulo\OneDrive\Documentos\AVL\avl352.exe")
caminho_geometria = Path(r"C:\Users\paulo\OneDrive\Documentos\AVL\aureon-completo.avl")
pasta_avl = caminho_geometria.parent

pasta_saida = dados_avl.resolve()
pasta_saida.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------------
# 2. Definição da Matriz de Casos com CL Alvo, Beta e Controles
# -------------------------------------------------------------------------
# Em aureon-completo.avl:
#   D1 = aileron | D2 = rudder (leme) | D3 = elevator (profundor)
beta_critico = 15.0
deflexao_leme = -25.0  # RUD 25TEL

casos_far23 = [
    {
        "id": "EV_1_rudder_kick",
        "descricao": "Rudder Kick em VD (Beta=0, D2=-25)",
        "cl_alvo": 0.17,
        "beta": 0.0,
        "d2_leme": deflexao_leme,
        "modo_d3": "PM 0.0",
    },
    {
        "id": "EV_2_overshoot",
        "descricao": "Dynamic Overshoot em VD (Beta=1.5*Beta_max, D2=-25)",
        "cl_alvo": 0.17,
        "beta": beta_critico,
        "d2_leme": deflexao_leme,
        "modo_d3": "PM 0.0",
    },
    {
        "id": "COMB_cauda_T",
        "descricao": "Carga Combinada Cauda em T em VD",
        "cl_alvo": 0.20,
        "beta": beta_critico,
        "d2_leme": deflexao_leme,
        "modo_d3": "PM 0.0",
    },
    {
        "id": "EH_2_manobra_pitch",
        "descricao": "Manobra Brusca de Profundor em VA",
        "cl_alvo": 0.45,
        "beta": 0.0,
        "d2_leme": 0.0,
        "modo_d3": "D3 -25.0",
    },
]

df_casos = pd.DataFrame(casos_far23)
df_casos.to_csv(pasta_saida / "matriz_casos_empenagem_FAR23.csv", index=False)

# -------------------------------------------------------------------------
# 3. Execução Iterativa no AVL
# -------------------------------------------------------------------------
for idx, row in df_casos.iterrows():
    caso_id = row["id"]
    cl_alvo = row["cl_alvo"]
    beta_val = row["beta"]
    leme_val = row["d2_leme"]
    modo_d3 = row["modo_d3"]

    nome_saida = f"distribuicao_caso_{caso_id}.txt"
    arquivo_temp_avl = pasta_avl / nome_saida
    arquivo_saida_final = pasta_saida / nome_saida

    if arquivo_temp_avl.exists():
        arquivo_temp_avl.unlink()
    if arquivo_saida_final.exists():
        arquivo_saida_final.unlink()

    comandos_oper = [
        f"LOAD {caminho_geometria.name}",
        "OPER",
        "A",
        f"C {cl_alvo:.6f}",
        "B",
        f"B {beta_val:.4f}",
        "D2",
        f"D2 {leme_val:.4f}",
    ]

    if "PM" in modo_d3:
        comandos_oper.extend(["D3", "PM 0.0"])
    else:
        valor_d3 = float(modo_d3.split()[-1])
        comandos_oper.extend(["D3", f"D3 {valor_d3:.4f}"])

    comandos_oper.extend(["X", "FS", f"{nome_saida}", "QUIT", "QUIT", ""])
    comandos_avl = "\n".join(comandos_oper)

    processo = subprocess.run(
        [str(caminho_avl)],
        input=comandos_avl,
        text=True,
        capture_output=True,
        cwd=str(pasta_avl),
    )

    if arquivo_temp_avl.exists():
        arquivo_temp_avl.replace(arquivo_saida_final)
        print(
            f"[OK] {caso_id:<22} | CL={cl_alvo:.3f} | Beta={beta_val:>5.1f}° | Leme(D2)={leme_val:>5.1f}°"
        )
    else:
        print(f"[ERRO] Falha na convergência do caso: {caso_id}")
        linhas_erro = processo.stdout.splitlines()[-12:]
        print("\n".join(linhas_erro))
        if processo.stderr:
            print(processo.stderr)

