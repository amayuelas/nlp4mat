from typing import Dict, List, Optional
import json
from llm import LLM
import os
import argparse

class GEMDExtractor:
    def __init__(self, model_name: str = "mistral-large-latest", provider: str = "mistral"):
        self.llm = LLM(model_name=model_name, provider=provider)
        
    def _create_extraction_prompt(self, text: str, synthesis_recipe: str) -> str:
        return f"""Task: Extract the synthesis procedure from the following research paper text and convert it to GEMD format.

Context:
The GEMD (Graphical Expression of Materials Data) format represents synthesis procedures as a sequence of Process Objects, where each process step contains:
- Parameters: Controlled variables (e.g., temperature, time, pressure)
- Conditions: Environmental variables (e.g., atmosphere, humidity)
- Input Materials: Ingredients with their quantities and roles
- Output Materials: Resulting materials from each step

Additional Context - Synthesis Recipe:
{synthesis_recipe}

Instructions:
1. Identify each distinct step in the synthesis procedure
2. For each step, extract:
   - Action/process name
   - Parameters (quantities, times, temperatures, etc.)
   - Conditions (atmosphere, pressure, etc.)
   - Input materials and their quantities
   - Output materials
3. Organize the steps in chronological order
4. Ensure all quantities have proper units

Text to analyze:
{text}

Please provide the output in JSON format following this structure:
{{
  "procedure": [
    {{
      "name": "step name",
      "parameters": [
        {{
          "name": "parameter name",
          "value": {{
            "nominal": value,
            "units": "unit"
          }}
        }}
      ],
      "conditions": [
        {{
          "name": "condition name",
          "value": {{
            "nominal": value,
            "units": "unit"
          }}
        }}
      ],
      "input_materials": [
        {{
          "name": "material name",
          "quantity": {{
            "nominal": value,
            "units": "unit"
          }}
        }}
      ],
      "output_materials": [
        {{
          "name": "material name"
        }}
      ]
    }}
  ]
}}"""

    def _create_refinement_prompt(self, extracted_data: Dict, synthesis_recipe: str) -> str:
        return f"""Task: Refine and validate the synthesis procedure extracted from a research paper.

Context:
The procedure should be represented as a sequence of Process Objects in GEMD format, where each step must have:
- Clear process name
- All relevant parameters with proper units
- All relevant conditions with proper units
- Complete input and output material information

Synthesis Recipe for Reference:
{synthesis_recipe}

Current extracted data:
{json.dumps(extracted_data, indent=2)}

Please review and refine the data to ensure:
1. Each step is clearly defined and in correct order
2. All parameters have proper units and values
3. All conditions are properly specified
4. Input and output materials are correctly identified
5. No steps are missing or incorrectly combined
6. The structure follows the GEMD Process Object format

Provide the refined data in JSON format."""

    def extract_gemd_data(self, paper_text: str, synthesis_recipe: str) -> Dict:
        # First extraction pass
        extraction_prompt = self._create_extraction_prompt(paper_text, synthesis_recipe)
        extracted_data = self.llm.generate_text(extraction_prompt, response_format={"type": "json_object"})
        
        # Parse the JSON response
        try:
            extracted_data = json.loads(extracted_data)
        except json.JSONDecodeError:
            raise ValueError("Failed to parse LLM response as JSON")
        
        # Refinement pass
        refinement_prompt = self._create_refinement_prompt(extracted_data, synthesis_recipe)
        refined_data = self.llm.generate_text(refinement_prompt, response_format={"type": "json_object"})
        
        try:
            return json.loads(refined_data)
        except json.JSONDecodeError:
            raise ValueError("Failed to parse refined LLM response as JSON")

    def save_gemd_data(self, data: Dict, output_path: str):
        """Save the extracted GEMD data to a JSON file."""
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

def process_file(input_file: str, output_file: Optional[str] = None) -> None:
    """
    Process an input file and save the GEMD data to the specified output file.
    If no output file is specified, it will save as 'synthesis.json' in the same directory as the input file.
    
    Args:
        input_file (str): Path to the input file containing the paper text
        output_file (Optional[str]): Path to the output file. If None, will use 'synthesis.json' in the input file's directory
    """
    # Validate input file exists
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    # Set default output file if not provided
    if output_file is None:
        input_dir = os.path.dirname(input_file)
        output_file = os.path.join(input_dir, "synthesis.json")
    
    # Read input file
    with open(input_file, 'r') as f:
        paper_text = f.read()
    
    # Read synthesis recipe file
    input_dir = os.path.dirname(input_file)
    synthesis_recipe_path = os.path.join(input_dir, "synthesis_step_by_step.txt")
    if not os.path.exists(synthesis_recipe_path):
        print(f"Warning: Synthesis recipe file not found at {synthesis_recipe_path}. Proceeding without it.")
        synthesis_recipe = ""
    else:
        with open(synthesis_recipe_path, 'r') as f:
            synthesis_recipe = f.read()
    
    # Process the text
    extractor = GEMDExtractor()
    try:
        gemd_data = extractor.extract_gemd_data(paper_text, synthesis_recipe)
        extractor.save_gemd_data(gemd_data, output_file)
        print(f"GEMD data successfully extracted and saved to: {output_file}")
    except Exception as e:
        print(f"Error during extraction: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Extract GEMD data from research papers')
    parser.add_argument('input_file', help='Path to the input file containing the paper text')
    parser.add_argument('--output', '-o', help='Path to the output file (default: synthesis.json in input file directory)')
    
    args = parser.parse_args()
    process_file(args.input_file, args.output)

if __name__ == "__main__":
    main()
