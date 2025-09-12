# BDSA Workflows

This repository contains workflows for processing whole slide images (WSIs) with **SLURM + Docker** on HPC.

---

## Prerequisites

```bash
docker build -t neurotk_docker:latest .
```
(Cluster nodes already have the required Docker images installed.)

---

## Workflow Overview

The workflow processes WSIs through multiple steps, configured via `dsa_workflow_config.json`:

- **Step 1:** Fetch images from DSA  
- **Step 2:** Verify local file matches and accessibility  
- **Step 3:** Run tissue segmentation in GPU-based Docker container  
- **Step 4:** Run Positive Pixel Count (PPC) in CPU-based Docker container  
  - **NEW:** Generates a TIFF label image *only if positive pixels are detected*  

---

## Quick Start

Clone the repo:

```bash
git clone --recursive https://github.com/Gutman-Lab/bdsa-workflows-slurm.git
cd bdsa-workflows-slurm
```

Create and activate a private environment:

```bash
python3 -m venv .env
source .env/bin/activate
pip install -r requirements.txt
```

Update `dsa_workflow_config.json` with your **output path** and **DSA credentials**:

```json
{
  "global": {
    "output_directory": "/nashome/youruser/bdsa-output",
    "dsa_api_key": "your-api-key",
    "dsa_server_url": "https://your-dsa",
    ...
  }
}
```

Run the workflow:

```bash
python run_workflow.py --config dsa_workflow_config.json
```

---

## Running Individual Steps

Each step can be run independently:

```bash
# Step 1: Fetch DSA Image Set
python Step1.Fetch_DSA_ImageSet.py --config dsa_workflow_config.json

# Step 2: Verify Local Files
python Step2.Verify_Local_Files.py --config dsa_workflow_config.json

# Step 3 + 4: Combined SLURM pipeline (segmentation + PPC with conditional TIFF)
python Step3_4.Run_Combined_SLURM-tiff.py --config dsa_workflow_config.json
```

---

## Configuration (dsa_workflow_config.json)

### Global Settings (`global`)
- `output_directory` → Workflow outputs
- `dsa_api_key`, `dsa_server_url`, `dsa_username`, `dsa_password`
- `local_file_store` → Path to local WSIs

### Step 1: Fetch Images (`step1`)
- `root_folder_id` → DSA folder ID
- `stainID` → Stain filter (e.g. `"aBeta"`)
- `output_file` → JSON list of selected images
- `max_images` → Limit number of images

### Step 2: Verify Local Files (`step2`)
- `input_file` → From step 1
- `output_file` → Accessibility results
- `check_readable`, `check_writable`, `check_executable`

### Step 3: Tissue Segmentation (`step3`)
- `input_file` → From step 2
- `output_file` → Segmentation results
- `docker_image` → Segmentation Docker image
- `tile_size`, `stride`, `batch_size`, `num_workers`
- `docker_mounts` → Host ↔ container mappings

### Step 4: Positive Pixel Count (`step4`)
- `input_file` → From step 3
- `output_file` → PPC results
- `docker_image` → PPC Docker image
- `ppc_parameters`:  
  - `docname`
  - `hue_value`, `hue_width`
  - `saturation_minimum`
  - `intensity_upper_limit`, `intensity_weak_threshold`, `intensity_strong_threshold`, `intensity_lower_limit`
- `num_workers`, `num_threads_per_worker`
- **Conditional TIFF output**:  
  - TIFF generated **only if total positives > 0** (`NumberPositive + Weak + Strong`)  

### Filters (`filters`)
- `min_size_mb` → Minimum WSI size
- `allowed_extensions` → e.g. `.svs`, `.ndpi`, `.tif`

---

## Notes

- Each image generates **two SLURM jobs**:  
  1 GPU job for segmentation + 1 CPU job for PPC.  
- With large batches (e.g. 500 slides), check your cluster’s job submission limits.  
- Logs are stored under `slurm_logs/`.  
- Outputs:  
  - `{slide}.anot` → Segmentation annotation  
  - `{slide}-ppc.anot` → PPC annotation (with pixel counts)  
  - `{slide}.tiff` → **Only if positives detected**

---