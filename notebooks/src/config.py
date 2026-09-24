from pathlib import Path

# Raiz do projeto (Cargas/)
raiz = Path(__file__).resolve().parent.parent.parent

# Diretórios principais
dados = raiz / "dados"
carregamentos = dados / "carregamentos"
imagens = raiz / "imagens"

# Subpastas de imagens
imagens_vn = imagens / "vn"
imagens_carregamentos = imagens / "carregamentos"

# Pastas dedicadas por superfície
imagens_asa = imagens_carregamentos / "asa"
imagens_eh = imagens_carregamentos / "eh"
imagens_ev = imagens_carregamentos / "ev"

# Garante a criação automática dos diretórios
for pasta in [imagens_asa, imagens_eh, imagens_ev, imagens_vn]:
    pasta.mkdir(parents=True, exist_ok=True)