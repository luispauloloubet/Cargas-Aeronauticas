# Cargas-Aeronáuticas

# Análise Estrutural e Determinação de Carregamentos Aerodinâmicos para Aeronave com Cauda em T (FAR 23 / AVL)

Este repositório contém o arcabouço computacional completo desenvolvido em **Python** e acoplado ao solver numérico **Athena Vortex Lattice (AVL)** para o levantamento de envelopes de voo (Diagrama V-n), cálculo de equilíbrio longitudinal/lateral e determinação dos carregamentos seccionais distribuídos ($N', T', L'$) ao longo das superfícies sustentadoras de uma aeronave executiva: **Asa Principal**, **Estabilizador Horizontal (EH)** e **Estabilizador Vertical (EV)** em configuração de **Cauda em T**.

O projeto segue rigorosamente os critérios de aeronavegabilidade prescritos na norma **14 CFR Part 23 (FAR 23 - Subparte C: Flight Loads)**.

> ⚠️ **Aviso Importante (Pré-requisito Obrigatório):**  
> Para executar as rotinas de automação aerodinâmica (`02.automacao_AERONAVE.py` e `03.automacao_EMPENAGENS_FAR23.py`), **é obrigatório ter o executável do AVL (Athena Vortex Lattice) instalado/salvo no seu computador**. Os scripts Python acionam o executável em segundo plano via `subprocess`. O caminho para o arquivo binário do AVL (ex.: `avl352.exe`) e para a geometria da aeronave (`.avl`) deve ser apontado no cabeçalho desses scripts antes da execução.

---

## 🎯 Objetivos do Projeto

1. **Determinação do Envelope de Voo Regulamentar (FAR § 23.333 a § 23.341):**
   * Determinar as velocidades operacionais características ($V_S, V_A, V_C, V_D$) a partir de parâmetros de projeto inerciais, geométricos e aerodinâmicos.
   * Modelar os limites estruturais do diagrama V-n de manobra ($n_{\max} = +3{,}8$ e $n_{\min} = -1{,}52$).
   * Calcular a resposta estrutural a rajadas verticais discretas de $50\text{ ft/s}$ em $V_C$ e $25\text{ ft/s}$ em $V_D$, incluindo o fator de atenuação de rajada ($K_g$).

2. **Simulação Aerodinâmica Acoplada (Método de Vórtices - VLM):**
   * Utilizar um modelo tridimensional completo da aeronave (`aureon-completo.avl`) para capturar efeitos de interação aeroelástica/aerodinâmica que análises isoladas não representam, tais como o efeito de placa de extremidade (*end-plate effect*) no topo do leme e a deflexão de esteira da asa sobre as empenagens.
   * Automatizar a execução em lote do AVL via chamadas de sistema em Python (`subprocess`), eliminando a necessidade de interação manual via terminal.

3. **Certificação de Cargas em Cauda em T (FAR § 23.421 a § 23.445):**
   * Simular trimagem longitudinal estática ($C_m = 0$) em todos os vértices críticos do diagrama V-n para as posições extremas de Centro de Gravidade.
   * Implementar manobras bruscas de profundor na velocidade de manobra ($V_A$) com batente de cálculo.
   * Simular casos de deflexão instantânea de leme (*Rudder Kick*) à velocidade de mergulho ($V_D$).
   * Avaliar derrapagens laterais dinâmicas com efeito de sobre-sinal dinâmico (*Dynamic Overshoot*, onde $\beta_{\text{crítico}} = 1{,}5 \cdot \beta_{\max}$), responsável pelos picos de flexão e momento fletor na raiz da empenagem vertical e momento torsor concentrado no topo da cauda.

4. **Extração de Carregamentos e Geração de Envoltórias Estruturais:**
   * Extrair os dados discretizados dos relatórios *Strip Forces* (`FS`) do AVL.
   * Converter os coeficientes locais e cordas em esforços lineares físicos por metro de envergadura/altura: força normal ($N'$), tangencial ($T'$) e sustentação ($L'$), expressos em $[\text{N/m}]$.
   * Identificar visual e numericamente as curvas envoltórias que servirão como condições de contorno de entrada para o dimensionamento preliminar de longarinas, nervuras, revestimentos e fixações.

---

## 📐 Fundamentação Teórica e Regulamentar (FAR 23)

### 1. Envelope de Voo V-n (Manobras e Rajadas)
* **Manobras Simétricas (§ 23.337):** Fator de carga positivo de cálculo fixado em $n = 3{,}8$ e limite negativo dado por $n = -0{,}4 \cdot n_{\max} = -1{,}52$.
* **Rajadas Atmosféricas Verticais (§ 23.341):** Variação do fator de carga $\Delta n$ dada por:
  $$\Delta n = \frac{\frac{1}{2} \rho_0 V_{\text{EAS}} \cdot a \cdot K_g \cdot U_{de}}{W/S}$$
  onde $U_{de}$ é a velocidade da rajada equivalente, $a$ é a derivada da sustentação em relação ao ângulo de ataque ($C_{L_\alpha}$), e $K_g$ é o fator de alívio por inércia da aeronave:
  $$K_g = \frac{0{,}88 \mu}{5{,}3 + \mu}, \qquad \mu = \frac{2 (W/S)}{\rho c \cdot g \cdot a}$$

### 2. Estabilizador Horizontal (EH)
* **§ 23.421 (Balancing Loads):** O profundor é acionado para garantir o equilíbrio estático de momentos de arfagem em torno do CG ($C_m = 0$) em todos os pontos do diagrama V-n. O CG dianteiro produz a maior força sustentadora negativa requerida na cauda.
* **§ 23.423 (Maneuvering Loads):** Movimento brusco do profundor até os batentes de projeto na velocidade de manobra ($V_A$), induzindo acelerações angulares de arfagem ($\dot{q}$) antes da resposta de atitude da aeronave.
* **§ 23.427 (Unsymmetrical Loads):** Considera a assimetria transversal de cargas de $100\%$ em uma semi-envergadura e $80\%$ na oposta.

### 3. Estabilizador Vertical (EV) e Cauda em T
* **§ 23.441(a)(1) (Rudder Kick):** Deflexão total do leme de direção à velocidade $V_D$ ou $V_A$ partindo de voo nivelado ($\beta = 0^\circ$). Gera o pico de esforço cortante na raiz do mastro vertical.
* **§ 23.441(a)(2) (Dynamic Overshoot):** Com o leme defletido, a aeronave oscila em torno do eixo $Z$ (guinada) e atinge um ângulo de derrapagem transitório superior ao ângulo de equilíbrio estático:
  $$\beta_{\text{crítico}} = 1{,}5 \cdot \beta_{\max}$$
  Essa condição maximiza o momento fletor na raiz da empenagem vertical.
* **§ 23.445 (Acoplamento de Cauda em T):** Quando a aeronave derrapa sob ângulo $\beta$, o escoamento cruzado no topo do estabilizador vertical gera uma sustentação diferencial entre as semi-asas do estabilizador horizontal. Esse momento fletor transversal no EH atua diretamente como um **momento torsor concentrado no topo do EV**.

---

## 📂 Estrutura do Repositório

```text
Cargas/
├── .vscode/                               # Configurações do VS Code
│   └── settings.json
├── dados/                                 # Entradas numéricas e planilhas de cálculo
│   ├── avl/                               # Distribuições aerodinâmicas e matrizes de trimagem (AVL)
│   │   ├── distribuicao_caso_0.txt        # Casos de manobra simétrica/rajada
│   │   ├── distribuicao_caso_1.txt
│   │   ├── distribuicao_caso_2.txt
│   │   ├── distribuicao_caso_3.txt
│   │   ├── distribuicao_caso_4.txt
│   │   ├── distribuicao_caso_va_as.txt    # Manobras assimétricas
│   │   ├── distribuicao_caso_vc_as.txt
│   │   ├── tabela_trimagem_casos.csv      # Condições de trimagem e ângulos de equilíbrio
│   │   └── matriz_casos_empenagem_FAR23.csv
│   ├── carregamentos/                     # Rotinas e planilhas de carregamento distribuído
│   │   ├── casos_carga_fuselagem.py       # Script de integração e balanceamento da fuselagem
│   │   └── *.xlsx                         # Planilhas de dados por estação
│   ├── CLs para analise.csv               # Coeficientes de sustentação por caso
│   ├── parametros.yaml                    # Parâmetros geométricos, pesos e inércias
│   └── pontos_criticos_diagramaVN.csv     # Pontos operacionais e fatores de carga (n)
└── imagens/                               # Saídas gráficas geradas pelas rotinas
    ├── carregamentos/                     # Distribuições de sustentação e forças por unidade de comprimento
    │   ├── asa/                           # Curvas spanwise e envelopes da asa
    │   ├── eh/                            # Cargas e envoltórias da EH
    │   ├── ev/                            # Cargas e envoltórias da EV
    │   └── fuselagem/                     # Distribuições ao longo do comprimento da fuselagem
    └── esforcos/                          # Diagramas de esforços solicitantes internos
        ├── asa/                           # V, M e T ao longo da asa
        └── eh/                            # V, M e T na empenagem horizontal
└── relatórios/                               # Espaço reservado para documentação técnica e memoriais
