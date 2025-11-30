import pandas as pd
import geopandas as gpd
import json
import os
from pyproj import CRS
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import warnings
import seaborn as sns

warnings.filterwarnings("ignore")

print("="*60)
print("INICIANDO ETL REFINADO: DENSIDADES E PROPORÇÕES")
print("="*60)

# ===============================================
# 1. CARREGAMENTO
# ===============================================
try:
    csv_demandas = pd.read_csv("demandas-marco-abril-2022.csv", sep=",", encoding="utf-8")
    csv_ocorrencias = pd.read_csv("ocorrencias_por_regional.csv", sep=",", encoding="utf-8")
    csv_idh = pd.read_excel("indicededesenvolvimentohumano.xlsx")
    
    regionais_novas = gpd.read_file("static/data/Secretarias_Executivas_Regionais.geojson")
    bairros = gpd.read_file("static/data/Bairros_de_Fortaleza.geojson")
    canais = gpd.read_file("static/data/Canais.geojson")
    valas_drenos = gpd.read_file("static/data/Valas_e_Drenos.geojson")
    risco_geo = gpd.read_file("static/data/risco_geologico.json")
    inundacao_geo = gpd.read_file("static/data/inundacao_raster_corrected.geojson")
    
    # Preparar CRS Métrico para cálculos de área
    crs_metrico = CRS.from_epsg(31984)
    regionais_proj = regionais_novas.to_crs(crs_metrico)
    # Calcular área em km2 para densidades
    regionais_proj['area_km2'] = regionais_proj.geometry.area / 1_000_000
    
except Exception as e:
    print(f"ERRO CRÍTICO NO CARREGAMENTO: {e}")
    exit()

# ===============================================
# 2. PROCESSAMENTO: LIXO (Com Densidade e % do Total)
# ===============================================
print(">>> Calculando Estatísticas de Lixo...")
csv_demandas.columns = csv_demandas.columns.str.strip().str.upper()
csv_fortaleza = csv_demandas[
    (csv_demandas['CIDADE'].str.upper().str.strip() == 'FORTALEZA') & 
    (csv_demandas['ZONA'].str.contains('SER', na=False))
].copy()

LIXO_KEYWORDS = ["COLETA", "ENTULHO", "PODA", "LIXO", "VOLUMOSO"]
csv_fortaleza['IS_LIXO'] = csv_fortaleza['TIPO DA DEMANDA'].str.upper().str.contains('|'.join(LIXO_KEYWORDS), na=False)

agg_lixo = csv_fortaleza[csv_fortaleza['IS_LIXO']].groupby('ZONA').size().reset_index(name='lixo_abs')
agg_lixo.rename(columns={'ZONA': 'regiao_adm'}, inplace=True)

# --- NOVO: Proporção do Total da Cidade ---
total_lixo_cidade = agg_lixo['lixo_abs'].sum()
agg_lixo['lixo_perc_total'] = (agg_lixo['lixo_abs'] / total_lixo_cidade) * 100

# ===============================================
# 3. PROCESSAMENTO: ALAGAMENTO (Com % do Total)
# ===============================================
print(">>> Calculando Estatísticas de Alagamento...")
ALAGAMENTO_KEYWORDS = ["Inundação", "Alagamento"]
df_alagamento = csv_ocorrencias[
    csv_ocorrencias['Tipologia de Ocorrência'].isin(ALAGAMENTO_KEYWORDS)
].copy()

df_alagamento['Regional'] = df_alagamento['Regional'].str.replace('SR ', 'SER ', regex=False)
df_alagamento = df_alagamento[df_alagamento['Regional'] != 'TODAS']

agg_alagamento = df_alagamento.groupby('Regional')['Ocorrências'].sum().reset_index()
agg_alagamento.rename(columns={'Regional': 'regiao_adm', 'Ocorrências': 'alagamento_abs'}, inplace=True)

# --- NOVO: Proporção do Total da Cidade ---
total_alag_cidade = agg_alagamento['alagamento_abs'].sum()
agg_alagamento['alagamento_perc_total'] = (agg_alagamento['alagamento_abs'] / total_alag_cidade) * 100

# ===============================================
# 4. PROCESSAMENTO: IDH
# ===============================================
print(">>> Processando IDH...")
df_idh = csv_idh[['Bairros', 'IDH']].copy()
df_idh['IDH'] = pd.to_numeric(df_idh['IDH'].astype(str).str.replace(',', '.'), errors='coerce')
df_idh.dropna(subset=['IDH'], inplace=True)

bairros = bairros.to_crs(regionais_novas.crs)
bairros['centroide'] = bairros.geometry.centroid
bairros_geo = bairros.set_geometry('centroide')
join_bairro_regional = gpd.sjoin(bairros_geo, regionais_novas[['regiao_adm', 'geometry']], how='inner', predicate='within')
mapa_bairro = join_bairro_regional[['Nome', 'regiao_adm']].drop_duplicates()
idh_regional = df_idh.merge(mapa_bairro, left_on='Bairros', right_on='Nome', how='inner')

agg_idh = idh_regional.groupby('regiao_adm')['IDH'].mean().reset_index()
agg_idh.rename(columns={'IDH': 'idh_medio'}, inplace=True)

# ===============================================
# 5. PROCESSAMENTO: DENSIDADE DE RISCO (Geo + Inundação)
# ===============================================
print(">>> Calculando Densidade Areal de Riscos...")

def calcular_densidade_risco(gdf_regionais, gdf_risco, nome_coluna_saida):
    if gdf_risco is None or gdf_risco.empty:
        return pd.DataFrame({'regiao_adm': gdf_regionais['regiao_adm'], nome_coluna_saida: 0.0})
    
    gdf_risco = gdf_risco.to_crs(crs_metrico)
    # Interseção para pegar apenas a área de risco DENTRO da regional
    overlay = gpd.overlay(gdf_regionais, gdf_risco, how='intersection')
    overlay['area_risco'] = overlay.geometry.area
    
    soma_risco = overlay.groupby('regiao_adm')['area_risco'].sum().reset_index()
    resultado = gdf_regionais[['regiao_adm', 'geometry']].merge(soma_risco, on='regiao_adm', how='left').fillna(0)
    
    # Porcentagem da área da regional que está comprometida
    resultado[nome_coluna_saida] = (resultado['area_risco'] / resultado.geometry.area) * 100
    return resultado[['regiao_adm', nome_coluna_saida]]

df_densidade_geo = calcular_densidade_risco(regionais_proj, risco_geo, 'perc_area_risco_geo')
df_densidade_inund = calcular_densidade_risco(regionais_proj, inundacao_geo, 'perc_area_inundacao')

# ===============================================
# 6. PROCESSAMENTO: INFRAESTRUTURA (Drenagem)
# ===============================================
print(">>> Calculando Densidade de Drenagem...")
canais_proj = canais.to_crs(crs_metrico)
valas_proj = valas_drenos.to_crs(crs_metrico)

canais_clip = gpd.overlay(canais_proj, regionais_proj, how='intersection')
valas_clip = gpd.overlay(valas_proj, regionais_proj, how='intersection')
canais_clip['comprimento'] = canais_clip.geometry.length
valas_clip['comprimento'] = valas_clip.geometry.length

infra_total = pd.concat([
    canais_clip.groupby('regiao_adm')['comprimento'].sum(),
    valas_clip.groupby('regiao_adm')['comprimento'].sum()
]).groupby('regiao_adm').sum().reset_index()

agg_infra = regionais_proj[['regiao_adm', 'area_km2']].merge(infra_total, on='regiao_adm', how='left').fillna(0)
# Km de rede por Km2 de área (Densidade)
agg_infra['densidade_drenagem'] = (agg_infra['comprimento'] / 1000) / agg_infra['area_km2']

# ===============================================
# 7. CONSOLIDAÇÃO E CÁLCULO DO SCORE REVISADO
# ===============================================
print(">>> Consolidando Master Dataframe...")

# Base com área para calcular densidade do lixo
df_master = regionais_proj[['regiao_adm', 'area_km2']].copy()

# Merge de todas as variáveis
df_master = df_master.merge(agg_lixo, on='regiao_adm', how='left').fillna(0)
df_master = df_master.merge(agg_alagamento, on='regiao_adm', how='left').fillna(0)
df_master = df_master.merge(agg_idh, on='regiao_adm', how='left')
df_master['idh_medio'] = df_master['idh_medio'].fillna(df_master['idh_medio'].mean())
df_master = df_master.merge(df_densidade_geo, on='regiao_adm', how='left').fillna(0)
df_master = df_master.merge(df_densidade_inund, on='regiao_adm', how='left').fillna(0)
df_master = df_master.merge(agg_infra[['regiao_adm', 'densidade_drenagem']], on='regiao_adm', how='left').fillna(0)

# --- NOVO: Densidade de Lixo (Demandas por Km2) ---
# Isso corrige a distorção de regionais grandes terem mais lixo apenas por serem grandes
df_master['densidade_lixo'] = df_master['lixo_abs'] / df_master['area_km2']

# --- NORMALIZAÇÃO (MinMax) ---
scaler = MinMaxScaler()

# Variáveis para o Índice
cols_to_norm = [
    'densidade_lixo',        # Substitui lixo absoluto
    'idh_medio', 
    'perc_area_risco_geo', 
    'perc_area_inundacao', 
    'densidade_drenagem'
]

# Criar colunas normalizadas (0 a 1)
df_norm = pd.DataFrame(scaler.fit_transform(df_master[cols_to_norm]), columns=[c+'_norm' for c in cols_to_norm])
df_final = pd.concat([df_master, df_norm], axis=1)

# --- CÁLCULO DO SCORE (PESOS REVISADOS) ---
# Lógica baseada nos documentos:
# 1. Risco Geo (30%): O maior causador de desastres (desabamentos) [IPPLAN]
# 2. Inundação (30%): A mancha natural de onde a água acumula.
# 3. Lixo (15%): Aumentado de 10% para 15%. [Pajeú] diz que obstrui canais, anulando a drenagem.
# 4. IDH (10%): Reduzido para 10%. É vulnerabilidade social, não causa física direta.
# 5. Drenagem (15%): Infraestrutura mitigadora.

print(">>> Calculando Score com Pesos Ajustados...")
df_final['score_risco'] = (
    (df_final['perc_area_risco_geo_norm'] * 0.30) +
    (df_final['perc_area_inundacao_norm'] * 0.30) +
    (df_final['densidade_lixo_norm'] * 0.15) +       # Agora usa densidade!!!
    ((1 - df_final['idh_medio_norm']) * 0.10) +       # Invertido
    ((1 - df_final['densidade_drenagem_norm']) * 0.15) # Invertido
)

# Classificação
df_final['cluster_risco'] = pd.qcut(df_final['score_risco'], 3, labels=['Baixo', 'Médio', 'Alto'])

# ===============================================
# 8. PREDICIT (Lógica Aprimorada)
# ===============================================
def gerar_predicao(row):
    nivel = row['cluster_risco']
    # Usa os dados brutos para o texto ficar humano
    risco_geo = row['perc_area_risco_geo']
    lixo_perc = row['lixo_perc_total']
    
    if nivel == 'Alto':
        if risco_geo > 10:
            return f"ALERTA CRÍTICO: {risco_geo:.1f}% da área é geologicamente instável. Risco iminente de desabamento se houver chuva persistente."
        else:
            return f"ALERTA OPERACIONAL: A região concentra {lixo_perc:.1f}% de todo o lixo da cidade. Obstrução de drenagem é o fator crítico aqui."
    elif nivel == 'Médio':
        return "ATENÇÃO: Infraestrutura no limite. Requer limpeza preventiva de canais."
    else:
        return "MONITORAMENTO: Risco controlado, mas verificar pontos isolados de alagamento histórico."

df_final['predicao_texto'] = df_final.apply(gerar_predicao, axis=1)

# ===============================================
# 9. EXPORTAÇÃO
# ===============================================
# Preparar JSON para o Front-end (mantendo nomes compatíveis com seu HTML)
export_cols = {
    'regiao_adm': 'regiao',
    'lixo_abs': 'lixo',                # Valor absoluto para exibir no gráfico
    'alagamento_abs': 'alagamento',    # Valor absoluto para exibir no gráfico
    'idh_medio': 'idh',
    'perc_area_risco_geo': 'risco_geo',
    'densidade_drenagem': 'densidade_drenagem', # Nome compatível com o HTML
    'cluster_risco': 'cluster',
    'predicao_texto': 'predict'
}

df_export = df_final.rename(columns=export_cols)[list(export_cols.values())]

# Arredondamentos estéticos
df_export['idh'] = df_export['idh'].round(3)
df_export['risco_geo'] = df_export['risco_geo'].round(2)
df_export['densidade_drenagem'] = df_export['densidade_drenagem'].round(2)

if not os.path.exists('static/data'): os.makedirs('static/data')
df_export.to_json('static/data/result.json', orient='records', force_ascii=False, indent=2)

print(f"[OK] JSON gerado com sucesso. Pesos e densidades aplicados.")

#Se o arquivo já tiver 'lixo', 'idh' etc.., elas vão ser descorbertas aqui antes do merge
colunas_geo_originais = ['regiao_adm', 'geometry']

# Verifica se existem outras colunas vitais no seu geojson original (ex: 'id'), se tiver, adicione na lista acima
regionais_limpas = regionais_novas[colunas_geo_originais].copy()

# Agora fazemos o merge limpo
regionais_com_dados = regionais_limpas.merge(df_export, left_on='regiao_adm', right_on='regiao', how='left')

# Salva o arquivo sobrescrevendo o anterior
regionais_com_dados.to_file("static/data/Secretarias_Executivas_Regionais.geojson", driver='GeoJSON')

print(f"[OK] GeoJSON atualizado com métricas (sem colunas duplicadas).")
# ===============================================
# 10. GRÁFICOS (Atualizados para refletir Densidade)
# ===============================================
output_path = 'static/images/'
if not os.path.exists(output_path): os.makedirs(output_path)
df_g = df_export.set_index('regiao')

# Gráfico de Cluster
plt.figure(figsize=(10, 6))
colors = df_g['cluster'].map({'Alto': '#d73027', 'Médio': '#fee08b', 'Baixo': '#4575b4'})
df_g['alagamento'].sort_values().plot(kind='barh', color=colors)
plt.title('Ocorrências de Alagamento (Cor = Índice de Risco Calculado)')
plt.tight_layout()
plt.savefig(output_path + 'grafico_resultado_cluster.png')
plt.close()

# Gráfico de Correlação Lixo (Agora usando Densidade no Eixo X para provar o ponto)
# Isso deve melhorar a linha de tendência que estava "flat"
plt.figure(figsize=(8, 6))
# Pegando a densidade calculada no df_final
densidade_lixo_plot = df_final.set_index('regiao_adm')['densidade_lixo']
plt.scatter(densidade_lixo_plot, df_g['alagamento'], color='red', alpha=0.7)
z = np.polyfit(densidade_lixo_plot, df_g['alagamento'], 1)
p = np.poly1d(z)
plt.plot(densidade_lixo_plot, p(densidade_lixo_plot), "b--")
plt.title('Correlação: Densidade de Lixo (Demandas/Km²) vs Alagamentos')
plt.xlabel('Demandas de Lixo por Km²')
plt.ylabel('Alagamentos')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(output_path + 'grafico_correlacao_lixo.png')
plt.close()

# --- Gráfico Extra: Mapa de Calor de Correlação (Heatmap) ---
plt.figure(figsize=(10, 8))
# Seleciona apenas as colunas numéricas usadas no modelo
cols_corr = ['lixo_abs', 'alagamento_abs', 'idh_medio', 'perc_area_risco_geo', 'densidade_drenagem']
labels_corr = ['Lixo', 'Alagamentos', 'IDH', 'Risco Geo.', 'Drenagem']

# Calcula a matriz de correlação
corr = df_final[cols_corr].corr()

# Gera o heatmap com agrupamento (Clustermap)
# Nota: O clustermap cria sua própria figura, então salvamos direto o objeto retornado
g = sns.clustermap(corr, 
                   annot=True, 
                   cmap="coolwarm", 
                   xticklabels=labels_corr, 
                   yticklabels=labels_corr,
                   figsize=(8, 8))

plt.title('Matriz de Correlação e Agrupamento', pad=20)
# O clustermap precisa ser salvo através do objeto 'g'
g.savefig(output_path + 'grafico_heatmap_correlacao.png')
plt.close()
print("[OK] Gráfico de Heatmap gerado.")

# (Os outros gráficos permanecem similares)
print("[OK] Gráficos atualizados.")