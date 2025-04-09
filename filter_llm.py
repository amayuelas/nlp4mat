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

def analyze_article(text: str, client: LLM) -> dict:
    """Analyzes a text using an LLM to check for material synthesis recipes."""
    # Split text into chunks if it's too large
    chunks = split_text_into_chunks(text)
    results = []
    
    # Use tqdm for progress bar over chunks if there are multiple chunks
    chunk_iterator = tqdm(chunks, desc="Analyzing text chunks", leave=False) if len(chunks) > 1 else chunks
    
    for chunk in chunk_iterator:
        prompt = f"""Analyze the following text and answer the questions in JSON format:


{chunk}

Questions:
1. Does it contain a material synthesis recipe? (Answer with true or false)
2. If yes, what is the material type? (Answer with the specific material type or "N/A" if no recipe)

Format your response as a JSON object with the following structure:
{{
    "contains_recipe": true/false,
    "material_type": "material type or N/A"
}}
"""
        
        response = client.generate_text(prompt, response_format={"type": "json_object"})
        try:
            # Attempt to parse the response, handling potential leading/trailing whitespace or markdown code blocks
            response_cleaned = response.strip().strip('```json').strip('```').strip()
            results.append(json.loads(response_cleaned))
        except json.JSONDecodeError:
            print(f"Warning: Failed to decode JSON response: {response}")
            results.append({"contains_recipe": False, "material_type": "Error parsing response"})
    
    # Merge results from all chunks
    final_result = {
        "contains_recipe": False,
        "material_type": "N/A"
    }
    
    # If any chunk contains a recipe, mark as True
    for result in results:
        if result.get("contains_recipe") is True:
            final_result["contains_recipe"] = True
            # Use the first non-N/A material type found
            if result.get("material_type") != "N/A":
                final_result["material_type"] = result["material_type"]
                break # Stop once we found the first recipe and material

    return final_result

def process_directory(folder_path: str, client: LLM):
    """Processes all text.txt files in subdirectories of the given folder."""
    base_path = Path(folder_path)
    subfolders = [f for f in base_path.iterdir() if f.is_dir()]
    
    print(f"Found {len(subfolders)} subfolders to process.")
    
    for subfolder in tqdm(subfolders, desc="Processing subfolders"):
        text_file = subfolder / "text.txt"
        output_file = subfolder / "filter.json"
        
        # if output_file.exists():
        #     print(f"Skipping {subfolder.name}, filter.json already exists.")
        #     continue

        if text_file.exists():
            try:
                with open(text_file, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                # Analyze the text
                print(f"Analyzing {text_file}...")
                analysis = analyze_article(text, client)
                
                # Save results to filter.json in the subfolder
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(analysis, f, indent=2)
                print(f"Saved analysis to {output_file}")

            except Exception as e:
                print(f"Error processing {text_file}: {e}")
        else:
            print(f"Warning: text.txt not found in {subfolder.name}")
    
    print(f"Directory analysis complete. Results saved in filter.json files within each processed subfolder.")

def process_single_file(file_path: str, client: LLM):
    """Processes a single text file."""
    input_path = Path(file_path)
    output_path = input_path.parent / 'filter.json'

    if not input_path.name.endswith('.txt'):
        print(f"Error: Input file must be a .txt file. Got: {input_path.name}")
        return
        
    if output_path.exists():
        print(f"Skipping {input_path.name}, {output_path.name} already exists.")
        return

    print(f"Processing single file: {input_path}...")
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Analyze the text
        analysis = analyze_article(text, client)
        
        # Save results to filter.json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2)
        print(f"Analysis complete. Results saved to {output_path}")
    except FileNotFoundError:
        print(f"Error: Input file not found: {input_path}")
    except Exception as e:
        print(f"Error processing {input_path}: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze text file(s) for material synthesis recipes.')
    parser.add_argument('input_path', help='Path to a single .txt file or a folder containing subfolders with text.txt files')
    
    args = parser.parse_args()
    input_path = args.input_path

    # Initialize LLM once
    try:
        client = LLM(model_name="mistralai/Mistral-Small-3.1-24B-Instruct-2503", provider="vllm")
    except Exception as e:
        print(f"Error initializing LLM: {e}")
        exit(1)

    if os.path.isfile(input_path):
        process_single_file(input_path, client)
    elif os.path.isdir(input_path):
        process_directory(input_path, client)
    else:
        print(f"Error: Input path is neither a file nor a directory: {input_path}")
        exit(1) 