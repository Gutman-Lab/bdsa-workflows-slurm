import json
import argparse
import subprocess
from pathlib import Path

def generate_sbatch_script(script_path, job_name, partition, gres, cpus, mem, time, command):
    with open(script_path, 'w') as f:
        f.write(f"""#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --output={script_path.with_suffix('.out')}
#SBATCH --error={script_path.with_suffix('.err')}
#SBATCH --partition={partition}
{f'#SBATCH --gres={gres}' if gres else ''}
#SBATCH --cpus-per-task={cpus}
#SBATCH --mem={mem}
#SBATCH --time={time}

set -euo pipefail
{command}
""")

def main(config_path):
    with open(config_path) as f:
        config = json.load(f)

    output_dir = Path(config["global"]["output_directory"])
    log_dir = output_dir / "slurm_logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    images_path = output_dir / config["step3"]["input_file"]
    with open(images_path) as f:
        images = json.load(f)

    results = []

    # Common env flags (headless + warnings + writable /tmp)
    common_env = (
        "-e MPLCONFIGDIR=/tmp/mpl "
        "-e XDG_CACHE_HOME=/tmp/xdg "
        "-e MPLBACKEND=Agg "
        "-e HOME=/tmp "
        "-e PYTHONWARNINGS=\"ignore:pkg_resources is deprecated as an API:UserWarning\" "
        "--tmpfs /tmp:rw,exec,nosuid,nodev "
    )

    for image in images:
        if not image.get("has_local_match"):
            continue

        local_path = Path(image["local_matches"][0])
        base_name  = local_path.stem

        seg_anot   = f"{base_name}.anot"        # segmentation anot
        ppc_anot   = f"{base_name}-ppc.anot"    # PPC anot (preferred)
        ppc_tiff   = f"{base_name}.tiff"        # conditional label image

        # ---------------- Step 3: Tissue segmentation (GPU) ----------------
        # Arg order preserved as you used:
        # "<slide>" GrayWhiteSegTest <tile> <stride> <batch> <num_workers> 0.5 --image_annotation ...
        step3_cmd = (
            f"docker run --rm --gpus all --network=host "
            f"--user $(id -u):$(id -g) "
            f"{common_env}"
            f"-v /wsi_archive:/wsi_archive "
            f"-v {output_dir}:/output "
            f"{config['step3']['docker_image']} "
            f"TissueCompartmentSegmentation "
            f"\"{local_path}\" "
            f"GrayWhiteSegTest "
            f"{config['step3']['tile_size']} "
            f"{config['step3']['stride']} "
            f"{config['step3']['batch_size']} "
            f"{config['step3']['num_workers']} "
            f"0.5 "
            f"--image_annotation \"/output/{seg_anot}\""
        )

        # ---------------- Step 4: PPC (CPU) ----------------
        # First run PPC (no TIFF) to produce /output/{base}-ppc.anot
        ppc_run_no_tiff = (
            f"docker run --rm --network=host "
            f"--user $(id -u):$(id -g) "
            f"{common_env}"
            f"-v /wsi_archive:/wsi_archive "
            f"-v {output_dir}:/output "
            f"{config['step4']['docker_image']} "
            f"PositivePixelCount "
            f"{config['step4']['ppc_parameters']['docname']} "
            f"\"{local_path}\" "
            f"{config['step4']['ppc_parameters']['hue_value']} "
            f"{config['step4']['ppc_parameters']['hue_width']} "
            f"{config['step4']['ppc_parameters']['saturation_minimum']} "
            f"{config['step4']['ppc_parameters']['intensity_upper_limit']} "
            f"{config['step4']['ppc_parameters']['intensity_weak_threshold']} "
            f"{config['step4']['ppc_parameters']['intensity_strong_threshold']} "
            f"{config['step4']['ppc_parameters']['intensity_lower_limit']} "
            f"/output/{seg_anot} "
            f"'' false 20 noToken noAPI "
            f"--image_annotation /output/{ppc_anot}"
        )

        # TIFF rerun (only if positives > 0)
        ppc_run_with_tiff = (
            f"docker run --rm --network=host "
            f"--user $(id -u):$(id -g) "
            f"{common_env}"
            f"-v /wsi_archive:/wsi_archive "
            f"-v {output_dir}:/output "
            f"{config['step4']['docker_image']} "
            f"PositivePixelCount "
            f"{config['step4']['ppc_parameters']['docname']} "
            f"\"{local_path}\" "
            f"{config['step4']['ppc_parameters']['hue_value']} "
            f"{config['step4']['ppc_parameters']['hue_width']} "
            f"{config['step4']['ppc_parameters']['saturation_minimum']} "
            f"{config['step4']['ppc_parameters']['intensity_upper_limit']} "
            f"{config['step4']['ppc_parameters']['intensity_weak_threshold']} "
            f"{config['step4']['ppc_parameters']['intensity_strong_threshold']} "
            f"{config['step4']['ppc_parameters']['intensity_lower_limit']} "
            f"/output/{seg_anot} "
            f"'' false 20 noToken noAPI "
            f"--image_annotation /output/{ppc_anot} "
            f"--outputLabelImage /output/{ppc_tiff}"
        )

        # Decide which .anot to parse: prefer PPC anot (has PPC stats), else seg anot
        # Use argv to avoid shell-quoting issues
        pos_check = (
            "ANOT_PATH=\""
            f"{(output_dir / ppc_anot)}"
            "\"\n"
            "if [ ! -f \"$ANOT_PATH\" ]; then ANOT_PATH=\""
            f"{(output_dir / seg_anot)}"
            "\"; fi\n"
            'echo "Reading anot: $ANOT_PATH"\n'
            "read -r POS WEAK STRONG <<< $(python3 - \"$ANOT_PATH\" <<'PY'\n"
            "import json, sys\n"
            "from pathlib import Path as P\n"
            "p = P(sys.argv[1])\n"
            "try:\n"
            "    d = json.loads(p.read_text())\n"
            "except Exception:\n"
            "    print('0 0 0'); sys.exit(0)\n"
            "def collect(x):\n"
            "    pos = weak = strong = 0\n"
            "    if isinstance(x, dict):\n"
            "        st = x.get('stats')\n"
            "        if isinstance(st, dict):\n"
            "            pos   += int(st.get('NumberPositive', 0) or 0)\n"
            "            weak  += int(st.get('NumberWeakPositive', 0) or 0)\n"
            "            strong+= int(st.get('NumberStrongPositive', 0) or 0)\n"
            "        for v in x.values():\n"
            "            p2,w2,s2 = collect(v)\n"
            "            pos += p2; weak += w2; strong += s2\n"
            "    elif isinstance(x, list):\n"
            "        for v in x:\n"
            "            p2,w2,s2 = collect(v)\n"
            "            pos += p2; weak += w2; strong += s2\n"
            "    return pos, weak, strong\n"
            "P,W,S = collect(d)\n"
            "print(P, W, S)\n"
            "PY\n"
            ")\n"
            'echo "Counts → Positive:$POS Weak:$WEAK Strong:$STRONG"\n'
        )

        step4_cmd = "\n".join([
            ppc_run_no_tiff,
            pos_check,
            'TOTAL=$(( ${POS:-0} + ${WEAK:-0} + ${STRONG:-0} ))',
            'echo "Total positives (weak+pos+strong): $TOTAL"',
            'if [ "$TOTAL" -gt 0 ]; then',
            '  echo "Positive pixels > 0 → generating TIFF"',
            f'  {ppc_run_with_tiff}',
            'else',
            '  echo "No positive pixels → skipping TIFF"',
            'fi'
        ])

        job_name   = f"bdsa_{base_name}"
        gpu_script = log_dir / f"{job_name}_gpu.sbatch"
        cpu_script = log_dir / f"{job_name}_cpu.sbatch"

        # Generate SLURM scripts
        generate_sbatch_script(
            gpu_script, f"{job_name}_gpu", "gpu", "gpu:1",
            12, "32G", "01:00:00", step3_cmd
        )
        generate_sbatch_script(
            cpu_script, f"{job_name}_cpu", "compute", None,
            16, "32G", "01:00:00", step4_cmd
        )

        # Submit Step 3
        print(f"Submitting GPU job: {gpu_script}")
        gpu_result = subprocess.run(["sbatch", str(gpu_script)], capture_output=True, text=True)
        if gpu_result.returncode != 0:
            print(f"Failed GPU submission: {gpu_result.stderr}")
            continue

        gpu_jobid = gpu_result.stdout.strip().split()[-1]

        # Submit Step 4 dependent on Step 3 success
        print(f"Submitting CPU job (afterok:{gpu_jobid}): {cpu_script}")
        cpu_result = subprocess.run(
            ["sbatch", f"--dependency=afterok:{gpu_jobid}", str(cpu_script)],
            capture_output=True, text=True
        )

        results.append({
            "image": image.get("name", base_name),
            "local_path": str(local_path),
            "seg_anot": str(output_dir / seg_anot),
            "ppc_anot": str(output_dir / ppc_anot),
            "ppc_tiff": str(output_dir / ppc_tiff),
            "gpu_sbatch": str(gpu_script),
            "cpu_sbatch": str(cpu_script),
            "gpu_jobid": gpu_jobid,
            "cpu_status": "submitted" if cpu_result.returncode == 0 else "failed",
            "cpu_message": cpu_result.stdout.strip() if cpu_result.returncode == 0 else cpu_result.stderr.strip()
        })

    result_path = output_dir / config["step3"]["output_file"]
    with open(result_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Submission results saved to {result_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="dsa_workflow_config.json")
    args = parser.parse_args()
    main(args.config)