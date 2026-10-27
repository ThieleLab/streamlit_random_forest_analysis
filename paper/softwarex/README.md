# FastForest — SoftwareX manuscript

`main.tex` is the Original Software Publication draft (v0.1, 2026-10-17), written from the Phase 3 benchmark in
`results/summary/`. It is a reading copy in the `article` class; at submission the body moves into Elsevier's
`elsarticle` template (`\journal{SoftwareX}`), which only changes the preamble and the title block.

`make_figures.py` builds the paper's figures from `results/summary/` (`per_run.csv`, `stability.csv`,
`recovery.csv`):

    python3 paper/softwarex/make_figures.py results/summary paper/softwarex/figures

Figures: `fig2_reduction_vs_accuracy` (the seven tables with repeated splits), `fig3_stability`,
`fig4_madelon_recovery`, `figS1_half_tables` (the six single-seed halves). Figure 1 (the pipeline) is TikZ in
`main.tex`. Tables 2–4 are typed from `summary.csv`, `datasets.csv` and `scalability.csv`; the numbers in the text
come from `CHECKPOINT.md` and were re-derived from `summary.csv`.

Compile with `latexmk -pdf main.tex` (pdfLaTeX; no bibliography file, the reference list is embedded).
Red square-bracket notes are for the authors: version tag and Zenodo DOI, the hosted app, funding, the
prepared-table deposit, the test count at release, and the CrossRef check of every reference.

Upload to Overleaf: New Project → Upload Project → the zip of this folder (`main.tex` + `figures/`).
