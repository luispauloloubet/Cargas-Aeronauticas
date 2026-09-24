import subprocess
from pathlib import Path
import pandas as pd
from src.config import dados, carregamentos

# -------------------------------------------------------------------------
# 1. Definição dos Caminhos e Diretórios
# -------------------------------------------------------------------------
caminho_avl = Path(r"C:\Users\paulo\OneDrive\Documentos\AVL\avl352.exe")
caminho_geometria = Path(r"C:\Users\paulo\OneDrive\Documentos\AVL\aureon-completo.avl")
pasta_avl = caminho_geometria.parent

pasta_saida = carregamentos.resolve()
pasta_saida.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------------
# 2. Definição da Matriz de Casos com CL Alvo, Beta e Controles
# -------------------------------------------------------------------------
# D1 = rudder (leme) | D2 = elevator (profundor)
# beta_critico = 1.5 * beta_max (exemplo com beta_max ~ 10 deg -> 15 deg)
beta_critico = 15.0
deflexao_leme = -25.0  # RUD 25TEL

# Configure abaixo os CLs alvo de projeto para cada condição:
casos_far23 = [
    {
        "id": "EV_1_rudder_kick",
        "descricao": "Rudder Kick em VD (Beta=0, D1=-25)",
        "cl_alvo": 0.15,  # CL de voo nivelado em VD
        "beta": 0.0,
        "d1_leme": deflexao_leme,
        "modo_d2": "PM 0.0",  # Profundor trimando Cm=0
    },
    {
        "id": "EV_2_overshoot",
        "descricao": "Dynamic Overshoot em VD (Beta=1.5*Beta_max, D1=-25)",
        "cl_alvo": 0.15,  # CL de voo nivelado em VD
        "beta": beta_critico,
        "d1_leme": deflexao_leme,
        "modo_d2": "PM 0.0",  # Profundor trimando Cm=0
    },
    {
        "id": "COMB_cauda_T",
        "descricao": "Carga Combinada Cauda em T em VD",
        "cl_alvo": 0.20,  # CL alvo da condição combinada
        "beta": beta_critico,
        "d1_leme": deflexao_leme,
        "modo_d2": "PM 0.0",  # Profundor trimando Cm=0
    },
    {
        "id": "EH_2_manobra_pitch",
        "descricao": "Manobra Brusca de Profundor em VA",
        "cl_alvo": 0.45,  # CL alvo na velocidade de manobra VA
        "beta": 0.0,
        "d1_leme": 0.0,
        "modo_d2": "D2 -25.0",  # Profundor no batente cabrador de cálculo
    },
]

df_casos = pd.DataFrame(casos_far23)
# Salva um registro dos casos executados para rastreabilidade
df_casos.to_csv(pasta_saida / "matriz_casos_empenagem_FAR23.csv", index=False)

# -------------------------------------------------------------------------
# 3. Execução Iterativa no AVL
# -------------------------------------------------------------------------
for idx, row in df_casos.iterrows():
    caso_id = row["id"]
    cl_alvo = row["cl_alvo"]
    beta_val = row["beta"]
    leme_val = row["d1_leme"]
    modo_d2 = row["modo_d2"]

    nome_saida = f"distribuicao_caso_{caso_id}.txt"
    arquivo_temp_avl = pasta_avl / nome_saida
    arquivo_saida_final = pasta_saida / nome_saida

    if arquivo_temp_avl.exists():
        arquivo_temp_avl.unlink()
    if arquivo_saida_final.exists():
        arquivo_saida_final.unlink()

    # Montagem dinâmica dos comandos do OPER:
    # 1. Fixa a sustentação total no CL desejado (A -> C <cl_alvo>)
    # 2. Fixa o ângulo de derrapagem (B -> B <beta>)
    # 3. Fixa a deflexão de leme D1 (D1 -> D1 <leme>)
    # 4. Configura o profundor D2 (trimando via PM 0.0 ou defletido fixo)
    comandos_oper = [
        f"LOAD {caminho_geometria.name}",
        "OPER",
        "A",
        f"C {cl_alvo:.6f}",
        "B",
        f"B {beta_val:.4f}",
        "D1",
        f"D1 {leme_val:.4f}",
    ]

    if "PM" in modo_d2:
        comandos_oper.extend(["D2", "PM 0.0"])
    else:
        # Ex: "D2 -25.0"
        valor_d2 = float(modo_d2.split()[-1])
        comandos_oper.extend(["D2", f"D2 {valor_d2:.4f}"])

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
            f"[OK] {caso_id:<22} | CL={cl_alvo:.3f} | Beta={beta_val:>5.1f}° | Leme={leme_val:>5.1f}°"
        )
    else:
        print(f"[ERRO] Falha na convergência do caso: {caso_id}")
        linhas_erro = processo.stdout.splitlines()[-12:]
        print("\n".join(linhas_erro))
        if processo.stderr:
            print(processo.stderr)