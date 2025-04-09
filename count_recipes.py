import os
import json

def count_recipes(dir_path: str):
    recipe_count = 0
    total_files = 0

    for root, dirs, files in os.walk(dir_path):
        if "filter.json" in files:
            total_files += 1
            file_path = os.path.join(root, "filter.json")
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if data.get("contains_recipe") == True:
                        recipe_count += 1

            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error reading {file_path}: {e}")

    print(f"Total filter.json files found: {total_files}")
    print(f"Number of files with contains_recipe=True: {recipe_count}")

if __name__ == "__main__":
    dir_path = "data1/parsed/cond-mat/2025"
    count_recipes(dir_path) 