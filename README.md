# Análise Multivariada de Risco de Alagamento - Fortaleza — Análise Multivariada de Risco (Lixo × Alagamentos)

> **AVISO IMPORTANTE (DISCLAIMER):** Este software é um **protótipo acadêmico** desenvolvido para fins de estudo e extensão universitária. Os índices de risco, predições e correlações apresentados aqui são baseados em modelos heurísticos e dados amostrais.
> **Este projeto NÃO deve ser utilizado para decisões oficiais.**

---

## 📥 Download dos Dados Utilizados

Os dados brutos necessários para executar o projeto (CSV, XLSX e GeoJSON originais) podem ser baixados diretamente no Google Drive:

👉 **[https://drive.google.com/drive/folders/17K1tM-U_Yh8x6tE9jYNuwslyPZ6L65G0?usp=sharing](https://drive.google.com/drive/folders/17K1tM-U_Yh8x6tE9jYNuwslyPZ6L65G0?usp=sharing)**

Após baixar, coloque todos os arquivos na seguinte estrutura:

```
static/
```

Assim, o ETL conseguirá localizar corretamente os dados para gerar os indicadores, gráficos e o arquivo `result.json` usado no mapa interativo.

---

## Sobre o Projeto

Originalmente concebido para analisar a relação entre o **descarte irregular de lixo** e os alagamentos em Fortaleza, este projeto evoluiu para uma **Análise Multivariada de Riscos**. Durante a investigação de dados (Big Data), identificou-se que o lixo, embora seja um agravante crítico, não atua isoladamente.

O sistema processa dados heterogêneos para gerar um **Índice Ponderado de Risco**, classificando as Secretarias Regionais em níveis de vulnerabilidade.

---

## 🌎 Demonstração do Projeto

Mapa interativo construído com Flask, Leaflet.js, GeoJSON e Chart.js, permitindo visualizar indicadores por Secretaria Regional.

---

## 📊 Metodologia Analítica

* Uso de GeoPandas, Pandas e Scikit-Learn
* Normalização MinMax
* Cálculo de densidades (lixo, inundação, risco geológico, drenagem)
* Modelo de score ponderado
* Geração de clusters de risco (Baixo, Médio, Alto)

---

## 🧱 Estrutura de Pastas

```
fortaleza-risk-map/
│
├── app.py
├── requirements.txt
├── Procfile
├── README.md
│
├── templates/
│   ├── index.html
│   └── mapa.html
│
├── static/
│   ├── data/
│   ├── images/
│
├── etl/
│   ├── etl.py
│   ├── raw/
│   └── processed/
│
└── .gitignore
```

---

## ▶️ Como Rodar Localmente

```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

---

## ☁️ Deploy no Render / Railway

**Procfile:**

```
web: gunicorn app:app
```

**Build command:** `pip install -r requirements.txt`

**Start command:** `gunicorn app:app`

---

## 📚 Relatório Acadêmico (Resumo)

Estudo realizado em 2025 pelos estudantes:

* Antônio Kayo César do Nascimento Cavalcante
* Yasmin de Sousa Cavalcante Freitas
* Marcos Sousa Ferreira
* Marlon Mendes Gonçalves
* Carlos Gabriel da Silva Castro

**Professor:** Boanerges Almeida

O trabalho demonstra, por técnicas de ciência de dados e geoprocessamento, a relação entre o descarte de lixo e a intensificação de alagamentos.

---

## 🧰 Tecnologias

* Python, Flask
* Pandas, GeoPandas
* Scikit-Learn
* Matplotlib, Seaborn
* Leaflet.js, Chart.js

---

## 📩 Contato

Projeto desenvolvido para fins acadêmicos e de portfólio.
