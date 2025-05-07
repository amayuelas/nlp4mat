import os
import json
from tqdm import tqdm

from collections import Counter

def count_recipes(dir_path: str):
    recipe_count = 0
    total_files = 0
    material_categories = Counter()
    for root, dirs, files in tqdm(os.walk(dir_path)):
        if "filter.json" in files:
            total_files += 1
            file_path = os.path.join(root, "filter.json")
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if data.get("contains_recipe") == True:
                        recipe_count += 1
                        # check if it is a valid string 
                        if isinstance(data.get("material_category"), str):
                            material_categories[data.get("material_category")] += 1
                        else:
                            material_categories[data.get("uncategorized")] += 1

            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error reading {file_path}: {e}")

    print(f"Total filter.json files found: {total_files}")
    print(f"Number of files with contains_recipe=True: {recipe_count}")
    print(f"Material categories: {material_categories}")
    # sum of all values in material_categories
    print(f"Sum of all values in material_categories: {sum(material_categories.values())}")

if __name__ == "__main__":
    dir_path = "../data_arxiv/cond-mat/parsed/2002"
    count_recipes(dir_path) 