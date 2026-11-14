import subprocess
from pathlib import Path
from src.config import dados_avl

# -------------------------------------------------------------------------
# 1. Definição de Caminhos
# -------------------------------------------------------------------------
caminho_avl = Path(r"C:\Users\paulo\OneDrive\Documentos\AVL\avl352.exe")
caminho_geometria = Path(
    r"C:\Users\paulo\OneDrive\Documentos\AVL\aureon-completo.avl"
)
pasta_avl = caminho_geometria.parent

pasta_saida = dados_avl.resolve()
pasta_saida.mkdir(parents=True, exist_ok=True)

arquivo_cmd = pasta_avl / "run_aileron_temp.run"

# -------------------------------------------------------------------------
# 2. Definição das Condições FAR § 23.349(a) em VA e VC
# -------------------------------------------------------------------------
casos_manobra = [
    {
        "nome_arquivo": "distribuicao_assimetrica_VA.txt",
        "CL": 1.020,  # CL correspondente a (2/3)*n_max em VA
        "delta_a": 15.0,  # Deflexão total de aileron em VA
    },
    {
        "nome_arquivo": "distribuicao_assimetrica_VC.txt",
        "CL": 0.350,  # CL correspondente a VC
        "delta_a": 8.0,  # Deflexão reduzida de aileron em VC
    },
]

# -------------------------------------------------------------------------
# 3. Execução no AVL e Salvamento Direto dos Arquivos TXT em dados/avl/
# -------------------------------------------------------------------------
for caso in casos_manobra:
    nome_txt = caso["nome_arquivo"]
    cl_alvo = caso["CL"]
    da = caso["delta_a"]

    arq_temp_fs = pasta_avl / nome_txt
    arq_final_fs = pasta_saida / nome_txt

    if arq_temp_fs.exists():
        arq_temp_fs.unlink()
    if arq_final_fs.exists():
        arq_final_fs.unlink()

    comandos = (
        f"LOAD {caminho_geometria.name}\n"
        "OPER\n"
        f"A C {cl_alvo:.4f}\n"
        "D3 PM 0.0\n"
        f"D1 D1 {da:.2f}\n"
        "R R 0.0\n"
        "X\n"
        "FS\n"
        f"{nome_txt}\n"
        "QUIT\n"
        "QUIT\n"
    )

    arquivo_cmd.write_text(comandos, encoding="utf-8")

    with open(arquivo_cmd, "r", encoding="utf-8") as stdin_f:
        subprocess.run(
            [str(caminho_avl)],
            stdin=stdin_f,
            capture_output=True,
            text=True,
            cwd=str(pasta_avl),
        )

    if arq_temp_fs.exists():
        arq_temp_fs.replace(arq_final_fs)
        print(f"[OK] Arquivo gerado: {arq_final_fs}")
    else:
        print(f"[ERRO] Falha ao gerar {nome_txt}.")

if arquivo_cmd.exists():
    arquivo_cmd.unlink()

