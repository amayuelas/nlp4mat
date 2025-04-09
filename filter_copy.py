import os
import json
import shutil
from pathlib import Path

def filter_and_copy_folders(input_folder, output_folder):
    """
    Copy subfolders to output_folder if their filter.json contains 'contains_recipe': True
    
    Args:
        input_folder (str): Path to the input folder containing subfolders
        output_folder (str): Path to the output folder where filtered subfolders will be copied
    """
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Get all subfolders in the input folder
    input_path = Path(input_folder)
    subfolders = [f for f in input_path.iterdir() if f.is_dir()]
    cnt = 0
    for subfolder in subfolders:
        filter_json_path = subfolder / 'filter.json'
        
        # Check if filter.json exists
        if filter_json_path.exists():
            try:
                # Read and parse filter.json
                with open(filter_json_path, 'r') as f:
                    filter_data = json.load(f)
                # Check if contains_recipe is True
                if bool(filter_data['contains_recipe']) == True:
                    # Copy the entire subfolder to output
                    dest_path = Path(output_folder) / subfolder.name
                    shutil.copytree(subfolder, dest_path, dirs_exist_ok=True)
                    print(f"contains_recipe: {filter_data['contains_recipe']} | Copied {subfolder.name} to {output_folder}")
                    cnt += 1
            except json.JSONDecodeError:
                print(f"Error: Invalid JSON in {filter_json_path}")
            except Exception as e:
                print(f"Error processing {subfolder.name}: {str(e)}")

    print(f"Copied {cnt} folders to {output_folder}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Filter and copy folders based on filter.json content')
    parser.add_argument('input_folder', help='Path to the input folder containing subfolders')
    parser.add_argument('output_folder', help='Path to the output folder where filtered subfolders will be copied')
    
    args = parser.parse_args()
    
    filter_and_copy_folders(args.input_folder, args.output_folder) 