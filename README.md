# Inteligência Artificial Generativa e Ensino de Matemática na Educação Profissional e Tecnológica: Uma Análise Exploratória

Análise de dados de uma oficina sobre o uso do ChatGPT (IA generativa) no aprendizado de Matemática, desenvolvida como parte do Trabalho de Conclusão de Curso (TCC) de [Beatriz de Olivera Araújo] — [Matemática / IFB].

## Sobre o projeto

A oficina aplicou atividades de resolução de questões de Matemática com apoio do ChatGPT e discussões sobre o uso crítico da IA. Os dados foram coletados por meio de:

- **Formulário Inicial**: perfil sociodemográfico dos participantes (idade, curso, sexo, região), contato prévio com IA, familiaridade, frequência de uso, confiança nas respostas e autopercepção em Matemática.
- **Formulário Final**: avaliação da experiência (possibilidade de aprender Matemática com ChatGPT, nível de compreensão das etapas "Resolução de Questões – Parte 01", "Questionando o uso de IA" e "Aprendendo com IA").
- **Notas dos questionários**: desempenho nas atividades "Resolução de Questões – Parte 1 e Parte 2" (exportadas do Moodle) e planilha consolidada com as notas.

Os scripts deste repositório realizam a limpeza dos dados, estatística descritiva e geração de gráficos para essas fontes.

## Estrutura do repositório

| Arquivo | Descrição |
|---|---|
| `formulario_1.py` | Análise do Formulário Inicial: limpeza, perfil sociodemográfico, perfil de uso de IA, percepção e confiança, cruzamentos entre variáveis, análise textual das estratégias de resolução, perfis de risco e exportação da base limpa (`base_limpa.csv`). |
| `formulario_2.py` | Análise do Formulário Final: frequências e porcentagens da pergunta sobre aprender Matemática com ChatGPT e distribuição das avaliações (Péssimo a Excelente) por etapa da oficina. |
| `codigo_questao.py` | Estatísticas descritivas e boxplot das notas dos questionários (a partir de `planilha_notas_aprendendoIA.ods`) e consolidação das notas das Partes 1 e 2 (maior nota por aluno e média final). |
| `comparacao.py` | Este arquivo faz um comparação das questões parecidas que podemos ver no formulário 1 e 2  |

## Requisitos

- Python 3.10+
- Bibliotecas: `pandas`, `numpy`, `matplotlib`, `seaborn`, `openpyxl`, `odfpy`

```bash
pip install pandas numpy matplotlib seaborn openpyxl odfpy
```

## Como executar

1. Clone o repositório:

```bash
git clone [URL-do-repositório]
cd [nome-da-pasta]
```

2. Coloque os arquivos de dados na mesma pasta dos scripts (veja a seção *Dados*).

3. Execute o script desejado:

```bash
python formulario_1.py
python formulario_2.py
python codigo_questao.py
```

## Dados

Os scripts esperam os seguintes arquivos:

- `Formulário Inicial.csv`
- `Formulário Final.xlsx`
- `planilha_notas_aprendendoIA.ods`
- `OSIERDP 20242-Resolução de Questão - Parte 1-notas.csv`
- `OSIERDP 20242-Resolução de questões - Parte 2-notas.csv`

> **Atenção:** os dados contêm informações pessoais dos participantes (nome, e-mail, matrícula, idade) e, em parte, de menores de idade. Por isso **não são publicados** neste repositório, em conformidade com a LGPD. Os arquivos estão listados no `.gitignore`.

## Saídas geradas

- `perfil_sociodemografico.png`, `perfil_uso_ia.png`, `percepcao_confianca.png`, `habilidades_matematicas.png`
- `cruz_*.png` (cruzamentos entre variáveis)
- `palavras_estrategias.png`, `categorias_estrategias.png`
- `boxplot_notas.png`
- `base_limpa.csv` (base tratada do Formulário Inicial)

## Metodologia

- **Limpeza:** padronização de faixas etárias, conversão de escalas numéricas, agrupamento de cursos e tratamento de valores ausentes como "Não informado".
- **Análise descritiva:** frequências absolutas e relativas, histogramas, boxplots e tabelas de contingência.
- **Análise textual:** contagem de palavras e categorização por palavras-chave das estratégias de resolução de problemas.
- **Notas:** para cada aluno, considera-se a maior nota entre as tentativas em cada parte; a nota final é a média das duas partes.

## Autoria

[Beatriz de Oliveira Araújo] — [1beatrizoliv.araujo@gmail.com]
Orientador(a): [Adriana Barbosa de Souza]

## Licença

[Ex.: MIT, ou "Uso acadêmico"]
