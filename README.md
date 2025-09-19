# ScrapTF

<img src="https://github.com/luisgbamaral/ScrapTF/blob/main/ScraperTF.png">

EN/PT

⚖️ **Measuring the Use of L&E in STF Rulings**
This repository contains the source code to replicate the results of the paper "Mensuração do Uso da AED nas Decisões do STF Através de um Algoritmo Supervisionado" (Measuring the Use of L&E in STF Rulings Through a Supervised Algorithm), submitted to the 18th Congress of the Brazilian Law and Economics Association (ABDE).

🎯 **About the Project**
This project has a twofold objective:

Data Collection: To scrape and process rulings from the Brazilian Supreme Federal Court (STF) that contain key terms from Law and Economics (L&E).

Ruling Classification: To train and evaluate Machine Learning models to automatically classify whether a ruling genuinely applies L&E concepts or if the mentions are merely incidental.

📊 **Key Results**
7 classification models were trained and evaluated.

The best model was selected based on the Friedman and Nemenyi statistical tests.

The winning model, a Support Vector Classifier (SVC), achieved an accuracy of over 92% on the test set.

266 rulings applying L&E were identified between January 1, 2012, and August 31, 2025.

📂 **Structure**
The code is primarily organized in Jupyter Notebooks (.ipynb) and uses a sequential programming approach to facilitate understanding and replication of the results.

📦 **Data**
All input data and the generated outputs are available at the link below:
www.kaggle.com/datasets/luisgamaral/scaptf

------------------------------------------------------------------------------------------------------------------------------------------------------------------


⚖️ **Mensuração do Uso da AED em Decisões do STF**
Este repositório contém o código-fonte para replicar os resultados do artigo "Mensuração do Uso da AED nas Decisões do STF Através de um Algoritmo Supervisionado", submetido ao XVIII Congresso da Associação Brasileira de Direito e Economia (ABDE).

🎯 **Sobre o Projeto**
O objetivo deste projeto é duplo:

Coletar dados: Realizar a extração e consolidação de decisões do Supremo Tribunal Federal (STF) que contenham termos-chave da Análise Econômica do Direito (AED).

Classificar decisões: Treinar e avaliar modelos de Machine Learning para classificar automaticamente se uma decisão aplica de fato os conceitos da AED ou se as menções são apenas incidentais.

📊 **Principais Resultados**
7 modelos de classificação foram treinados e avaliados.

A seleção do melhor modelo foi feita com base nos testes estatísticos de Friedman e Nemenyi.

O modelo vencedor, Support Vector Classifier (SVC), alcançou acurácia superior a 92% no conjunto de teste.

Foram identificadas 266 decisões com aplicação da AED no período de 01/01/2012 a 31/08/2025.

📂 **Estrutura**
Os códigos estão organizados, em sua maioria, em Notebooks Jupyter (.ipynb) e utilizam uma abordagem de programação sequencial para facilitar o entendimento e a replicação dos resultados.

📦 **Dados**
Todos os dados de entrada (inputs) e os resultados gerados (outputs) estão disponíveis no link abaixo:
www.kaggle.com/datasets/luisgamaral/scaptf


