import os
import json

def count_recipes():
    base_dir = "data/parsed/cond-mat"
    recipe_count = 0
    total_files = 0

    for root, dirs, files in os.walk(base_dir):
        if "filter.json" in files:
            total_files += 1
            file_path = os.path.join(root, "filter.json")
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if data.get("contains_recipe") == "True":
                        recipe_count += 1
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error reading {file_path}: {e}")

    print(f"Total filter.json files found: {total_files}")
    print(f"Number of files with contains_recipe=True: {recipe_count}")

if __name__ == "__main__":
    count_recipes() 