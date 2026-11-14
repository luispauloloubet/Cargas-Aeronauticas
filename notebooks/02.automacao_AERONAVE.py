from pathlib import Path
import re
import subprocess
import pandas as pd
from src.config import dados, dados_avl
from src.carregamentos import analises

# -------------------------------------------------------------------------
# 1. Definição dos Caminhos e Diretórios
# -------------------------------------------------------------------------
caminho_avl = Path(r"C:\Users\paulo\OneDrive\Documentos\AVL\avl352.exe")
caminho_geometria = Path(
    r"C:\Users\paulo\OneDrive\Documentos\AVL\aureon-completo.avl"
)
pasta_avl = caminho_geometria.parent

pasta_saida = dados_avl.resolve()
pasta_saida.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------------
# 2. Leitura dos Casos Críticos (Pontos do Diagrama V-n)
# -------------------------------------------------------------------------
caminho_vn = dados / "pontos_criticos_diagramaVN.csv"
caminho_tabela = dados / "CLs para analise.csv"
if caminho_vn.exists():
    df_vn = pd.read_csv(caminho_vn, index_col=0)
    df_casos = analises(df_vn)
else:
    df_casos = pd.read_csv(caminho_tabela)

arquivo_cmd = pasta_avl / "run_trim.run"
arquivo_st_temp = pasta_avl / "trim_temp.txt"

resultados_trim = []

# -------------------------------------------------------------------------
# 3. Execução Iterativa no AVL (Trimagem com D3 Elevator + Exportação ST e FS)
# -------------------------------------------------------------------------
for idx, row in df_casos.iterrows():
    cl_alvo = float(row["CL"])
    nome_fs = f"distribuicao_caso_{idx}.txt"
    arquivo_fs_temp = pasta_avl / nome_fs
    arquivo_fs_final = pasta_saida / nome_fs

    if arquivo_st_temp.exists():
        arquivo_st_temp.unlink()
    if arquivo_fs_temp.exists():
        arquivo_fs_temp.unlink()
    if arquivo_fs_final.exists():
        arquivo_fs_final.unlink()

    comandos_avl = (
        f"LOAD {caminho_geometria.name}\n"
        "OPER\n"
        f"A C {cl_alvo:.6f}\n"
        "D3 PM 0.0\n"
        "X\n"
        "ST\n"
        f"{arquivo_st_temp.name}\n"
        "FS\n"
        f"{nome_fs}\n"
        "QUIT\n"
        "QUIT\n"
    )

    arquivo_cmd.write_text(comandos_avl, encoding="utf-8")

    with open(arquivo_cmd, "r", encoding="utf-8") as stdin_f:
        proc = subprocess.run(
            [str(caminho_avl)],
            stdin=stdin_f,
            capture_output=True,
            text=True,
            cwd=str(pasta_avl),
        )

    if arquivo_fs_temp.exists():
        arquivo_fs_temp.replace(arquivo_fs_final)

    if arquivo_st_temp.exists():
        texto_st = arquivo_st_temp.read_text(encoding="utf-8")

        match_alpha = re.search(r"Alpha\s*=\s*([-+]?\d*\.?\d+)", texto_st)
        match_elevator = re.search(r"elevator\s*=\s*([-+]?\d*\.?\d+)", texto_st)

        if match_alpha and match_elevator:
            alpha_val = float(match_alpha.group(1))
            delta_e_val = float(match_elevator.group(1))

            dados_linha = {
                "Caso": idx,
                "CL_alvo": cl_alvo,
                "Alpha": alpha_val,
                "Delta_e": delta_e_val,
            }

            for col in df_casos.columns:
                if col != "CL":
                    dados_linha[col] = row[col]

            resultados_trim.append(dados_linha)
            print(
                f"[OK] Caso {idx + 1:02d} (CL = {cl_alvo:7.4f}) -> Alpha ="
                f" {alpha_val:6.3f}°, Delta_e = {delta_e_val:7.3f}° | {nome_fs}"
            )
        else:
            print(f"[ERRO] Falha ao extrair dados do relatório ST no Caso {idx + 1}.")

        arquivo_st_temp.unlink()
    else:
        print(f"[ERRO] Falha na convergência do AVL para o Caso {idx + 1}.")
        linhas = proc.stdout.splitlines()[-15:]
        print("\n".join(linhas))
        break

if arquivo_cmd.exists():
    arquivo_cmd.unlink()

# -------------------------------------------------------------------------
# 4. Exportação da Tabela Única Consolidada
# -------------------------------------------------------------------------
if resultados_trim:
    df_trim_final = pd.DataFrame(resultados_trim)
    caminho_saida_csv = pasta_saida / "tabela_trimagem_casos.csv"
    df_trim_final.to_csv(caminho_saida_csv, index=False)

    print("-" * 60)
    print(f"[CONCLUÍDO] Tabela salva com sucesso em:\n{caminho_saida_csv}\n")
    print(df_trim_final[["Caso", "CL_alvo", "Alpha", "Delta_e"]])

