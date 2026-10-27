# Reference check — FastForest SoftwareX draft v0.1

Every entry of the reference list of `main.tex` (tag `paper-v0.1`, L304–314) checked against
CrossRef on 2026-10-27: `api.crossref.org/works/<DOI>` for the entries with a DOI, a
bibliographic query (`/works?query.bibliographic=`) for the others; where CrossRef has no record,
the publisher's own page. The reference list is unchanged; this file only reports.

Fields: ✓ confirmed, ✗ differs, — not given in the paper, ? could not be confirmed.

## Summary

- 11 entries; 9 are cited in the text, **2 are never cited** (`breiman2001`, `kalousis2007`).
- 7 found in CrossRef by DOI and 1 more (Tibshirani 1996) by its DOI, which the paper omits.
- 3 are not in CrossRef (JMLR and NeurIPS proceedings have no DOIs). Pedregosa 2011 is confirmed
  in full from the JMLR page. Louppe 2013 and Guyon 2004 are confirmed from the NeurIPS proceedings
  pages except for their **page ranges**, which the official records leave empty.
- **Differs:** R1 (APOLLO) — the registered title has no "APOLLO:" prefix; volume, issue and article
  number are missing (the red note already says so).
- **Not confirmed:** pages of R2 (Kursa 2010: CrossRef has no page field and the JSS site did
  not answer), R7 (Louppe 2013) and R9 (Guyon 2004).

## Entries

| # | key | cited in text | as printed | CrossRef / publisher record | DOI | title | year | volume (issue) | pages | authors | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | heinken2025 | 6× | Heinken A, Hulshof TO, et al. APOLLO: a genome-scale metabolic reconstruction resource of 247,092 diverse human microbes spanning multiple continents, age groups, and body sites. Cell Syst 2025. doi:10.1016/j.cels.2025.101196 | CrossRef 10.1016/j.cels.2025.101196: "A genome-scale metabolic reconstruction resource of 247,092 diverse human microbes spanning multiple continents, age groups, and body sites", Cell Systems, issued 2025-02, vol 16, issue 2, article 101196; 22 authors, Heinken A, Hulshof TO (Timothy Otto), Nap B, … Thinnes CC, Thiele I | ✓ | ✗ registered title has no "APOLLO:" prefix | ✓ | — (16(2)) | — (article 101196) | ✓ first two; list incomplete (22 authors, last Thiele I) | **differs**: title prefix; add 16(2):101196 and the authors |
| R2 | kursa2010 | 2× | Kursa MB, Rudnicki WR. Feature selection with the Boruta package. J Stat Softw 2010;36(11):1–13. doi:10.18637/jss.v036.i11 | CrossRef 10.18637/jss.v036.i11: "Feature Selection with the Boruta Package", Journal of Statistical Software, 2010, vol 36, issue 11; no page field; Kursa M, Rudnicki W | ✓ | ✓ | ✓ | ✓ 36(11) | ? (not in CrossRef; jstatsoft.org timed out) | ✓ | confirmed except pages |
| R3 | guyon2002 | 2× | Guyon I, Weston J, Barnhill S, Vapnik V. Gene selection for cancer classification using support vector machines. Mach Learn 2002;46:389–422. doi:10.1023/A:1012487302797 | CrossRef 10.1023/a:1012487302797: "Gene Selection for Cancer Classification using Support Vector Machines", Machine Learning, issued 2002-01, vol 46, issue 1–3, pages 389–422; Guyon I, Weston J, Barnhill S, Vapnik V | ✓ | ✓ | ✓ | ✓ 46 (issue 1–3 not printed) | ✓ | ✓ | confirmed |
| R4 | tibshirani1996 | 2× | Tibshirani R. Regression shrinkage and selection via the lasso. J R Stat Soc B 1996;58:267–288. | CrossRef 10.1111/j.2517-6161.1996.tb02080.x: "Regression Shrinkage and Selection Via the Lasso", Journal of the Royal Statistical Society Series B: Statistical Methodology, 1996, vol 58, issue 1, pages 267–288; Tibshirani R | — (exists: 10.1111/j.2517-6161.1996.tb02080.x) | ✓ | ✓ | ✓ 58 (issue 1 not printed) | ✓ | ✓ | confirmed; DOI can be added |
| R5 | pedregosa2011 | 1× | Pedregosa F, Varoquaux G, Gramfort A, et al. Scikit-learn: machine learning in Python. J Mach Learn Res 2011;12:2825–2830. | Not in CrossRef (JMLR assigns no DOIs; the query returned only unrelated book chapters). JMLR page jmlr.org/papers/v12/pedregosa11a.html: "Scikit-learn: Machine Learning in Python", Pedregosa F, Varoquaux G, Gramfort A, Michel V, … ; 12(85):2825−2830, 2011 | — (none exists) | ✓ | ✓ | ✓ 12 (number 85 not printed) | ✓ | ✓ | confirmed from the publisher page |
| R6 | breiman2001 | **never** | Breiman L. Random forests. Mach Learn 2001;45:5–32. doi:10.1023/A:1010933404324 | CrossRef 10.1023/a:1010933404324: "Random Forests", Machine Learning, issued 2001-10, vol 45, issue 1, pages 5–32; Breiman L | ✓ | ✓ | ✓ | ✓ 45 (issue 1 not printed) | ✓ | ✓ | confirmed; **not cited in the text** |
| R7 | louppe2013 | 1× | Louppe G, Wehenkel L, Sutera A, Geurts P. Understanding variable importances in forests of randomized trees. Adv Neural Inf Process Syst 2013;26:431–439. | Not in CrossRef (the query returned unrelated items). NeurIPS proceedings page and official BibTeX: "Understanding variable importances in forests of randomized trees", Louppe G, Wehenkel L, Sutera A, Geurts P, Advances in Neural Information Processing Systems 26 (NIPS 2013), Curran Associates; `pages = {}` | — (none exists) | ✓ | ✓ | ✓ 26 | ? (empty in the official record) | ✓ | confirmed except pages |
| R8 | mcinnes2018 | 1× | McInnes L, Healy J, Saul N, Großberger L. UMAP: uniform manifold approximation and projection. J Open Source Softw 2018;3(29):861. doi:10.21105/joss.00861 | CrossRef 10.21105/joss.00861: "UMAP: Uniform Manifold Approximation and Projection", Journal of Open Source Software, issued 2018-09-02, vol 3, issue 29, page 861; McInnes L, Healy J, Saul N, Großberger L | ✓ | ✓ | ✓ | ✓ 3(29) | ✓ 861 | ✓ | confirmed |
| R9 | guyon2004 | 1× | Guyon I, Gunn S, Ben-Hur A, Dror G. Result analysis of the NIPS 2003 feature selection challenge. Adv Neural Inf Process Syst 2004;17:545–552. | Not in CrossRef. NeurIPS proceedings page and official BibTeX: "Result Analysis of the NIPS 2003 Feature Selection Challenge", Guyon I, Gunn S, Ben-Hur A, Dror G, Advances in Neural Information Processing Systems 17 (NIPS 2004), MIT Press; `pages = {}`. CrossRef has a related chapter by the same authors: "Design and Analysis of the NIPS2003 Challenge", Studies in Fuzziness and Soft Computing, pages 237–263, doi:10.1007/978-3-540-35488-8_10 (issue date not registered) | — (none exists) | ✓ | ✓ | ✓ 17 | ? (empty in the official record) | ✓ | confirmed except pages |
| R10 | stiglic2010 | 1× | Stiglic G, Kokol P. Stability of ranked gene lists in large microarray analysis studies. J Biomed Biotechnol 2010;2010:616358. doi:10.1155/2010/616358 | CrossRef 10.1155/2010/616358: "Stability of Ranked Gene Lists in Large Microarray Analysis Studies", Journal of Biomedicine and Biotechnology, 2010, vol 2010, pages 1–9; Stiglic G, Kokol P | ✓ | ✓ | ✓ | ✓ 2010 | ✓ article 616358 (= DOI suffix; CrossRef gives pages 1–9) | ✓ | confirmed |
| R11 | kalousis2007 | **never** | Kalousis A, Prados J, Hilario M. Stability of feature selection algorithms: a study on high-dimensional spaces. Knowl Inf Syst 2007;12:95–116. doi:10.1007/s10115-006-0040-8 | CrossRef 10.1007/s10115-006-0040-8: "Stability of feature selection algorithms: a study on high-dimensional spaces", Knowledge and Information Systems, online 2006-12-01, print 2007-05, vol 12, issue 1, pages 95–116; Kalousis A, Prados J, Hilario M | ✓ | ✓ | ✓ (print year) | ✓ 12 (issue 1 not printed) | ✓ | ✓ | confirmed; **not cited in the text** |

## Notes for the interrogation

- `breiman2001` is listed but the random forest itself is never cited in the text; `kalousis2007`
  (the stability measure) is listed but the stability paragraph (§3.2, Fig. 3) does not cite it.
- The paper prints no DOI for Tibshirani 1996 although one exists, and none can exist for
  Pedregosa 2011, Louppe 2013 or Guyon 2004.
- Issue numbers are printed for some journals (J Stat Softw, JOSS) and not for others (Machine
  Learning, JRSS B, KAIS); SoftwareX's style decides at the elsarticle port.
