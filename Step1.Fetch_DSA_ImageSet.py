import girder_client
import os
import json
import argparse

def load_config(config_path):
    with open(config_path, 'r') as f:
        return json.load(f)

def get_dsa_client(config):
    dsa_url = config["global"]["dsa_server_url"]
    dsa_key = config["global"].get("dsa_api_key")

    gc = girder_client.GirderClient(apiUrl=dsa_url)
    if dsa_key:
        gc.authenticate(apiKey=dsa_key)
    else:
        raise ValueError("No authentication method provided in config.")
    return gc

def get_all_items(gc, folder_id):
    all_items = []
    items = gc.get(f"/item?folderId={folder_id}")
    all_items.extend(items)

    subfolders = gc.get(f"/folder?parentType=folder&parentId={folder_id}")
    for f in subfolders:
        all_items.extend(get_all_items(gc, f['_id']))

    return all_items

def build_item_path(gc, item):
    path_parts = [item['name']]
    folder_id = item['folderId']
    while folder_id:
        folder = gc.get(f"/folder/{folder_id}")
        path_parts.insert(0, folder['name'])
        parent_type = folder.get('parentType')
        parent_id = folder.get('parentId')

        if parent_type == 'folder':
            folder_id = parent_id
        elif parent_type == 'collection':
            collection = gc.get(f"/collection/{parent_id}")
            path_parts.insert(0, collection['name'])
            break
        else:
            break
    return '/'.join(path_parts)

def save_image_list(images, config):
    output_path = os.path.join(config["global"]["output_directory"], config["step1"]["output_file"])
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(images, f, indent=2)
    print(f"Saved {len(images)} images to {output_path}")

def main(config_path):
    config = load_config(config_path)
    gc = get_dsa_client(config)

    root_folder_id = config["step1"]["root_folder_id"]
    stain_id_filter = config["step1"]["stainID"]
    max_images = config["step1"].get("max_images", 200)

    print(f"Recursively fetching all items under folder {root_folder_id}...")
    all_items = get_all_items(gc, root_folder_id)
    print(f"Total items found recursively: {len(all_items)}")

    print(f"\nFiltering items with npSchema.stainID='{stain_id_filter}'...")
    filtered = []
    for item in all_items:
        meta = item.get('meta', {})
        np_schema = meta.get('npSchema', {})
        if np_schema.get('stainID') == stain_id_filter:
            filtered.append(item)
        if len(filtered) >= max_images:
            break

    print(f"Filtered items count: {len(filtered)}")
    for i, item in enumerate(filtered):
        try:
            item_path = build_item_path(gc, item)
            item['fullPath'] = item_path
            print(f"{i+1}. Name: {item['name']}, ID: {item['_id']}, Path: {item_path}")
        except Exception as e:
            print(f"Error building path for item {item['name']} (ID: {item['_id']}): {e}")

    save_image_list(filtered, config)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='dsa_workflow_config.json')
    args = parser.parse_args()
    main(args.config)
