import os
from pathlib import Path
from llm import LLM
import json

def analyze_article(text: str, llm: LLM) -> dict:
    prompt = f"""Analyze the following text and answer the questions in JSON format:
    
{text}

Questions:
1. Does it contain a material synthesis recipe? (Answer with "Yes" or "No")
2. If yes, what is the material type? (Answer with the specific material type or "N/A" if no recipe)

Format your response as a JSON object with the following structure:
{{
    "contains_recipe": "Yes/No",
    "material_type": "material type or N/A"
}}
"""
    
    response = llm.generate_text(prompt, response_format={"type": "json_object"})
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"contains_recipe": "Error", "material_type": "Error parsing response"}

def process_folder(folder_path: str):
    # Initialize LLM
    llm = LLM(model_name="mistral-large-latest", provider="mistral")
    
    # Get all subfolders
    base_path = Path(folder_path)
    results = {}
    
    for subfolder in base_path.iterdir():
        if subfolder.is_dir():
            text_file = subfolder / "text.txt"
            if text_file.exists():
                with open(text_file, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                # Analyze the text
                analysis = analyze_article(text, llm)
                results[subfolder.name] = analysis
    
    # Save results to a JSON file
    output_file = base_path / "analysis_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print(f"Analysis complete. Results saved to {output_file}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze text files for material synthesis recipes')
    parser.add_argument('folder_path', help='Path to the folder containing subfolders with text.txt files')
    
    args = parser.parse_args()
    process_folder(args.folder_path) 