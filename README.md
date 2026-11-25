# Pos Indonesia: Enterprise Business Work Samples

Work samples from my role as **Bidding Staff** in the **Enterprise Business Sub-Directorate, PT Pos Indonesia (Persero)**, November 2026 to present.

This repository documents *how* the work was done (methods, statistics, limitations). It contains no raw data, no personal data, and no internal tender or complaint data.

## Scope of work

| Area | What I do |
|---|---|
| Procurement monitoring | Scrape the government General Procurement Plan (RUP) portal weekly and distribute the results to PT Pos Indonesia branch offices across Indonesia |
| Lead tracking | Maintain and check the LPSE tender spreadsheet to identify lead opportunities for the bidding team |
| Public perception analysis | Sentiment and aspect analysis of public opinion on X (documented below) |

## Project: Public sentiment toward PT Pos Indonesia on X

An exploratory analysis of **93 public opinions** (30 replies and 63 quote tweets from 91 accounts) responding to one viral thread on 22-23 November 2026 that asked why Pos Indonesia trails private couriers.

### Method

1. **Collection:** 125 raw tweets (62 replies, 63 quote tweets) collected with tweet-harvest v2.7.1 on Google Colab, using the `conversation_id:` and `quoted_tweet_id:` search operators. Only 62 of 111 replies could be retrieved (private, filtered or deleted accounts).
2. **Cleaning:** removed the thread author's replies and replies without an opinion; normalized slang. Result: 93 opinions.
3. **Labeling:** three annotators (two people and one AI model) labeled sentiment (Negative, Positive, Mixed, Neutral) and ten aspects with a written codebook. Order was randomized; usernames and likes were hidden.
4. **Final label:** majority vote (2 of 3); nine ties were decided with codebook rules.
5. **Analysis (Python: pandas, NumPy, SciPy, scikit-learn):** descriptive statistics, Wilson confidence intervals, chi-square, binomial test, Mann-Whitney U, Spearman correlation, Cohen's and Fleiss' Kappa.

### Key results (indicative only)

| Sentiment | Count | Share | 95% CI |
|---|---|---|---|
| Negative | 61 | 65.6% | 55.5-74.5% |
| Neutral | 15 | 16.1% | 10.0-24.9% |
| Mixed | 11 | 11.8% | 6.7-20.0% |
| Positive | 6 | 6.5% | 3.0-13.4% |

| Aspect | Criticism | Praise |
|---|---|---|
| Innovation and adaptation | 17 | 0 |
| Work culture and HR | 17 | 0 |
| Operating hours | 16 | 0 |
| SOE status and governance | 14 | 0 |
| Tariff | 7 | 3 |
| Speed and reliability | 2 | 8 |
| Customer service | 5 | 1 |
| Network reach | 2 | 4 |
| Systems and technology | 4 | 1 |
| Non-parcel services | 2 | 2 |

- Criticism clustered on organizational aspects (innovation, work culture, operating hours, SOE status) rather than on delivery itself.
- Praise for speed and reach exists but rests on very few opinions, so it is anecdotal.
- One quote tweet holds 98.1% of all likes; negative opinions were not significantly more liked than others (Mann-Whitney p = 0.35).
- Competitors were mentioned in 17 opinions (18.3%).

### Limitations

- The thread's question was leading, so the roughly two-thirds negative share does **not** represent overall public opinion.
- One thread, not a random sample; p-values and confidence intervals are descriptive.
- Inter-annotator agreement is moderate (Fleiss' Kappa = 0.55); several aspects are lower (Kappa 0.30-0.39).
- The AI model drafted the codebook, labeled, and helped decide ties (8 of 9 tie decisions matched its label). If ties had followed the human annotator's labels, the negative share would be 59.1%; the conclusions do not change.
- Findings should be validated against internal complaint data before any decision is based on them.

## Repository contents

```
Pos-Indonesia-Enterprise-Business/
├── README.md
├── .gitignore
├── docs/
│   ├── Sinyal_Awal_Persepsi_Netizen_terhadap_Pos_Indonesia.pdf
│   └── Laporan_Pendamping_Metode_Proses_Analisis_dan_Angka_Lengkap.pdf
└── scripts/
    ├── label_ai.py
    └── langkah4_analisis.py
```

**Documents**

- [Summary deck (PDF, Indonesian)](./docs/Sinyal_Awal_Persepsi_Netizen_terhadap_Pos_Indonesia.pdf)
- [Companion report: methods and full numbers (PDF, Indonesian)](./docs/Laporan_Pendamping_Metode_Proses_Analisis_dan_Angka_Lengkap.pdf)

**Scripts**

| Script | Purpose |
|---|---|
| [`scripts/label_ai.py`](./scripts/label_ai.py) | Labels from the third annotator (AI model), written before the human labels were opened. Sentiment, aspect codes (+ praise, - criticism), competitor mention and a short note per opinion. |
| [`scripts/langkah4_analisis.py`](./scripts/langkah4_analisis.py) | Inter-annotator reliability (Cohen's and Fleiss' Kappa), final labels by majority vote with documented tie decisions, and all descriptive statistics and tests. |

## Reproducing the analysis

The scripts are published for transparency. They **cannot run from this repository alone**, because the input data are excluded for privacy:

- `langkah4_analisis.py` reads `label_p2.xlsx`, `label_kahfi.xlsx` and `data_bersih_pos.csv` (annotator sheets and the cleaned tweet dataset).
- It writes results to an `analisis/` folder, which must exist before running.
- Requirements: Python 3, pandas, NumPy, SciPy, scikit-learn, openpyxl.

Run it from a working folder that holds the input files and `label_ai.py`.

## Data and privacy

Raw tweets, usernames, annotator sheets, the cleaned dataset and generated outputs that contain tweet text are excluded (see `.gitignore`) to respect user privacy and platform terms. No internal Pos Indonesia data is included.

## Author

**Ageng Windarto Jati** · [LinkedIn](https://www.linkedin.com/in/agengwindartojati/) · [Portfolio](https://github.com/gencWeze/Capstone-and-Project-Portfolio)
