from pathlib import Path

# Raiz do projeto (Cargas/)
raiz = Path(__file__).resolve().parent.parent.parent

# Diretórios principais de dados
dados = raiz / "dados"
dados_avl = dados / "avl"
carregamentos = dados / "carregamentos"

# Diretórios principais de imagens
imagens = raiz / "imagens"
imagens_vn = imagens / "vn"
imagens_carregamentos = imagens / "carregamentos"
imagens_esforcos = imagens / "esforços"

# Pastas dedicadas por superfície (Carregamentos Distribuídos)
imagens_asa = imagens_carregamentos / "asa"
imagens_eh = imagens_carregamentos / "eh"
imagens_ev = imagens_carregamentos / "ev"
imagens_fuselagem = imagens_carregamentos / "fuselagem"

# Pastas dedicadas por superfície (Esforços Solicitantes)
esforcos_asa = imagens_esforcos / "asa"
esforcos_eh = imagens_esforcos / "eh"
esforcos_ev = imagens_esforcos / "ev"
esforcos_fuselagem = imagens_esforcos / "fuselagem"

# Garante a criação automática dos diretórios necessários
for pasta in [
    dados_avl,
    carregamentos,
    imagens_asa,
    imagens_eh,
    imagens_ev,
    imagens_fuselagem,
    esforcos_asa,
    esforcos_eh,
    esforcos_ev,
    esforcos_fuselagem,
    imagens_vn,
]:
    pasta.mkdir(parents=True, exist_ok=True)
