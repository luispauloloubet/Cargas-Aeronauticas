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

## 📁 Estrutura Detalhada de Diretórios e Arquivos

```text
Cargas/
│
├── dados/                                    # Dados de entrada, tabelas e parâmetros de projeto
│   ├── CLs para analise.csv                  # Tabela com coeficientes de sustentação para trimagem
│   ├── parametros.yaml                       # Propriedades de massa, geometria de referência e voo
│   ├── pontos_criticos_diagramaVN.csv        # Tabela dos vértices do envelope (V, n, q_inf)
│   │
│   └── carregamentos/                        # Diretório de saídas brutas do AVL e tabelas processadas
│       ├── matriz_casos_empenagem_FAR23.csv  # Definição dos casos laterais (Beta, Deflexões D1/D2)
│       ├── distribuicao_caso_0.txt           # Saída de Strip Forces (FS) do AVL para Caso 0 (V-n)
│       ├── distribuicao_caso_1.txt           # Saída de Strip Forces (FS) do AVL para Caso 1 (V-n)
│       ├── distribuicao_caso_2.txt           # Saída de Strip Forces (FS) do AVL para Caso 2 (V-n)
│       ├── distribuicao_caso_3.txt           # Saída de Strip Forces (FS) do AVL para Caso 3 (V-n)
│       ├── distribuicao_caso_4.txt           # Saída de Strip Forces (FS) do AVL para Caso 4 (V-n)
│       ├── distribuicao_caso_COMB_cauda_T.txt# Relatório bruto FS para caso acoplado de Cauda em T
│       ├── distribuicao_caso_EH_2_manobra_pitch.txt # Relatório FS para manobra brusca de profundor
│       ├── distribuicao_caso_EV_1_rudder_kick.txt   # Relatório FS para manobra de leme puro (Beta=0)
│       ├── distribuicao_caso_EV_2_overshoot.txt     # Relatório FS para overshoot de derrapagem
│       │
│       ├── asa/                              # CSVs de carregamentos seccionais da Asa Principal
│       │   ├── carregamento asa [envergadura] caso 0.csv
│       │   ├── carregamento asa [envergadura] caso 1.csv
│       │   ├── carregamento asa [envergadura] caso 2.csv
│       │   ├── carregamento asa [envergadura] caso 3.csv
│       │   └── carregamento asa [envergadura] caso 4.csv
│       │
│       ├── eh/                               # CSVs de carregamentos do Estabilizador Horizontal
│       │   ├── carregamento EH [envergadura] caso 0.csv
│       │   ├── carregamento EH [envergadura] caso 1.csv
│       │   ├── carregamento EH [envergadura] caso 2.csv
│       │   ├── carregamento EH [envergadura] caso 3.csv
│       │   ├── carregamento EH [envergadura] caso 4.csv
│       │   ├── carregamento EH [envergadura] caso COMB_cauda_T.csv
│       │   ├── carregamento EH [envergadura] caso EH_2_manobra_pitch.csv
│       │   ├── carregamento EH [envergadura] caso EV_1_rudder_kick.csv
│       │   └── carregamento EH [envergadura] caso EV_2_overshoot.csv
│       │
│       └── ev/                               # CSVs de carregamentos do Estabilizador Vertical
│           ├── carregamento EV [altura] caso 0.csv
│           ├── carregamento EV [altura] caso 1.csv
│           ├── carregamento EV [altura] caso 2.csv
│           ├── carregamento EV [altura] caso 3.csv
│           ├── carregamento EV [altura] caso 4.csv
│           ├── carregamento EV [altura] caso COMB_cauda_T.csv
│           ├── carregamento EV [altura] caso EH_2_manobra_pitch.csv
│           ├── carregamento EV [altura] caso EV_1_rudder_kick.csv
│           └── carregamento EV [altura] caso EV_2_overshoot.csv
│
├── imagens/                                  # Diretório de armazenamento de figuras e plots técnicos
│   ├── vn/                                   # Gráficos de envoltórias operacionais da aeronave
│   │   ├── 01.diagrama_vn_manobras.png      # Curva isolada do envelope de manobra
│   │   ├── 02.diagramaVN_Rajadas.png        # Linhas de penetração de rajada vertical
│   │   ├── 03.diagramaVN_Rajadas2.png       # Comparação entre limites de rajada e manobra
│   │   └── 04.diagramaVN_final.png          # Envelope de voo combinado final com preenchimento
│   │
│   └── carregamentos/                        # Gráficos de distribuição seccional e envoltórias
│       ├── asa/
│       │   ├── distribuicao_asa_N_prime_caso_0.png # Distribuição de carga normal para o Caso 0
│       │   └── envelope_asa_N_prime.png     # Envelope com todos os casos de carga sobrepostos
│       ├── eh/
│       │   └── envelope_eh_N_prime.png      # Envelope de cargas normais na empenagem horizontal
│       └── ev/
│           ├── distribuicao_ev_N_prime_caso_EV_2_overshoot.png # Força lateral no caso dinâmico
│           └── envelope_ev_N_prime.png      # Envelope de esforço cortante lateral no mastro
│
├── notebooks/                                # Código-fonte, automações e pipelines de cálculo
│   ├── 01.diagramaVN.ipynb                   # Construção matemática do diagrama V-n
│   ├── 02.automacao_AERONAVE.py              # Script de automação AVL para casos simétricos
│   ├── 03.automacao_EMPENAGENS_FAR23.py      # Script de automação AVL para manobras da cauda em T
│   ├── 04.execucao.py                        # Script orquestrador de processamento e gráficos
│   │
│   └── src/                                  # Módulos Python reutilizáveis (biblioteca interna)
│       ├── __init__.py                       # Arquivo de inicialização de pacote Python
│       ├── config.py                         # Definição e auto-criação de diretórios via pathlib
│       ├── carregamentos.py                  # Algoritmo de parsing de Strip Forces e cálculo de N', T', L'
│       └── graficos.py                       # Funções padronizadas de plotagem com Matplotlib
│
└── relatórios/                               # Espaço reservado para documentação técnica e memoriais
