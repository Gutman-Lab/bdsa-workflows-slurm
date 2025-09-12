import os
import json
import argparse

def check_file_access(file_path, checks):
    return {
        "readable": os.access(file_path, os.R_OK) if checks.get("check_readable", True) else None,
        "writable": os.access(file_path, os.W_OK) if checks.get("check_writable", False) else None,
        "executable": os.access(file_path, os.X_OK) if checks.get("check_executable", False) else None
    }

def main(config_path):
    with open(config_path) as f:
        config = json.load(f)

    output_dir = config['global']['output_directory']
    image_list_path = os.path.join(output_dir, config['step2']['input_file'])
    store_path = config['global']['local_file_store']
    file_checks = config['step2'].get('file_checks', {})

    with open(image_list_path) as f:
        images = json.load(f)

    print(f"Scanning local file store at {store_path}...")
    local_files = {}
    for root, _, files in os.walk(store_path):
        for fname in files:
            fname_lower = fname.lower()
            local_files.setdefault(fname_lower, []).append(os.path.join(root, fname))

    print(f"Matching {len(images)} images to local files...")
    enriched = []
    for img in images:
        img_name_lower = img['name'].lower()
        matched_paths = local_files.get(img_name_lower, [])

        img.update({
            'local_matches': matched_paths,
            'has_local_match': bool(matched_paths),
            'is_duplicate': len(matched_paths) > 1,
            'match_count': len(matched_paths),
            'accessibility': []
        })

        for path in matched_paths:
            access_info = check_file_access(path, file_checks)
            img['accessibility'].append({
                "path": path,
                **access_info
            })

        enriched.append(img)

    output_path = os.path.join(output_dir, config['step2']['output_file'])
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(enriched, f, indent=2)
    print(f"Accessibility results saved to {output_path} ({len(enriched)} records)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='dsa_workflow_config.json')
    args = parser.parse_args()
    main(args.config)
