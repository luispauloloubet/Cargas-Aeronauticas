import subprocess
from pathlib import Path
import pandas as pd
from src.config import dados, carregamentos

# -------------------------------------------------------------------------
# 1. Definição dos Caminhos e Diretórios
# -------------------------------------------------------------------------
caminho_avl = Path(r"C:\Users\paulo\OneDrive\Documentos\AVL\avl352.exe")
caminho_geometria = Path(r"C:\Users\paulo\OneDrive\Documentos\AVL\aureon-completo.avl")
pasta_avl = caminho_geometria.parent  # Diretório onde residem o .avl e o 0213hsnlf.dat

pasta_saida = carregamentos.resolve()
pasta_saida.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------------
# 2. Leitura dos Casos Críticos
# -------------------------------------------------------------------------
df_cls = pd.read_csv(dados / "CLs para analise.csv")

# -------------------------------------------------------------------------
# 3. Execução Iterativa no AVL
# -------------------------------------------------------------------------
for idx, row in df_cls.iterrows():
    cl_alvo = row["CL"]
    nome_saida = f"distribuicao_caso_{idx}.txt"
    arquivo_temp_avl = pasta_avl / nome_saida
    arquivo_saida_final = pasta_saida / nome_saida

    # Limpa versões anteriores residuais se existirem
    if arquivo_temp_avl.exists():
        arquivo_temp_avl.unlink()
    if arquivo_saida_final.exists():
        arquivo_saida_final.unlink()

    # ---------------------------------------------------------------------
    # Sequência de Prompts do AVL:
    # 1. LOAD <geometria> -> Lê a geometria completa da aeronave. Como o cwd
    #                        está fixado em pasta_avl, ele encontra o .dat nativamente.
    # 2. OPER             -> Entra no menu de operações aerodinâmicas de ponto de voo.
    # 3. A                -> Seleciona a variável Alpha (ângulo de ataque) para ajuste.
    # 4. C <cl_alvo>      -> Fixa a restrição de sustentação total no CL do caso (Alpha varia).
    # 5. D2               -> Seleciona a 2ª variável de controle (elevator / profundor).
    # 6. PM 0.0           -> Impõe momento de arfagem nulo (Cm = 0), acionando o profundor
    #                        para trimagem longitudinal estática da aeronave.
    # 7. X                -> Executa a convergência numérica da esteira de vórtices e derivadas.
    # 8. FS               -> Abre a gravação do relatório Strip Forces (forças seccionais).
    # 9. <nome_saida>     -> Define o nome do arquivo TXT local que receberá os dados.
    # 10. QUIT            -> Sai do menu OPER e retorna à raiz do AVL.
    # 11. QUIT            -> Encerra o executável AVL liberando o processo.
    # ---------------------------------------------------------------------
    comandos_avl = (
        f"LOAD {caminho_geometria.name}\n"
        f"OPER\n"
        f"A\n"
        f"C {cl_alvo:.6f}\n"
        f"D2\n"
        f"PM 0.0\n"
        f"X\n"
        f"FS\n"
        f"{nome_saida}\n"
        f"QUIT\n"
        f"QUIT\n"
    )

    processo = subprocess.run(
        [str(caminho_avl)],
        input=comandos_avl,
        text=True,
        capture_output=True,
        cwd=str(pasta_avl)  # Executa a partir da pasta do AVL
    )

    # Move o relatório gerado na pasta do AVL para a pasta final 'dados/carregamentos'
    if arquivo_temp_avl.exists():
        arquivo_temp_avl.replace(arquivo_saida_final)
        print(f"[OK] Caso {idx} (CL = {cl_alvo:.4f}) gerado com sucesso!")
    else:
        print(f"[ERRO] Falha no Caso {idx}:")
        linhas_erro = processo.stdout.splitlines()[-15:]
        print("\n".join(linhas_erro))
        if processo.stderr:
            print(processo.stderr)