import os
from pathlib import Path
from llm import LLM
from tqdm import tqdm
import json
from typing import List, Dict
import tiktoken

def get_token_count(text: str, encoding_name: str = "cl100k_base") -> int:
    """Get the number of tokens in a text using tiktoken."""
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(text))

def split_text_into_chunks(text: str, max_tokens: int = 120000) -> List[str]:
    """Split text into chunks based on token count, trying to break at sentence boundaries."""
    encoding = tiktoken.get_encoding("cl100k_base")
    sentences = text.split('. ')
    chunks = []
    current_chunk = []
    current_token_count = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        sentence_token_count = len(encoding.encode(sentence))
        
        if current_token_count + sentence_token_count > max_tokens and current_chunk:
            # Current chunk is full, save it and start a new one
            chunks.append('. '.join(current_chunk) + '.')
            current_chunk = [sentence]
            current_token_count = sentence_token_count
        else:
            current_chunk.append(sentence)
            current_token_count += sentence_token_count
    
    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append('. '.join(current_chunk) + '.')
    
    return chunks

def analyze_article(text: str, llm: LLM) -> dict:
    # Split text into chunks if it's too large
    chunks = split_text_into_chunks(text)
    results = []
    
    for chunk in chunks:
        prompt = f"""Analyze the following text and answer the questions in JSON format:
        
{chunk}

Questions:
1. Does it contain a material synthesis recipe? (Answer with "Yes" or "No")
2. If yes, what is the material type? (Answer with the specific material type or "N/A" if no recipe)

Format your response as a JSON object with the following structure:
{{
    "contains_recipe": "True/False",
    "material_type": "material type or N/A"
}}
"""
        
        response = llm.generate_text(prompt, response_format={"type": "json_object"})
        try:
            results.append(json.loads(response))
        except json.JSONDecodeError:
            results.append({"contains_recipe": "Error", "material_type": "Error parsing response"})
    
    # Merge results from all chunks
    final_result = {
        "contains_recipe": "False",
        "material_type": "N/A"
    }
    
    # If any chunk contains a recipe, mark as True
    for result in results:
        if result["contains_recipe"] == "True":
            final_result["contains_recipe"] = "True"
            # Use the first non-N/A material type found
            if result["material_type"] != "N/A":
                final_result["material_type"] = result["material_type"]
                break
    
    return final_result

def process_folder(folder_path: str):
    # Initialize LLM
    llm = LLM(model_name="mistral-large-latest", provider="mistral")
    
    # Get all subfolders
    base_path = Path(folder_path)
    
    for subfolder in tqdm(list(base_path.iterdir()), desc="Processing folders"):
        if subfolder.is_dir():
            text_file = subfolder / "text.txt"
            if text_file.exists():
                with open(text_file, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                # Analyze the text
                analysis = analyze_article(text, llm)
                
                # Save results to filter.json in the subfolder
                output_file = subfolder / "filter.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(analysis, f, indent=2)
    
    print(f"Analysis complete. Results saved in filter.json files within each subfolder")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze text files for material synthesis recipes')
    parser.add_argument('folder_path', help='Path to the folder containing subfolders with text.txt files')
    
    args = parser.parse_args()
    process_folder(args.folder_path) 