import pandas as pd
import matplotlib
matplotlib.use('TkAgg')

import matplotlib.pyplot as plt

# --- Carregar os dados ---
df = pd.read_excel("/home/beatriz/Documentos/vscode/TCC/Formulário Final.xlsx")

# ---Selecionar a pergunta---
coluna = "Você acha que é possível aprender Matemática com ChatGPT ?"

# ---Frequência absoluta---
frequencia = df[coluna].value_counts()

# ---Frequência relativa (%)---
porcentagem = df[coluna].value_counts(normalize=True) * 100

# ---Montar tabela---
tabela = pd.DataFrame({
    "Frequência": frequencia,
    "Porcentagem (%)": porcentagem.round(2)
})

print(tabela)

# ---Gráfico---
frequencia.plot(kind="bar", figsize=(7, 4))

plt.title("Possibilidade de aprender Matemática com ChatGPT")
plt.xlabel("Respostas")
plt.ylabel("Quantidade de participantes")
plt.xticks(rotation=0)
plt.tight_layout()
plt.show()

#------------------------------

perguntas = [
    'Qual foi seu nível de compreensão das primeiras questões ? mais especificamente "Resolvendo questões - Parte 01"',
    'Qual foi o nível de compreensão das primeiras questões do "Resolução de Questões - Parte 01" ?',
    'Qual foi seu nível de compreensão no tópico de "Questionando o uso de IA" ? Conseguiu entender melhor IA ?',
    'A partir do que foi feito no tópico "Aprendendo com  IA "  como você avalia esta experiência de aprendizado com ChatGPT'
]

ordem = ["Péssimo", "Ruim", "Mediano", "Bom", "Excelente"]

for i, pergunta in enumerate(perguntas):

    respostas = df[pergunta].str.strip().str.capitalize()

    frequencia = respostas.value_counts().reindex(
        ordem, fill_value=0
    )

    plt.figure(figsize=(7, 4))

    frequencia.plot(kind="bar")

    plt.title(f"Distribuição das avaliações - Etapa {i+1}")
    plt.xlabel("Nível de avaliação")
    plt.ylabel("Número de participantes")
    plt.xticks(rotation=30)

    plt.tight_layout()
    plt.show()
    
    
