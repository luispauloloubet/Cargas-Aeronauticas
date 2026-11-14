import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from mpl_toolkits.mplot3d import Axes3D

# Adiciona a pasta de carregamentos ao path para importar CASOS_CARGA gerado por 06.forca_resultante_fuselagem.py
_PASTA_CARREGAMENTOS = Path(__file__).resolve().parent.parent / "dados" / "carregamentos"
if str(_PASTA_CARREGAMENTOS) not in sys.path:
    sys.path.insert(0, str(_PASTA_CARREGAMENTOS))

from casos_carga_fuselagem import CASOS_CARGA

# =============================================================================
# 1. INPUTS GEOMÉTRICOS E DE POSICIONAMENTO
# =============================================================================
ft_to_m = 0.3048

# Leituras diretas e conversões
lenght_m           = 59.17751644 * ft_to_m
b_asa_m            = 18.94 
cr_asa_m           = 2.88  
ct_asa_m           = 0.82  
cr_eh_m            = 1.69  
ct_eh_m            = 0.69  
b_eh_m             = 7.05  
cr_ev_m            = 6.1975 * ft_to_m
ct_ev_m            = 4.869 * ft_to_m
b_ev_m             = 7.844 * ft_to_m

Dpt_m              = 1.8   
Dpax_m             = 2.0   
Lcabpax_m          = 26.2467 * ft_to_m
Lcabpt_m           = 8.2021 * ft_to_m
Lradome_m          = 3.0 * ft_to_m

D_motor_m          = 0.74
Bitola_m           = 25.0 * b_asa_m / 100.0
z_TP_m             = 5.0 * ft_to_m
Entre_eixos_m      = 26.0 * ft_to_m
Lenght_fus_motor_m = 17.614 * ft_to_m
R_fus_motor_m      = Lenght_fus_motor_m / (2.0 * np.pi)
y_asa_motor_m      = (D_motor_m / 2.0) + R_fus_motor_m

# -----------------------------------------------------------------------------
# CÁLCULO DE POSIÇÕES ABSOLUTAS
# -----------------------------------------------------------------------------
# Posição base da Asa
x_asa_m = lenght_m - (22.37100657 * ft_to_m) - (cr_ev_m * 3.0 / 4.0)
z_asa_m = -1.5 * ft_to_m

# Componentes (Baseados no braço X e Z em relação à asa)
x_eh_m    = x_asa_m + (23.67100657 * ft_to_m)
z_eh_m    = 12.7413735 * ft_to_m

x_ev_m    = x_asa_m + (22.37100657 * ft_to_m)
#z_ev_base = 9.0073894 * ft_to_m
z_ca_ev_m = 9.0073894 * ft_to_m

x_motor_m = x_asa_m + (14.0 * ft_to_m)
z_motor_m = 3.4006543 * ft_to_m

x_nlg     = Lradome_m
x_mlg     = x_nlg + Entre_eixos_m
z_mlg     = -z_TP_m

components = {
    'NLG (Trem de Nariz)':        {'pos': (x_nlg, 0.0, -z_TP_m)},
    'MLG (Trem Principal - Esq)': {'pos': (x_mlg, -Bitola_m/2.0, z_mlg)},
    'MLG (Trem Principal - Dir)': {'pos': (x_mlg, Bitola_m/2.0, z_mlg)},
    'Asa (Esq)':                  {'pos': (x_asa_m, -b_asa_m/4.0, z_asa_m)},
    'Asa (Dir)':                  {'pos': (x_asa_m, b_asa_m/4.0, z_asa_m)},
    'Motor (Esq)':                {'pos': (x_motor_m, -y_asa_motor_m, z_motor_m)},
    'Motor (Dir)':                {'pos': (x_motor_m, y_asa_motor_m, z_motor_m)},
    'Empenagem Horizontal (Esq)': {'pos': (x_eh_m, -b_eh_m/4.0, z_eh_m)},
    'Empenagem Horizontal (Dir)': {'pos': (x_eh_m, b_eh_m/4.0, z_eh_m)},
    'Empenagem Vertical (CA)':    {'pos': (x_ev_m, 0.0, z_ca_ev_m)}
}

# -----------------------------------------------------------------------------
# PERFIL DA FUSELAGEM (Ajuste do Nariz e Upsweep da Cauda)
# -----------------------------------------------------------------------------
# 4 Estações para transição correta e suave do nariz
x0 = 0.0                                    
x1 = Lradome_m + Lcabpt_m # Nariz longo termina no fim do cockpit                   
x2 = x1 + Lcabpax_m       # Início do cone de cauda           
x3 = lenght_m                                 

d0 = 0.1                                    
d1 = Dpax_m                                   
d2 = Dpax_m                                   
d3 = 0.45                                   

# Alinhamento vertical das seçoes da fuselagem
z_center_0 = 0                                # Ponta do nariz sutilmente abaixo
z_center_1 = 1.8044619*ft_to_m                                 # Centro da cabine
z_center_2 = 1.8044619*ft_to_m                                   # Centro da cabine
z_center_3 = 4.3471129*ft_to_m        # Sobe o centro do cone para manter o teto reto

fuselage_profile = {
    'x_stations': np.array([x0, x1, x2, x3]),
    'diameters':  np.array([d0, d1, d2, d3]),
    'z_offsets':  np.array([z_center_0, z_center_1, z_center_2, z_center_3])
}

# =============================================================================
# 2. INPUTS ESTRUTURAIS E MATERIAL
# =============================================================================
# Obs.: As cargas em CASOS_CARGA (casos_carga_fuselagem.py) já estão na condição
# ULTIMATE (FS = 1.5 aplicado em 06.forca_resultante_fuselagem.py).
# Portanto, FS_cargas = 1.0 para forças/momentos de CASOS_CARGA (evitando dupla
# multiplicação por 1.5), e FS_pressao = 1.5 apenas para delta_P nominal.
MATERIAL = {'E': 73e9, 'sigma_y': 345e6, 'tau_allow': 200e6, 'FS': 1.0, 'FS_pressao': 1.5}
NUM_STRINGERS = 36

# Pontos de apoio estaticamente determinados na junção asa-fuselagem (longarinas A e B)
x_apoio_A = x_asa_m - 0.25 * cr_asa_m
x_apoio_B = x_apoio_A + cr_asa_m
z_apoio   = z_asa_m

structural_profile = {
    'x_stations': np.array([x0, x_asa_m - 1.0, x_asa_m + 2.0, x3]),
    'skin_t':     np.array([0.0012, 0.0018, 0.0020, 0.0012]), 
    'h_str':      np.array([0.018,  0.026,  0.026,  0.018]), 
    'b_str':      np.array([0.014,  0.018,  0.018,  0.014]), 
    't_str':      np.array([0.0012, 0.0018, 0.0018, 0.0012]), 
    'h_frame':    np.array([0.05,   0.08,   0.08,   0.05]),
    't_frame':    np.array([0.0012, 0.0020, 0.0020, 0.0012]),
}

# =============================================================================
# 4. PIPELINE DE CÁLCULO ESTRUTURAL (VIGA BI-APOIADA NA JUNÇÃO ASA-FUSELAGEM)
# =============================================================================

interp_D = interp1d(fuselage_profile['x_stations'], fuselage_profile['diameters'], kind='linear', fill_value="extrapolate")
interp_Z_off = interp1d(fuselage_profile['x_stations'], fuselage_profile['z_offsets'], kind='linear', fill_value="extrapolate")
interp_h_str = interp1d(structural_profile['x_stations'], structural_profile['h_str'], kind='linear', fill_value="extrapolate")
interp_b_str = interp1d(structural_profile['x_stations'], structural_profile['b_str'], kind='linear', fill_value="extrapolate")
interp_t_str = interp1d(structural_profile['x_stations'], structural_profile['t_str'], kind='linear', fill_value="extrapolate")
interp_h_frm = interp1d(structural_profile['x_stations'], structural_profile['h_frame'], kind='linear', fill_value="extrapolate")
interp_t_frm = interp1d(structural_profile['x_stations'], structural_profile['t_frame'], kind='linear', fill_value="extrapolate")
interp_skin_t = interp1d(structural_profile['x_stations'], structural_profile['skin_t'], kind='linear', fill_value="extrapolate")

def propriedades_perfil_Z(h, b, t):
    A_s = (2 * b + h) * t
    I_min = (t * b**3) / 6 + (h * t**3) / 12
    r_g = np.sqrt(I_min / A_s)
    return A_s, I_min, r_g

def calcular_reacoes_apoio(cargas_caso):
    """
    Calcula as reações nos apoios A (pino dianteiro em x_apoio_A) e B (rolete traseiro
    em x_apoio_B) da junção asa-fuselagem para equilibrar estaticamente a viga.
    """
    L_ab = x_apoio_B - x_apoio_A
    sum_Fx, sum_Fy, sum_Fz = 0.0, 0.0, 0.0
    sum_My_A, sum_Mz_A, sum_Mt = 0.0, 0.0, 0.0
    z_A = float(interp_Z_off(x_apoio_A))

    for comp_name, comp_info in components.items():
        if comp_name not in cargas_caso:
            continue
        pos_x, pos_y, pos_z = comp_info['pos']
        c = cargas_caso[comp_name]
        fx, fy, fz = c['Fx'], c['Fy'], c['Fz']
        mt, my, mz = c.get('Mt', 0.0), c.get('My', 0.0), c.get('Mz', 0.0)

        sum_Fx += fx
        sum_Fy += fy
        sum_Fz += fz
        sum_My_A += my + fz * (pos_x - x_apoio_A) + fx * (pos_z - z_A)
        sum_Mz_A += mz + fy * (pos_x - x_apoio_A) - fx * pos_y
        sum_Mt   += mt + (fz * pos_y) - (fy * (pos_z - z_A))

    R_Ax = -sum_Fx
    R_Bz = -sum_My_A / L_ab
    R_Az = -sum_Fz - R_Bz
    R_By = -sum_Mz_A / L_ab
    R_Ay = -sum_Fy - R_By
    R_Mt = -sum_Mt

    return {
        'R_Ax': R_Ax, 'R_Az': R_Az, 'R_Bz': R_Bz,
        'R_Ay': R_Ay, 'R_By': R_By, 'R_Mt': R_Mt
    }

def obter_esforcos_secao(x, cargas_caso, z_center_local, reacoes):
    F_x, V_y, V_z, M_y, M_z, M_t = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    for comp_name, comp_info in components.items():
        pos_x, pos_y, pos_z = comp_info['pos']
        if pos_x > x and comp_name in cargas_caso:
            c = cargas_caso[comp_name]
            F_x += c['Fx']
            V_y += c['Fy']
            V_z += c['Fz']
            
            # Torção (Mx) é a soma do momento de transporte Mt + (Fz * Braço Y) - (Fy * Braço Z)
            M_t += c.get('Mt', 0.0) + (c['Fz'] * pos_y) - (c['Fy'] * (pos_z - z_center_local))
            
            # Momento Fletor Longitudinal (My): momento de transporte My + (Fz * Braço X) + (Fx * Braço Z)
            M_y += c.get('My', 0.0) + c['Fz'] * (pos_x - x) + c['Fx'] * (pos_z - z_center_local)

            # Momento Fletor Lateral (Mz): momento de transporte Mz + (Fy * Braço X) - (Fx * Braço Y)
            M_z += c.get('Mz', 0.0) + c['Fy'] * (pos_x - x) - c['Fx'] * pos_y

    # Inclui as reações dos apoios B e A da junção asa-fuselagem e reação de torção no caixão da asa (x_asa_m)
    z_A = float(interp_Z_off(x_apoio_A))
    if x_apoio_B > x:
        dx_B = x_apoio_B - x
        V_y += reacoes['R_By']
        V_z += reacoes['R_Bz']
        M_y += reacoes['R_Bz'] * dx_B
        M_z += reacoes['R_By'] * dx_B
        M_t -= reacoes['R_By'] * (z_A - z_center_local)

    if x_asa_m > x:
        M_t += reacoes['R_Mt']

    if x_apoio_A > x:
        dx_A = x_apoio_A - x
        F_x += reacoes['R_Ax']
        V_y += reacoes['R_Ay']
        V_z += reacoes['R_Az']
        M_y += reacoes['R_Az'] * dx_A + reacoes['R_Ax'] * (z_A - z_center_local)
        M_z += reacoes['R_Ay'] * dx_A
        M_t -= reacoes['R_Ay'] * (z_A - z_center_local)
            
    return F_x, V_y, V_z, M_y, M_z, M_t

estacoes_analise = np.linspace(x0, x3, 100)
resultados_casos = {}

for nome_caso, cargas in CASOS_CARGA.items():
    res = {'x': estacoes_analise, 'mos_escoamento': [], 'mos_frame': [], 'mos_skin': [], 'L_frame': []}
    delta_P_ult = cargas.get('delta_P', 0.0) * MATERIAL['FS_pressao']
    reacoes = calcular_reacoes_apoio(cargas)
    
    for x in estacoes_analise:
        R = interp_D(x) / 2.0
        if R <= 0.1: R = 0.1 
        z_cent = interp_Z_off(x)
        
        Fx, Vy, Vz, My, Mz, Mt = obter_esforcos_secao(x, cargas, z_cent, reacoes)
        V_res = np.sqrt(Vy**2 + Vz**2)
        M_res = np.sqrt(My**2 + Mz**2)
        
        h_s, b_s, t_s = interp_h_str(x), interp_b_str(x), interp_t_str(x)
        h_f = interp_h_frm(x)
        t_f = interp_t_frm(x)
        t_skin = interp_skin_t(x)
        A_s, I_min, r_g = propriedades_perfil_Z(h_s, b_s, t_s)
        
        # Área e Momento de Inércia da seção completa: Stringers + Revestimento (Skin)
        A_total = (NUM_STRINGERS * A_s) + (2.0 * np.pi * R * t_skin)
        I_yy = (NUM_STRINGERS * A_s * (R**2) / 2.0) + (np.pi * (R**3) * t_skin)
        
        # 1. Tensão normal longitudinal máxima (flexão composta + força axial)
        sigma_flex = abs(M_res * R / I_yy) if I_yy > 0 else 0.0
        sigma_axial = abs(Fx / A_total) if A_total > 0 else 0.0
        sigma_max = sigma_flex + sigma_axial

        # 2. Cisalhamento atuante no anel da caverna (área efetiva de cisalhamento do anel = pi * R * t_frame)
        A_cis_frame = np.pi * R * t_f
        tau_frame_atuante = (V_res / A_cis_frame) if A_cis_frame > 0 else 0.0
        
        # Limiar de ruído numérico de ponto flutuante (1 Pa) e espaçamento máximo construtivo (1.0 m)
        L_MAX_CONSTRUTIVO = 1.0
        if sigma_max > 1.0:
            L_max = min(L_MAX_CONSTRUTIVO, float(np.pi * r_g * np.sqrt(MATERIAL['E'] / (sigma_max * MATERIAL['FS']))))
        else:
            L_max = L_MAX_CONSTRUTIVO
            
        # 3. Estado plano de tensões no revestimento (Von Mises biaxial completo: sigma_x, sigma_hoop e tau_skin)
        q_V = V_res / (np.pi * R) if R > 0 else 0.0
        q_Mt = np.abs(Mt) / (2.0 * np.pi * (R**2)) if R > 0 else 0.0
        tau_skin_atuante = (q_V + q_Mt) / t_skin if t_skin > 0 else 0.0

        # Pressurização atua apenas na região pressurizada da cabine (x <= x2)
        if t_skin > 0 and x <= x2:
            sigma_hoop = (delta_P_ult * R) / t_skin
            sigma_long_p = (delta_P_ult * R) / (2.0 * t_skin)
        else:
            sigma_hoop = 0.0
            sigma_long_p = 0.0

        sigma_x_skin = sigma_max + sigma_long_p
        sigma_eq_skin = np.sqrt(
            (sigma_x_skin**2)
            - (sigma_x_skin * sigma_hoop)
            + (sigma_hoop**2)
            + 3.0 * (tau_skin_atuante**2)
        )
            
        mos_esc = (MATERIAL['sigma_y'] / (sigma_max * MATERIAL['FS'])) - 1 if sigma_max > 1.0 else 5
        mos_frame = (MATERIAL['tau_allow'] / (tau_frame_atuante * MATERIAL['FS'])) - 1 if tau_frame_atuante > 1.0 else 5
        mos_skin = (MATERIAL['sigma_y'] / (sigma_eq_skin * MATERIAL['FS'])) - 1 if sigma_eq_skin > 1.0 else 5
        
        res['mos_escoamento'].append(mos_esc)
        res['mos_frame'].append(mos_frame)
        res['mos_skin'].append(mos_skin)
        res['L_frame'].append(L_max)
        
    resultados_casos[nome_caso] = res

# =============================================================================
# 5. VISUALIZAÇÃO DOS RESULTADOS (Margens de Segurança e Espaçamento)
# =============================================================================
def _rotulo_curto_caso(nome_caso: str) -> str:
    prefixo = nome_caso.split(":")[0].strip()
    mapa_curto = {
        "Caso 1": "1",
        "Caso 2": "2",
        "Caso 3": "3",
        "Caso 4": "4",
        "Caso 5": "5",
        "EV_1_rudder_kick": "EV-1",
        "EV_2_overshoot": "EV-2",
        "COMB_cauda_T": "Cauda-T",
        "EH_2_manobra_pitch": "EH-2",
    }
    return mapa_curto.get(prefixo, prefixo)

fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(11, 13), sharex=True)
cmap = plt.get_cmap('tab10')

for i, (nome_caso, res) in enumerate(resultados_casos.items()):
    cor_c = cmap(i % 10)
    rotulo = _rotulo_curto_caso(nome_caso)
    ax1.plot(res['x'], np.clip(res['mos_escoamento'], -1, 5), color=cor_c, linewidth=1.5, label=rotulo)
    ax2.plot(res['x'], np.clip(res['mos_frame'], -1, 5), color=cor_c, linewidth=1.5, linestyle='--', label=rotulo)
    ax3.plot(res['x'], np.clip(res['mos_skin'], -1, 5), color=cor_c, linewidth=1.5, linestyle='-.', label=rotulo)
    ax4.plot(res['x'], np.clip(res['L_frame'], 0, 1.05), color=cor_c, linewidth=1.5, label=rotulo)

for ax in [ax1, ax2, ax3]:
    ax.axhline(0, color='red', linestyle='-', linewidth=1.2, alpha=0.8)

ax1.set_title("Margem de Segurança - Escoamento dos Stringers (Flexão)", fontsize=11)
ax2.set_title("Margem de Segurança - Cisalhamento das Cavernas", fontsize=11)
ax3.set_title("Margem de Segurança - Revestimento / Skin (Von Mises)", fontsize=11)
ax4.set_title("Distância Máxima entre Cavernas - Critério de Flambagem (Euler)", fontsize=11)
ax4.set_xlabel("Estação x da Fuselagem [m]", fontsize=10)

for ax in [ax1, ax2, ax3, ax4]:
    ax.set_ylabel("MoS" if ax != ax4 else "L_frame [m]", fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.5)

# Legenda única e limpa no topo da figura (fora da área dos gráficos)
handles, labels = ax1.get_legend_handles_labels()
fig.legend(
    handles,
    labels,
    loc='upper center',
    ncol=len(labels),
    frameon=True,
    fontsize=9,
    title="Casos de Carga",
    title_fontsize=9,
    bbox_to_anchor=(0.5, 0.995),
)

plt.tight_layout(rect=[0, 0, 1, 0.955])
plt.show()

# =============================================================================
# 6. VISUALIZAÇÃO 3D DA GEOMETRIA 
# =============================================================================
def plot_fuselage_3d(fuselage_profile, components, num_stringers=36):
    fig = plt.figure(figsize=(13, 7))
    ax = fig.add_subplot(111, projection='3d')

    x_stations = fuselage_profile['x_stations']
    diameters = fuselage_profile['diameters']
    z_offsets = fuselage_profile['z_offsets']

    x_mesh = np.linspace(x_stations[0], x_stations[-1], 60)
    theta_mesh = np.linspace(0, 2 * np.pi, 36)

    r_smooth = np.interp(x_mesh, x_stations, diameters / 2.0)
    z_smooth = np.interp(x_mesh, x_stations, z_offsets)

    X_grid, THETA_grid = np.meshgrid(x_mesh, theta_mesh)
    R_grid, _ = np.meshgrid(r_smooth, theta_mesh)
    Z_off_grid, _ = np.meshgrid(z_smooth, theta_mesh)

    Y_grid = R_grid * np.cos(THETA_grid)
    Z_grid = Z_off_grid + R_grid * np.sin(THETA_grid)

    ax.plot_surface(X_grid, Y_grid, Z_grid, color='cyan', alpha=0.15, edgecolor='none')
    ax.plot_wireframe(X_grid, Y_grid, Z_grid, color='gray', alpha=0.1, rstride=5, cstride=5)

    thetas = np.linspace(0, 2 * np.pi, num_stringers, endpoint=False)
    for th in thetas:
        y_str = r_smooth * np.cos(th)
        z_str = z_smooth + r_smooth * np.sin(th)
        ax.plot(x_mesh, y_str, z_str, color='black', linewidth=0.6, alpha=0.6)

    x_frames = np.arange(x_stations[0], x_stations[-1], 0.5) 
    for x_f in x_frames:
        r_f = np.interp(x_f, x_stations, diameters / 2.0)
        z_f = np.interp(x_f, x_stations, z_offsets)
        y_ring = r_f * np.cos(theta_mesh)
        z_ring = z_f + r_f * np.sin(theta_mesh)
        x_ring = np.full_like(theta_mesh, x_f)
        ax.plot(x_ring, y_ring, z_ring, color='blue', alpha=0.4, linewidth=1.0)

    grupos_legenda = {
        'NLG (Trem de Nariz)':        ('cyan',   'NLG'),
        'MLG (Trem Principal - Esq)': ('blue',   'MLG'),
        'MLG (Trem Principal - Dir)': ('blue',   'MLG'),
        'Asa (Esq)':                  ('green',  'Asa'),
        'Asa (Dir)':                  ('green',  'Asa'),
        'Motor (Esq)':                ('red',    'Motores'),
        'Motor (Dir)':                ('red',    'Motores'),
        'Empenagem Horizontal (Esq)': ('purple', 'EH'),
        'Empenagem Horizontal (Dir)': ('purple', 'EH'),
        'Empenagem Vertical (CA)':    ('orange', 'EV'),
    }
    
    all_x, all_y, all_z = [x_mesh.min(), x_mesh.max()], [Y_grid.min(), Y_grid.max()], [Z_grid.min(), Z_grid.max()]
    grupos_ja_plotados = set()

    for comp_name, comp_data in components.items():
        px, py, pz = comp_data['pos']
        cor, rotulo_grp = grupos_legenda.get(comp_name, ('magenta', comp_name))
        lbl = rotulo_grp if rotulo_grp not in grupos_ja_plotados else None
        if lbl:
            grupos_ja_plotados.add(rotulo_grp)
        ax.scatter(px, py, pz, color=cor, s=55, depthshade=False, label=lbl)
        
        z_eixo = np.interp(px, x_stations, z_offsets)
        ax.plot([px, px], [0, py], [z_eixo, pz], color=cor, linestyle='--', alpha=0.7)
        all_x.append(px); all_y.extend([py, -py]); all_z.append(pz)

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    min_z, max_z = min(all_z), max(all_z)

    ax.set_xlim(min_x, max_x)
    ax.set_ylim(min_y, max_y)
    ax.set_zlim(min_z, max_z)
    ax.set_box_aspect((max_x - min_x, max_y - min_y, max_z - min_z))

    ax.set_xlabel('Estação X [m]')
    ax.set_ylabel('Y [m]')
    ax.set_zlabel('Z [m]')
    ax.set_title("Modelo Estrutural 3D da Fuselagem (Proporções Reais)", fontsize=11)
    ax.legend(loc='upper left', frameon=True, fontsize=9)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    rho_al = 2780.0
    xs_m = np.linspace(x0, x3, 1000)
    Rs_m = interp_D(xs_m) / 2.0
    t_sk_m = interp_skin_t(xs_m)
    h_s_m, b_s_m, t_s_m = interp_h_str(xs_m), interp_b_str(xs_m), interp_t_str(xs_m)
    m_skin = float(np.trapezoid(2.0 * np.pi * Rs_m * t_sk_m * rho_al, xs_m))
    m_str = float(np.trapezoid(NUM_STRINGERS * (2.0 * b_s_m + h_s_m) * t_s_m * rho_al, xs_m))
    x_f_m = np.arange(x0, x3, 0.5)
    R_f_m = interp_D(x_f_m) / 2.0
    m_frames = float(np.sum(2.0 * np.pi * R_f_m * (interp_h_frm(x_f_m) + 0.040) * interp_t_frm(x_f_m) * rho_al))
    m_total_casca = m_skin + m_str + m_frames
    print("=" * 75)
    print("ESTIMATIVA DE MASSA ESTRUTURAL DA FUSELAGEM (Al 2024-T3, rho = 2780 kg/m³)")
    print("=" * 75)
    print(f"  - Revestimento (Skin):        {m_skin:7.1f} kg")
    print(f"  - Stringers ({NUM_STRINGERS}x Perfil Z):   {m_str:7.1f} kg")
    print(f"  - Cavernas / Frames (0.50m):  {m_frames:7.1f} kg")
    print("-" * 75)
    print(f"  => MASSA TOTAL (Casca Limpa): {m_total_casca:7.1f} kg ({m_total_casca * 9.81:8.1f} N)")
    print(f"  => MASSA TOTAL (+20% Secund.):{m_total_casca * 1.20:7.1f} kg ({m_total_casca * 1.20 * 9.81:8.1f} N)")
    print("=" * 75)
    plot_fuselage_3d(fuselage_profile, components, NUM_STRINGERS)
