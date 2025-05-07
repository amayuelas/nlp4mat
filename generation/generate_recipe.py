from llm import LLM
import os
import argparse
import json
import re
from tqdm import tqdm


prompt = """Given this paper describing how to make a material, write down a step by step guide of the synthesis recipe.
The recipe should include the following sections:
1. Target Material
2. Reagents
3. Environment Parameters
4. Equipment
5. Procedure
6. Notes (if any)

Please format the response exactly like this example and use LaTeX for mathematical expressions and chemical formulas:

------------------ EXAMPLE STARTS ------------------

## Target Material: 
    Chemical Formula: $\\text{{FAPbI}}_3$
    Form: Single Crystals
    Expected Purity: >99.99%

## Reagents: 
    1. Formamidinium iodide (FAI)
       - Chemical Formula: $\\text{{CH}}_5\\text{{N}}_2\\text{{I}}$
       - Purity: >99.99%
       - Form: Powder
    2. Lead(II) iodide ($\\text{{PbI}}_2$)
       - Chemical Formula: $\\text{{PbI}}_2$
       - Purity: >99.99%
       - Form: Powder
    3. γ-butyrolactone (GBL)
       - Chemical Formula: $\\text{{C}}_4\\text{{H}}_6\\text{{O}}_2$
       - Purity: >99.9%
       - Form: Liquid

## Environment Parameters:
    Temperature Range: $60-180\\,^\\circ\\text{{C}}$
    Atmosphere: N₂ (inert)
    Pressure: Ambient (1 atm)
    Humidity: <1% RH (in glovebox)

## Equipment:
    1. Vessels:
       - Type: Glass vial
         Specifications: 20 mL, borosilicate
       - Type: Glass microfibre filter
         Specifications: 25 mm diameter, 0.45 µm pore size
    2. Processing Equipment:
       - Type: Stirring apparatus
         Specifications: Teflon-coated magnetic stirrer, temperature control
       - Type: Hot plate
         Specifications: Temperature range 0-300°C, digital display
       - Type: Vacuum oven
         Specifications: Temperature range up to 200°C, vacuum capability
       - Type: Oil bath
         Specifications: Temperature range 0-200°C, 2L capacity
    3. Safety Equipment:
       - Type: N₂ glovebox
         Specifications: O₂ and H₂O levels < 1 ppm
       - Type: Chemical fume hood
         Specifications: Standard laboratory grade
       - Type: Personal protective equipment
         Specifications: Nitrile gloves, lab coat, safety glasses

## Procedure:
    1. Preparation of the Precursor Solution:
       - Weigh out 687.9 mg (4 mmol) of formamidinium iodide (FAI) and 1844.0 mg (4 mmol) of lead(II) iodide ($\\text{{PbI}}_2$)
       - Dissolve these in 4 mL of γ-butyrolactone (GBL) to make a $1\\,\\text{{M}}$ solution
       - Mix using magnetic stirring at $60\\,^\\circ\\text{{C}}$ for 4 hours
    2. Filtration:
       - Filter the solution using a 25 mm diameter, 0.45 µm pore glass microfibre filter
       - Collect the filtrate in a clean glass vial
    3. Crystal Growth:
       - Transfer the filtrate to a clean vial
       - Heat the vial in an oil bath at $95\\,^\\circ\\text{{C}}$ for 4 hours
       - Maintain undisturbed conditions for crystal formation
    4. Drying:
       - Transfer crystals to a clean container
       - Dry in a vacuum oven at $180\\,^\\circ\\text{{C}}$ for 45 minutes
    5. Storage:
       - Store the crystals in an N₂-filled container
       - Keep in a desiccator to prevent moisture absorption

## Notes:
    - All synthetic work must be conducted in an N₂ glovebox except for the drying step
    - Ensure all chemicals are of high purity (>99.99%)
    - The drying step is critical for removing residual solvent
    - Crystal quality can be verified using X-ray diffraction
    - The resulting crystals can be used for further characterization or application in perovskite solar cells

------------------ EXAMPLE ENDS ------------------

Here is the paper text:

{paper_text}

IMPORTANT:
- Do not include any other text than the synthesis recipe.
- Do not include information that is not in the paper. And do not assume any information.
- Do not include any other sections than the ones specified in the example.

Your synthesis recipe: """


def clean_extraction(text: str) -> str:
    """
    Clean the extraction section by removing hyphens, bullet points, and list numbers.
    
    Args:
        text (str): The text to clean
        
    Returns:
        str: Cleaned text
    """
    # Remove hyphens at the start of lines
    text = re.sub(r'^-\s*', '', text, flags=re.MULTILINE)
    
    # Remove bullet points
    text = re.sub(r'^•\s*', '', text, flags=re.MULTILINE)
    
    # Remove numbered lists (e.g., 1., 2., etc.)
    text = re.sub(r'^\d+\.\s*', '', text, flags=re.MULTILINE)
    
    # Remove any remaining leading whitespace
    text = re.sub(r'^\s+', '', text, flags=re.MULTILINE)
    
    return text


def extract_synthesis_recipe(paper_text_path: str, model_name: str = "mistralai/Mistral-Small-3.1-24B-Instruct-2503", provider: str = "vllm") -> str:
    """
    Extract a synthesis recipe from a paper text file using an LLM.
    
    Args:
        paper_text_path (str): Path to the text file containing the paper content
        model_name (str): Name of the LLM model to use
        provider (str): Provider of the LLM service ("mistral" or "vllm")
        
    Returns:
        str: The formatted recipe text
    """
    # Read the paper text
    with open(paper_text_path, 'r') as f:
        paper_text = f.read()
    
    # Initialize LLM and get response
    llm = LLM(model_name=model_name, provider=provider)
    formatted_prompt = prompt.format(paper_text=paper_text)
    response = llm.generate_text(formatted_prompt)
    
    # Save to text file
    output_path = os.path.join(os.path.dirname(paper_text_path), "recipe.txt")
    with open(output_path, 'w') as f:
        f.write(response)
        
    return response

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Extract synthesis recipe from paper text files')
    parser.add_argument('input_path', type=str, help='Path to a text file or folder containing paper text files')
    parser.add_argument('--model', type=str, default='command-a-03-2025', 
                        help='Name of the LLM model to use')
    parser.add_argument('--provider', type=str, default='cohere', 
                        help='Provider of the LLM service')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Determine if input is a file or folder
    if os.path.isfile(args.input_path):
        if not args.input_path.endswith('.md'):
            print(f"Error: Input file must be a .md file")
            exit(1)
        text_files = [args.input_path]
    elif os.path.isdir(args.input_path):
        # Find all markdown files in the input folder and its subfolders
        text_files = []
        for root, _, files in os.walk(args.input_path):
            for file in files:
                if file.endswith('.md'):
                    text_files.append(os.path.join(root, file))
        
        if not text_files:
            print(f"No markdown files found in {args.input_path}")
            exit(1)
    else:
        print(f"Error: Input path does not exist: {args.input_path}")
        exit(1)
    
    print(f"Found {len(text_files)} markdown file(s) to process")
    
    # Process each file with progress bar
    for paper_path in tqdm(text_files, desc="Processing files"):
        try:
            # Create output directory structure
            relative_path = os.path.relpath(paper_path, args.input_path)
            output_dir = os.path.join(os.path.dirname(paper_path))
            
            # Check if filter.json exists and contains recipe
            filter_json_path = os.path.join(output_dir, "filter.json")
            if os.path.exists(filter_json_path):
                with open(filter_json_path, 'r') as f:
                    filter_data = json.load(f)
                    if not filter_data.get("contains_recipe", False):
                        print(f"\nSkipping {paper_path} - No recipe found in filter.json")
                        continue
            
            recipe = extract_synthesis_recipe(paper_path, args.model, args.provider)
            
            
            print(f"\nSuccessfully processed: {paper_path}")
            print(f"Output saved to: {output_dir}")
        except Exception as e:
            print(f"\nError processing {paper_path}: {str(e)}")
