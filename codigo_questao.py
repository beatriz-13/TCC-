import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

pasta = Path(__file__).parent

dados = pd.read_excel(
    pasta / "planilha_notas_aprendendoIA.ods",
    engine="odf"
)

print(dados.head())
print(dados.shape)
print(dados.columns)
print(dados.info())

# Estatísticas descritivas QUESTIONARIOS
estatisticas = dados[["Questionário 1", "Questionário 2", "Media"]].describe().T

print("\nESTATÍSTICAS DESCRITIVAS")
print(estatisticas)

# Boxplot
dados[["Questionário 1", "Questionário 2", "Media"]].boxplot()

plt.title("Distribuição das notas dos questionários")
plt.ylabel("Notas")
plt.grid(axis="y", alpha=0.3)
 
plt.savefig(
    pasta / "boxplot_notas.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()

print("\nGráfico salvo como: boxplot_notas.png")

import pandas as pd

pasta_tcc = '/home/beatriz/Documentos/vscode/TCC/'

# Carregar os arquivos
df_parte1 = pd.read_csv(pasta_tcc + 'OSIERDP 20242-Resolução de Questão - Parte 1-notas.csv')
df_parte2 = pd.read_csv(pasta_tcc + 'OSIERDP 20242-Resolução de questões - Parte 2-notas.csv')

# Função robusta para limpar e converter a coluna de notas para float
def limpar_nota(col):
    if col.dtype == object:
        s = col.astype(str).str.replace('–', '0', regex=False).str.replace('-', '0', regex=False)
        s = s.str.replace('.', '', regex=False)
        s = s.str.replace(',', '.', regex=False)
        return pd.to_numeric(s, errors='coerce').fillna(0)
    return pd.to_numeric(col, errors='coerce').fillna(0)

# Aplicando a limpeza nas colunas de nota
df1['Nota_1_Num'] = limpar_nota(df1['Nota/10,000'])
df2['Nota_2_Num'] = limpar_nota(df2['Nota/10,000'])

# Agrupando por aluno (pegando a maior nota por tentativa)
resumo_p1 = df1.groupby(['Endereço de e-mail', 'Nome', 'Sobrenome'])['Nota_1_Num'].max().reset_index()
resumo_p2 = df2.groupby(['Endereço de e-mail', 'Nome', 'Sobrenome'])['Nota_2_Num'].max().reset_index()

# Mesclando as tabelas
tabela_final = pd.merge(resumo_p1, resumo_p2, on=['Endereço de e-mail', 'Nome', 'Sobrenome'], how='outer').fillna(0)


tabela_final['Nota_Final'] = (tabela_final['Nota_1_Num'] + tabela_final['Nota_2_Num']) / 2

print(tabela_final.head())]
