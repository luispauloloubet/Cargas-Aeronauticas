from pathlib import Path
import subprocess
import sys

PASTA_NOTEBOOKS = Path(__file__).resolve().parent

ETAPAS_PIPELINE = [
    ("02.automacao_AERONAVE.py",         "Trimagem e Distribuições V-n no AVL (Casos 1 a 5)"),
    ("03.automacao_EMPENAGENS_FAR23.py", "Manobras de Empenagens e Cauda em T no AVL (FAR 23)"),
    ("04.automacao_ROLAMENTO_FAR23.py",  "Manobras de Rolamento Assimétrico no AVL (VA e VC)"),
    ("05.cargas_distribuidas.py",        "Cargas Distribuídas e Esforços Solicitantes (Asa, EH e EV)"),
    ("06.forca_resultante_fuselagem.py", "Forças Resultantes e Momentos de Transporte na Fuselagem"),
    ("07.analise_cargas_fuselagem.py",   "Análise de Cargas e Esforços na Viga da Fuselagem (18 m)"),
]


def main():
    print("=" * 80)
    print("EXECUÇÃO COMPLETA DO PIPELINE DE CARGAS E ESFORÇOS AERODINÂMICOS / ESTRUTURAIS")
    print("=" * 80)

    for idx, (nome_script, descricao) in enumerate(ETAPAS_PIPELINE, start=1):
        caminho_script = PASTA_NOTEBOOKS / nome_script
        print(f"\n[{idx}/{len(ETAPAS_PIPELINE)}] {descricao} ({nome_script})")
        print("-" * 80)

        resultado = subprocess.run(
            [sys.executable, str(caminho_script)],
            cwd=str(PASTA_NOTEBOOKS),
        )
        if resultado.returncode != 0:
            print(f"\n[ERRO] A etapa {nome_script} falhou com código {resultado.returncode}.")
            sys.exit(resultado.returncode)

    print("\n" + "=" * 80)
    print("[SUCESSO] Todo o pipeline (02 a 07) foi executado e atualizado!")
    print("Para abrir a análise estrutural e visualização 3D da fuselagem, execute:")
    print("  python notebooks/08.estruturas_fuselagem.py")
    print("=" * 80)


if __name__ == "__main__":
    main()

