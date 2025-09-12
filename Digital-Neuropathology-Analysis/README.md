# Unified Digital Neuropathology Analysis
This repository contains a **Jupyter notebook pipeline** for extending **Dunn et al. (2015)** with modern machine learning and digital pathology tools.  
The workflow parses `*-ppc.anot` files (JSON annotation outputs from Positive Pixel Counting), computes derived metrics, performs statistical & ML analyses, and generates tables, figures, and reports.
---
## 📂 Directory Structure
```
bdsa-workflows-slurm/
├── output/        # Input folder containing *-ppc.anot JSON files
├── results/       # All outputs are written here
│   ├── tables/    # CSV and Excel exports (metrics, summaries, reports)
│   ├── advanced_visualizations/   # Figures (SPPP plots, heatmaps, PCA, RF importances)
│   └── extended_analysis_report.txt
└── Unified_Neuropathology_Notebook.ipynb   # Jupyter notebook code
```
---

## 🔄 Workflow Overview

## Features

### 1. **Data Parsing**
- Reads all `*-ppc.anot` files from `/output`.
- Handles schema variations (`stats`, `ppc_stats`, `performance`).
- Extracts pixel counts, intensity metrics, and processing times.

### 2. **Derived Metrics**
- **SPPP**: Strong Positive Pixel Percent  
- **Positivity Rate**  
- **Strong Ratio**  
- **ABC Scoring** (Braak, CERAD, Thal, ABC level)

### 3. **Statistical Analysis**
- ANOVA (SPPP across regions)  
- Correlation matrix  
- OLS regression (guarded)

### 4. **Tables / Exports**
- Per-image metrics CSV  
- Region summary CSV  
- Correlation matrix CSV  
- Excel export (if available)

### 5. **Visualizations**
- Boxplots (SPPP by region)  
- Heatmaps (correlation)  
- Efficiency scatter plots  

### 6. **Advanced Analyses**
- PCA (scatter + variance explained)  
- RandomForest Regressor (predict SPPP)  
- RandomForest Classifier (predict `abc_level`, with confusion matrices)

### 7. **Report**
- `extended_analysis_report.txt` summarizing dataset, stats, key results, and outputs

---

## References

- Dunn, W. D., et al. (2015). *Applicability of digital analysis and imaging technology in neuropathology assessment*. Neuropathology, 36(3), 270–282.  
- Neltner, J. H., et al. (2012). *Digital pathology and image analysis for robust high-throughput quantitative assessment of Alzheimer disease neuropathologic changes*. J Neuropathol Exp Neurol, 71(12), 1075–1085.  
- Kapasi, A., et al. (2023). *High-throughput digital quantification of Alzheimer disease pathology*. J Neuropathol Exp Neurol, 82(12), 976–986.  
- Gonzalez, A. D., et al. (2025). *Digital pathology in tau research: A comparison of QuPath and HALO*. J Neuropathol Exp Neurol, 84(8), 692–706.  
