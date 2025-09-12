import argparse
import subprocess
import sys

def run_python_script(script_path, config_path):
    print(f"\nRunning {script_path}...")
    result = subprocess.run(
        [sys.executable, script_path, "--config", config_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Error in {script_path}:\n{result.stderr}")
        sys.exit(1)
    print(result.stdout)

def main():
    parser = argparse.ArgumentParser(description="Run full DSA workflow pipeline.")
    parser.add_argument("--config", default="dsa_workflow_config.json", help="Path to config JSON file")
    args = parser.parse_args()

    # Step 1
    run_python_script("Step1.Fetch_DSA_ImageSet.py", args.config)
    # Step 2
    run_python_script("Step2.Verify_Local_Files.py", args.config)
   
    # Step 3+4 - mearge and run combined SLURM script
    run_python_script("Step3_4.Run_Combined_SLURM-tiff.py", args.config)

    print("\nWorkflow completed successfully!")

if __name__ == "__main__":
    main()
