# Format And Reproducibility Check

## Paper Limits

- Total PDF pages: 19.
- Main-text pages: 8, from PDF page 5 to page 12.
- Main-text length estimate from Poppler text extraction: 3,783 Chinese characters, 314 English tokens, and 219 numeric tokens; total rough count 4,316, below 8,000.

## Format Basis

- Template: `docs/paper/Template_ECNU_Undergraduate_202505/ecnuundergraduate.cls`.
- Page size: A4.
- Margins: left 2.6 cm, right 2.6 cm, top 2.8 cm, bottom 2.5 cm.
- Body requirement noted by template: Songti, small fourth size, 25 pt line spacing.
- Header/footer: centered report title in header and centered page number in footer.
- Headings: chapter, section, and subsection styles are controlled by the ECNU template.
- Captions: table and figure captions are numbered by chapter and rendered through the template caption style.
- Visual check: rendered pages 1, 5, 12, 13, 14, 15, and 17 were inspected; no overlap, clipped text, or broken figure/table rendering was found.

## Data And Modeling Checks

- The local project data directory contains the full raw data under `data/raw/`; raw data is excluded from GitHub because of its size.
- Data inventory reports 773 training wells, 3 visible test wells, and 14,151 submission rows.
- Model evaluation uses well-level GroupKFold out-of-fold results. The visible test wells are used for format checks only.
- Hyperparameter selection and model comparison are based on OOF validation, not the Kaggle hidden test set.
- Main numeric results in the paper and retained CSV files are rounded to three decimals.

## Result Mapping

- Paper data overview: `results/data_overview.csv`.
- Main model comparison: `results/model_comparison.csv`.
- Gating and alpha comparison: `results/alpha_search.csv` and `results/candidate_selection.csv`.
- Ensemble and postprocess comparison: `results/ensemble_comparison.csv` and `results/postprocess_comparison.csv`.
- Final submission file: `results/final_submission.csv`.
