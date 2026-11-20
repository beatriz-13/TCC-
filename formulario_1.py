import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from collections import Counter
import re
import warnings
warnings.filterwarnings('ignore')

sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 10

# ============================================================
# 1. CARREGAMENTO
# ============================================================


pasta = Path(__file__).parent

df = pd.read_csv(pasta / "Formulário Inicial.csv", encoding="utf-8-sig")

# Renomear as colunas para usa-las mais tarde
df.columns = [
    'nome', 'grupos', 'email', 'data', 'nome_completo', 'idade',
    'email_institucional', 'matricula', 'curso', 'regiao', 'sexo',
    'contato_chatgpt', 'contato_outras_ia', 'familiaridade',
    'frequencia_uso', 'habilidades_matematicas', 'chatgpt_ajuda',
    'confianca_ia', 'outras_fontes', 'estrategia', 'ia_cola'
]

print(f"Total de respondentes: {len(df)}")

# ============================================================
# 2. LIMPEZA
# ============================================================



# --- Idade: Pegar as idades dos alunos para saber a faixa etária e prevenir erros ---
def clean_idade(x):
    if pd.isna(x): return 'Não informado'
    x = str(x).strip()
    if x in ['14-15', '16-17', '18-19', '20 ou +']:
        return x
    try:
        n = float(x)
        if n <= 15: return '14-15'
        if n <= 17: return '16-17'
        if n <= 19: return '18-19'
        return '20 ou +'
    except:
        return x

df['idade_faixa'] = df['idade'].apply(clean_idade)



# --- Escalas numéricas de familiaridade e frequência dos alunos ---
def clean_scale(x):
    if pd.isna(x): return np.nan
    try: return float(str(x).replace(',', '.').strip())
    except: return np.nan

for c in ['familiaridade', 'frequencia_uso']:
    df[c] = df[c].apply(clean_scale)



# --- Extrair o curso-base ---
def clean_curso(x):
    if pd.isna(x) or str(x).strip() == '':
        return 'Não informado'
    x = str(x)
    if 'Manutenção Automotiva' in x: return 'Manutenção Automotiva'
    if 'Meio Ambiente' in x: return 'Meio Ambiente'
    return 'Outro'

df['curso_base'] = df['curso'].apply(clean_curso)




# --- Categorias com onde os alunos não informaram os dados completos 
colunas_categoricas = [
    'sexo', 'regiao', 'habilidades_matematicas',
    'contato_chatgpt', 'contato_outras_ia', 'chatgpt_ajuda',
    'confianca_ia', 'outras_fontes', 'ia_cola'
]

df[colunas_categoricas] = (
    df[colunas_categoricas]
    .fillna('Não informado')
    .replace('', 'Não informado')
)



# --- Data de resposta ---
df['data_resposta'] = pd.to_datetime(df['data'], format='%A, %d %b %Y, %H:%M', errors='coerce')




print("\nValores únicos por coluna (para conferência):")
for c in ['idade_faixa', 'curso_base', 'sexo', 'habilidades_matematicas',
          'confianca_ia', 'outras_fontes', 'ia_cola']:
    print(f"  {c}: {df[c].value_counts(dropna=False).to_dict()}")



# ============================================================
# 3. PERFIL SOCIODEMOGRÁFICO
# ============================================================

# --- plotar os gráficos ---
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

df['sexo'].value_counts().plot(kind='bar', ax=axes[0,0], color='steelblue')
axes[0,0].set_title('Distribuição por Sexo'); axes[0,0].set_ylabel('N')

df['idade_faixa'].value_counts().plot(kind='bar', ax=axes[0,1], color='coral')
axes[0,1].set_title('Distribuição por Faixa Etária'); axes[0,1].set_ylabel('N')

df['curso_base'].value_counts().plot(kind='bar', ax=axes[1,0], color='seagreen')
axes[1,0].set_title('Distribuição por Curso'); axes[1,0].set_ylabel('N')

df['regiao'].value_counts().head(10).plot(kind='bar', ax=axes[1,1], color='purple')
axes[1,1].set_title('Top 10 Regiões Administrativas'); axes[1,1].set_ylabel('N')
axes[1,1].tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.savefig('perfil_sociodemografico.png', dpi=120, bbox_inches='tight')
plt.show()



# ============================================================
# 4. PERFIL DE USO DE IA
# ============================================================
print("\n=== PERFIL DE USO DE IA ===")
print("\nContato com ChatGPT:")
print(df['contato_chatgpt'].value_counts(normalize=True).mul(100).round(1))
print("\nContato com outras IAs:")
print(df['contato_outras_ia'].value_counts(normalize=True).mul(100).round(1))
print("\nFamiliaridade (1-5):")
print(df['familiaridade'].describe().round(2))
print("\nFrequência de uso (1-5):")
print(df['frequencia_uso'].describe().round(2))
print("\nJá usou IA para cola:")
print(df['ia_cola'].value_counts(normalize=True).mul(100).round(1))

fig, axes = plt.subplots(1, 3, figsize=(16, 5))

# Histograma de familiaridade
df['familiaridade'].dropna().plot(kind='hist',
                                  bins=5,
                                  ax=axes[0],
                                  color='teal',
                                  edgecolor='black',
                                  rwidth=0.8)
                                  
axes[0].set_title('Nível de Familiaridade com ChatGPT')
axes[0].set_xlabel('1 (Nada) → 5 (Muito)')

# Histograma de frequência
df['frequencia_uso'].dropna().plot(kind='hist', bins=5, ax=axes[1],
                                   color='darkorange', edgecolor='black', rwidth=0.8)
axes[1].set_title('Frequência de Uso para Deveres')
axes[1].set_xlabel('1 (Nunca) → 5 (Sempre)')

# Uso para cola
df['ia_cola'].value_counts().plot(kind='bar', ax=axes[2], color='crimson')
axes[2].set_title('Já usou IA para "cola"?')
axes[2].tick_params(axis='x', rotation=0)

plt.tight_layout()
plt.savefig('perfil_uso_ia.png', dpi=120, bbox_inches='tight')
plt.show()

# ============================================================
# 5. PERCEPÇÃO E CONFIANÇA
# ============================================================
print("\n=== PERCEPÇÃO E CONFIANÇA ===")
print("\nChatGPT pode ajudar a resolver problemas:")
print(df['chatgpt_ajuda'].value_counts())
print("\nConfiança nas respostas da IA:")
print(df['confianca_ia'].value_counts(normalize=True).mul(100).round(1))
print("\nCostuma buscar outras fontes:")
print(df['outras_fontes'].value_counts(normalize=True).mul(100).round(1))

fig, axes = plt.subplots(1, 3, figsize=(16, 5))
df['chatgpt_ajuda'].value_counts().plot(kind='bar', ax=axes[0], color='steelblue')
axes[0].set_title('Acredita que ChatGPT ajuda?')

df['confianca_ia'].value_counts().plot(kind='bar', ax=axes[1], color='indianred')
axes[1].set_title('Confiança nas respostas da IA')
axes[1].tick_params(axis='x', rotation=30)

df['outras_fontes'].value_counts().plot(kind='bar', ax=axes[2], color='seagreen')
axes[2].set_title('Busca outras fontes?')
axes[2].tick_params(axis='x', rotation=30)
plt.tight_layout()
plt.savefig('percepcao_confianca.png', dpi=120, bbox_inches='tight')
plt.show()

# ============================================================
# 6. HABILIDADES MATEMÁTICAS
# ============================================================
ordem = ['Insuficiente', 'Ruim', 'Regular', 'Bom', 'Excelente']
cont = df['habilidades_matematicas'].value_counts().reindex(ordem).fillna(0)
print("\n=== AUTOPERCEPÇÃO EM MATEMÁTICA ===")
print(cont)

plt.figure(figsize=(8, 4))
cont.plot(kind='bar', color='slateblue')
plt.title('Autopercepção das Habilidades Matemáticas')
plt.ylabel('Nº de alunos')
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig('habilidades_matematicas.png', dpi=120, bbox_inches='tight')
plt.show()

# ============================================================
# 7. CRUZAMENTOS INTERESSANTES(Dados)
# ============================================================

# --- 7.1 Sexo × Familiaridade ---
plt.figure(figsize=(8, 4))
sns.boxplot(data=df, x='sexo', y='familiaridade', palette='Set2')
plt.title('Familiaridade com ChatGPT por Sexo')
plt.tight_layout()
plt.savefig('cruz_sexo_familiaridade.png', dpi=120, bbox_inches='tight')
plt.show()

# --- 7.2 Curso × Frequência de uso ---
plt.figure(figsize=(8, 4))
sns.boxplot(data=df, x='curso_base', y='frequencia_uso', palette='Set3')
plt.title('Frequência de Uso de IA por Curso')
plt.tight_layout()
plt.savefig('cruz_curso_frequencia.png', dpi=120, bbox_inches='tight')
plt.show()

# --- 7.3 Familiaridade × Confiança ---
plt.figure(figsize=(8, 4))
sns.boxplot(data=df, x='confianca_ia', y='familiaridade', palette='coolwarm')
plt.title('Familiaridade × Confiança nas Respostas')
plt.xticks(rotation=20)
plt.tight_layout()
plt.savefig('cruz_familiaridade_confianca.png', dpi=120, bbox_inches='tight')
plt.show()

# --- 7.4 Uso para cola × Frequência ---
plt.figure(figsize=(8, 4))
sns.boxplot(data=df, x='ia_cola', y='frequencia_uso', palette='Set1')
plt.title('Frequência de Uso × Uso para "Cola"')
plt.tight_layout()
plt.savefig('cruz_cola_frequencia.png', dpi=120, bbox_inches='tight')
plt.show()

# --- 7.5 Habilidades matemáticas × Frequência de uso ---
plt.figure(figsize=(8, 4))
sns.boxplot(data=df[df['habilidades_matematicas'].isin(ordem)],
            x='habilidades_matematicas', y='frequencia_uso',
            order=ordem, palette='viridis')
plt.title('Autopercepção em Matemática × Frequência de Uso de IA')
plt.tight_layout()
plt.savefig('cruz_matematica_frequencia.png', dpi=120, bbox_inches='tight')
plt.show()

# --- 7.6 Tabela de contingência: Sexo × Confiança ---
print("\n=== Cruzamento: Sexo × Confiança ===")
print(pd.crosstab(df['sexo'], df['confianca_ia'], normalize='index').mul(100).round(1))

# --- 7.7 Correlação entre escalas ---
print("\n=== Correlação Familiaridade × Frequência ===")
print(df[['familiaridade', 'frequencia_uso']].corr().round(3))

# ============================================================
# 8. ANÁLISE TEXTUAL DAS ESTRATÉGIAS
# ============================================================
print("\n=== ESTRATÉGIAS MAIS CITADAS ===")

stopwords = set("""
a o e de da do das dos em no na nos nas um uma uns umas para por com que se
eu meu minha me mais mas como não sim quando onde qual quais é são foi ser
tento tento tento também já ou ao aos à às sobre entre depois então
""".split())

def tokenize(text):
    if pd.isna(text): return []
    text = str(text).lower()
    text = re.sub(r'[^aáéíóúâêôãõçàü\w\s]', ' ', text)
    return [w for w in text.split() if w not in stopwords and len(w) > 2]

all_words = []
for t in df['estrategia'].dropna():
    all_words.extend(tokenize(t))

word_freq = Counter(all_words).most_common(20)
print("\nTop 20 palavras nas estratégias:")
for w, c in word_freq:
    print(f"  {w}: {c}")

# Gráfico de palavras mais frequentes
words_df = pd.DataFrame(word_freq, columns=['palavra', 'freq'])
plt.figure(figsize=(10, 5))
sns.barplot(data=words_df, x='freq', y='palavra', palette='magma')
plt.title('Top 20 palavras nas estratégias de resolução')
plt.tight_layout()
plt.savefig('palavras_estrategias.png', dpi=120, bbox_inches='tight')
plt.show()

# --- Categorização manual (heurística por palavras-chave) ---
def categorizar_estrategia(txt):
    if pd.isna(txt): return 'Não respondeu'
    t = str(txt).lower()
    cats = []
    if any(w in t for w in ['chat', 'ia', 'gpt', 'gemini', 'copilot']):
        cats.append('Usa IA')
    if any(w in t for w in ['professor', 'prof', 'monitor', 'colega', 'amiga', 'ajuda']):
        cats.append('Pede ajuda humana')
    if any(w in t for w in ['youtube', 'vídeo', 'video', 'aula']):
        cats.append('Videoaula')
    if any(w in t for w in ['caderno', 'livro', 'site', 'pesquis', 'google', 'artigo']):
        cats.append('Pesquisa/caderno')
    if any(w in t for w in ['fórmula', 'formula', 'cálculo', 'calculo', 'conta']):
        cats.append('Aplica fórmula/cálculo')
    if any(w in t for w in ['sozinho', 'sozinha', 'raciocínio', 'logica', 'lógica', 'cabeça']):
        cats.append('Raciocínio próprio')
    return ' + '.join(cats) if cats else 'Outro'

df['categoria_estrategia'] = df['estrategia'].apply(categorizar_estrategia)
print("\n=== Categorias de estratégia (pode haver múltiplas por aluno) ===")
explode = df['categoria_estrategia'].str.split(' + ').explode()
print(explode.value_counts())

plt.figure(figsize=(10, 4))
explode.value_counts().plot(kind='bar', color='teal')
plt.title('Estratégias citadas pelos alunos')
plt.ylabel('Nº de citações')
plt.xticks(rotation=30, ha='right')
plt.tight_layout()
plt.savefig('categorias_estrategias.png', dpi=120, bbox_inches='tight')
plt.show()

# ============================================================
# 9. PERFIS DE RISCO (síntese)
# ============================================================
print("\n=== PERFIS DE RISCO ===")

# --- Alunos que: usam IA com frequência, confiam totalmente, não checam outras fontes, já usaram para cola ---
risco = df[
    (df['frequencia_uso'] >= 4) &
    (df['confianca_ia'].isin(['Um pouco', 'Com certeza'])) &
    (df['outras_fontes'].str.contains('somente a IA', na=False)) &
    (df['ia_cola'] == 'Sim')
]
print(f"\nAlunos com perfil de alto risco (uso intenso + confiança + não checa + cola): {len(risco)}")
print(risco[['nome', 'idade_faixa', 'curso_base', 'frequencia_uso', 'confianca_ia']].to_string(index=False))

# ---Perfil "cético saudável": usa IA, mas sempre checa outras fontes---
cetico = df[df['outras_fontes'].str.contains('sites, livros', na=False)]
print(f"\nAlunos que sempre buscam outras fontes: {len(cetico)} ({len(cetico)/len(df)*100:.1f}%)")

# ============================================================
# 10. EXPORTAR A LIMPESA
# ============================================================
df.to_csv('base_limpa.csv', index=False, encoding='utf-8-sig')
print("\nBase limpa exportada para 'base_limpa.csv'")


