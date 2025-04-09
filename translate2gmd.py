import os
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from datetime import datetime
import uuid
from mistralai import Mistral
from tqdm import tqdm

# Initialize Mistral client
api_key = os.environ.get("MISTRAL_API_KEY")
client = Mistral(api_key=api_key) if api_key else None

# Unit mappings for different types of attributes
property_units = {
    'temperature': 'K',
    'pressure': 'GPa',
    'magnetic_field': 'T',
    'lattice_constant': 'Å',
    'band_gap': 'eV',
    'conductivity': 'S/m',
    'density': 'g/cm³',
    'melting_point': 'K',
    'curie_temperature': 'K',
    'neel_temperature': 'K',
    'hardness': 'GPa',
    'yield_strength': 'MPa',
    'tensile_strength': 'MPa',
    'elongation': '%',
    'thermal_conductivity': 'W/m·K',
    'specific_heat': 'J/g·K',
    'coefficient_of_thermal_expansion': '10⁻⁶/K'
}

condition_units = {
    'temperature': 'K',
    'pressure': 'GPa',
    'magnetic_field': 'T',
    'atmosphere': 'dimensionless',
    'synthesis_method': 'dimensionless',
    'sample_preparation': 'dimensionless',
    'measurement_method': 'dimensionless',
    'crystal_structure': 'dimensionless',
    'phase': 'dimensionless',
    'orientation': 'dimensionless',
    'grain_size': 'μm',
    'surface_finish': 'dimensionless',
    'heat_treatment': 'dimensionless',
    'cooling_rate': 'K/s'
}

parameter_units = {
    'measurement_time': 's',
    'scan_rate': 'K/min',
    'sample_size': 'mm',
    'heating_rate': 'K/min',
    'cooling_rate': 'K/s',
    'strain_rate': 's⁻¹',
    'frequency': 'Hz',
    'voltage': 'V',
    'current': 'A'
}

@dataclass
class Material:
    name: str
    formula: str
    properties: Dict[str, float]
    conditions: Dict[str, Any]
    parameters: Dict[str, float]
    source: str
    authors: List[str]
    date: str
    notes: Optional[str] = None
    tags: List[str] = None
    uids: List[str] = None

def generate_uid() -> str:
    """Generate a unique identifier for GEMD objects."""
    return str(uuid.uuid4())

def create_template(name: str, description: Optional[str] = None) -> Dict:
    """Create a GEMD template with required fields."""
    return {
        "type": "template",
        "name": name,
        "uids": [generate_uid()],
        "description": description
    }

def create_spec(name: str, template: Optional[Dict] = None, notes: Optional[str] = None) -> Dict:
    """Create a GEMD spec with required fields."""
    spec = {
        "type": "spec",
        "name": name,
        "uids": [generate_uid()],
        "notes": notes
    }
    if template:
        spec["template"] = template
    return spec

def create_run(name: str, spec: Dict, notes: Optional[str] = None) -> Dict:
    """Create a GEMD run with required fields."""
    return {
        "type": "run",
        "name": name,
        "uids": [generate_uid()],
        "spec": spec,
        "notes": notes
    }

def create_attribute(name: str, value: Any, origin: str, units: str = "dimensionless", 
                    template: Optional[Dict] = None, notes: Optional[str] = None) -> Dict:
    """Create a GEMD attribute with required fields."""
    attribute = {
        "type": "attribute",
        "name": name,
        "value": value,
        "origin": origin,
        "units": units,
        "notes": notes
    }
    if template:
        attribute["template"] = template
    return attribute

def extract_relevant_sections(text: str) -> Dict[str, str]:
    """Extract relevant sections from the text for LLM processing."""
    sections = {
        "properties": "",
        "conditions": "",
        "parameters": ""
    }
    
    # Common section headers in materials science papers
    section_headers = {
        "properties": [
            r"properties",
            r"characterization",
            r"measurements",
            r"results",
            r"physical properties",
            r"mechanical properties",
            r"thermal properties",
            r"electrical properties",
            r"magnetic properties",
            r"optical properties"
        ],
        "conditions": [
            r"experimental",
            r"methodology",
            r"sample preparation",
            r"synthesis",
            r"processing",
            r"heat treatment",
            r"annealing",
            r"quenching",
            r"atmosphere",
            r"environment"
        ],
        "parameters": [
            r"measurement parameters",
            r"experimental setup",
            r"instrumentation",
            r"measurement conditions",
            r"scanning parameters",
            r"heating rate",
            r"cooling rate",
            r"strain rate",
            r"frequency",
            r"voltage"
        ]
    }
    
    # Split text into paragraphs
    paragraphs = text.split('\n\n')
    
    # Process each paragraph
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        # Check for section headers
        for section, headers in section_headers.items():
            for header in headers:
                if re.search(header, para, re.IGNORECASE):
                    sections[section] += para + "\n\n"
                    break
    
    return sections

def split_text_into_chunks(text: str, max_chunk_size: int = 1000) -> List[str]:
    """Split text into smaller chunks while preserving sentence boundaries."""
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = []
    current_size = 0
    
    for sentence in sentences:
        sentence_size = len(sentence)
        if current_size + sentence_size > max_chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            current_size = 0
        
        current_chunk.append(sentence)
        current_size += sentence_size
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

def extract_with_llm(text: str) -> Dict[str, Any]:
    """Use LLM to extract material information from smaller chunks of text."""
    if not client:
        return {}
    
    # Split text into smaller chunks
    chunks = split_text_into_chunks(text)
    result = {
        "properties": {},
        "conditions": {},
        "parameters": {}
    }
    
    # Process each chunk with progress bar
    for chunk in tqdm(chunks, desc="Processing text chunks", leave=False):
        # Extract relevant sections from the chunk
        sections = extract_relevant_sections(chunk)
        
        # Skip empty chunks
        if not any(sections.values()):
            continue
        
        # Create focused prompt for this chunk
        prompt = f"""You are a materials science expert. Extract material information from the following text.
        Return ONLY a JSON object with this exact structure:
        {{
            "properties": {{"property_name": numeric_value}},
            "conditions": {{"condition_name": value}},
            "parameters": {{"parameter_name": numeric_value}}
        }}
        
        Text to analyze:
        {sections['properties']}
        {sections['conditions']}
        {sections['parameters']}
        
        Rules:
        1. Return ONLY valid JSON
        2. Use numeric values for properties and parameters
        3. Use strings for categorical conditions
        4. Use numbers for numeric conditions
        5. Do not include any explanatory text
        6. Use null for invalid values
        7. Extract only information present in this text chunk
        """
        
        try:
            # Process chunk with LLM
            response = client.chat.complete(
                model="mistral-small-latest",
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Extract JSON from response
            response_text = response.choices[0].message.content.strip()
            
            # Try to find JSON in the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                try:
                    chunk_result = json.loads(json_str)
                    # Merge results from this chunk
                    for section in ["properties", "conditions", "parameters"]:
                        if section in chunk_result:
                            # For properties and parameters, only update if value is better (not null)
                            if section in ["properties", "parameters"]:
                                for name, value in chunk_result[section].items():
                                    if value is not None and (name not in result[section] or result[section][name] is None):
                                        result[section][name] = value
                            # For conditions, update if not present
                            else:
                                for name, value in chunk_result[section].items():
                                    if name not in result[section]:
                                        result[section][name] = value
                except json.JSONDecodeError as e:
                    print(f"JSON parsing error in chunk: {e}")
            else:
                print("No valid JSON found in chunk response")
                
        except Exception as e:
            print(f"LLM extraction failed for chunk: {e}")
            continue
    
    return result

def extract_properties_and_conditions(text: str) -> Tuple[Dict[str, float], Dict[str, Any], Dict[str, Any]]:
    """Extract material properties, conditions, and parameters from text using both regex and LLM."""
    properties = {}
    conditions = {}
    parameters = {}
    
    # Common property patterns in materials science papers
    property_patterns = {
        'temperature': r'(\d+(?:\.\d+)?)\s*(?:K|°C|°K)',
        'pressure': r'(\d+(?:\.\d+)?)\s*(?:GPa|MPa|bar|atm)',
        'magnetic_field': r'(\d+(?:\.\d+)?)\s*(?:T|mT|kOe)',
        'lattice_constant': r'(\d+(?:\.\d+)?)\s*(?:Å|A)',
        'band_gap': r'(\d+(?:\.\d+)?)\s*(?:eV)',
        'conductivity': r'(\d+(?:\.\d+)?)\s*(?:S/m|Ω⋅cm)',
        'density': r'(\d+(?:\.\d+)?)\s*(?:g/cm³|g/cm3)',
        'melting_point': r'(\d+(?:\.\d+)?)\s*(?:K|°C|°K)',
        'curie_temperature': r'(\d+(?:\.\d+)?)\s*(?:K|°C|°K)',
        'neel_temperature': r'(\d+(?:\.\d+)?)\s*(?:K|°C|°K)',
        'hardness': r'(\d+(?:\.\d+)?)\s*(?:GPa|MPa|Vickers)',
        'yield_strength': r'(\d+(?:\.\d+)?)\s*(?:MPa|GPa)',
        'tensile_strength': r'(\d+(?:\.\d+)?)\s*(?:MPa|GPa)',
        'elongation': r'(\d+(?:\.\d+)?)\s*(?:%)',
        'thermal_conductivity': r'(\d+(?:\.\d+)?)\s*(?:W/m·K)',
        'specific_heat': r'(\d+(?:\.\d+)?)\s*(?:J/g·K)',
        'coefficient_of_thermal_expansion': r'(\d+(?:\.\d+)?)\s*(?:10⁻⁶/K)',
    }
    
    # Common condition patterns with more context
    condition_patterns = {
        'temperature': r'(?:at|measured at|recorded at)\s+(\d+(?:\.\d+)?)\s*(?:K|°C|°K)',
        'pressure': r'(?:at|measured at|recorded at)\s+(\d+(?:\.\d+)?)\s*(?:GPa|MPa|bar|atm)',
        'magnetic_field': r'(?:at|measured at|recorded at)\s+(\d+(?:\.\d+)?)\s*(?:T|mT|kOe)',
        'atmosphere': r'(?:under|in)\s+(?:vacuum|air|nitrogen|argon|oxygen|inert atmosphere)',
        'synthesis_method': r'(?:synthesized|prepared|grown)\s+by\s+([^.,]+)',
        'sample_preparation': r'(?:sample was|samples were)\s+([^.,]+)',
        'measurement_method': r'(?:measured using|characterized by)\s+([^.,]+)',
        'crystal_structure': r'(?:crystal structure|structure)\s+([^.,]+)',
        'phase': r'(?:phase|crystalline phase)\s+([^.,]+)',
        'orientation': r'(?:oriented|orientation)\s+([^.,]+)',
        'grain_size': r'grain size\s+(\d+(?:\.\d+)?)\s*(?:μm|nm)',
        'surface_finish': r'surface finish\s+([^.,]+)',
        'heat_treatment': r'heat treated\s+([^.,]+)',
        'cooling_rate': r'cooling rate\s+(\d+(?:\.\d+)?)\s*(?:K/s|°C/s)',
    }
    
    # Common parameter patterns
    parameter_patterns = {
        'measurement_time': r'measurement time\s+(\d+(?:\.\d+)?)\s*(?:s|min|h)',
        'scan_rate': r'scan rate\s+(\d+(?:\.\d+)?)\s*(?:K/min|°C/min)',
        'sample_size': r'sample size\s+(\d+(?:\.\d+)?)\s*(?:mm|cm)',
        'heating_rate': r'heating rate\s+(\d+(?:\.\d+)?)\s*(?:K/min|°C/min)',
        'cooling_rate': r'cooling rate\s+(\d+(?:\.\d+)?)\s*(?:K/s|°C/s)',
        'strain_rate': r'strain rate\s+(\d+(?:\.\d+)?)\s*(?:s⁻¹)',
        'frequency': r'frequency\s+(\d+(?:\.\d+)?)\s*(?:Hz|kHz|MHz)',
        'voltage': r'voltage\s+(\d+(?:\.\d+)?)\s*(?:V|kV|mV)',
        'current': r'current\s+(\d+(?:\.\d+)?)\s*(?:A|mA|μA)',
    }
    
    # Extract properties with progress bar
    for prop_name, pattern in tqdm(property_patterns.items(), desc="Extracting properties", leave=False):
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                value = float(match.group(1))
                properties[prop_name] = value
            except ValueError:
                continue
    
    # Extract conditions with progress bar
    for cond_name, pattern in tqdm(condition_patterns.items(), desc="Extracting conditions", leave=False):
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                if cond_name in ['atmosphere', 'synthesis_method', 'sample_preparation', 
                               'measurement_method', 'crystal_structure', 'phase', 'orientation',
                               'surface_finish', 'heat_treatment']:
                    conditions[cond_name] = match.group(0).strip()
                else:
                    value = float(match.group(1))
                    conditions[cond_name] = value
            except ValueError:
                continue
    
    # Extract parameters with progress bar
    for param_name, pattern in tqdm(parameter_patterns.items(), desc="Extracting parameters", leave=False):
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                value = float(match.group(1))
                parameters[param_name] = value
            except ValueError:
                continue
    
    # Then enhance with LLM-based extraction
    print("Before!!!")
    llm_result = extract_with_llm(text)
    print("After!!!")

    
    # Merge LLM results with regex results
    for prop_name, value in tqdm(llm_result.get("properties", {}).items(), desc="Merging LLM properties", leave=False):
        if prop_name not in properties:
            try:
                properties[prop_name] = float(value)
            except (ValueError, TypeError):
                continue
    
    for cond_name, value in tqdm(llm_result.get("conditions", {}).items(), desc="Merging LLM conditions", leave=False):
        if cond_name not in conditions:
            conditions[cond_name] = value
    
    for param_name, value in tqdm(llm_result.get("parameters", {}).items(), desc="Merging LLM parameters", leave=False):
        if param_name not in parameters:
            try:
                parameters[param_name] = float(value)
            except (ValueError, TypeError):
                continue
    
    return properties, conditions, parameters

def validate_and_clean_material(material: Material) -> Material:
    """Validate and clean material data using LLM."""
    if not client:
        return material
    
    prompt = f"""You are a materials science expert. Validate and clean the following material data.
    Return ONLY a JSON object with the following structure:
    {{
        "properties": {{"property_name": value}},
        "conditions": {{"condition_name": value}},
        "parameters": {{"parameter_name": value}}
    }}
    
    Material data to validate:
    {{
        "name": "{material.name}",
        "formula": "{material.formula}",
        "properties": {json.dumps(material.properties)},
        "conditions": {json.dumps(material.conditions)},
        "parameters": {json.dumps(material.parameters)}
    }}
    
    Tasks:
    1. Validate chemical formula format
    2. Check property values are within reasonable ranges
    3. Ensure units are consistent
    4. Remove any invalid or contradictory data
    5. Add any missing important properties or conditions
    
    Important:
    - Return ONLY valid JSON
    - Do not include any explanatory text
    - Keep numeric values as numbers, not strings
    - Use null for invalid values
    """
    try:
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract JSON from response
        response_text = response.choices[0].message.content.strip()
        
        # Try to find JSON in the response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            cleaned_data = json.loads(json_str)
        else:
            print("No valid JSON found in LLM response")
            return material
        
        # Update material with cleaned data
        if "properties" in cleaned_data:
            for name, value in cleaned_data["properties"].items():
                if value is not None:  # Only update non-null values
                    try:
                        material.properties[name] = float(value)
                    except (ValueError, TypeError):
                        continue
        
        if "conditions" in cleaned_data:
            for name, value in cleaned_data["conditions"].items():
                if value is not None:  # Only update non-null values
                    material.conditions[name] = value
        
        if "parameters" in cleaned_data:
            for name, value in cleaned_data["parameters"].items():
                if value is not None:  # Only update non-null values
                    try:
                        material.parameters[name] = float(value)
                    except (ValueError, TypeError):
                        continue
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
    except Exception as e:
        print(f"LLM validation failed: {e}")
    
    return material

def parse_markdown_file(file_path: Path) -> Material:
    """Parse markdown file to extract material information."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract title and authors
    lines = content.split('\n')
    title = lines[0].replace('# ', '').strip()
    authors = []
    for line in lines[1:]:
        if line.startswith('${ }^{'):
            authors.append(line.split('}$')[0].split('${ }^{')[1].strip())
        elif line.strip() and not line.startswith('#'):
            break
    

    # Extract material formula from title
    formula = title.split('$\\mathrm{')[-1].split('}$')[0] if '$\\mathrm{' in title else ''
    # Extract properties, conditions, and parameters from the text
    properties, conditions, parameters = extract_properties_and_conditions(content)

    # Create Material object with extracted information
    material = Material(
        name=title,
        formula=formula,
        properties=properties,
        conditions=conditions,
        parameters=parameters,
        source=str(file_path),
        authors=authors,
        date=datetime.now().isoformat()
    )
    
    # Validate and clean material data using LLM
    material = validate_and_clean_material(material)

    return material

def create_gemd_material(material: Material) -> Dict:
    """Convert Material object to GEMD format with proper Specs and Runs."""
    # Create templates
    material_template = create_template(
        name="Material Template",
        description="Template for material properties and conditions"
    )
    
    measurement_template = create_template(
        name="Measurement Template",
        description="Template for material measurements"
    )
    
    process_template = create_template(
        name="Process Template",
        description="Template for material processing steps"
    )
    
    # Create material spec
    material_spec = create_spec(
        name=f"{material.name} Spec",
        template=material_template,
        notes="Specification for material properties and conditions"
    )
    
    # Create material run
    material_run = create_run(
        name=f"{material.name} Run",
        spec=material_spec,
        notes="Actual material properties and conditions"
    )
    
    # Create GEMD format material with proper structure
    gemd_material = {
        "type": "material",
        "name": material.name,
        "formula": material.formula,
        "template": material_template,
        "spec": material_spec,
        "run": material_run,
        "properties": [],
        "conditions": [],
        "parameters": [],
        "source": {
            "type": "source",
            "name": material.source,
            "authors": material.authors,
            "date": material.date
        }
    }
    
    # Add properties with their units and associated conditions
    for name, value in material.properties.items():
        units = property_units.get(name, "dimensionless")
        property_attr = create_attribute(
            name=name,
            value=value,
            origin="measured",
            units=units,
            template=measurement_template
        )
        gemd_material["properties"].append(property_attr)
    
    # Add conditions
    for name, value in material.conditions.items():
        units = condition_units.get(name, "dimensionless")
        condition_attr = create_attribute(
            name=name,
            value=value,
            origin="specified",
            units=units,
            template=process_template
        )
        gemd_material["conditions"].append(condition_attr)
    
    # Add parameters
    for name, value in material.parameters.items():
        units = parameter_units.get(name, "dimensionless")
        parameter_attr = create_attribute(
            name=name,
            value=value,
            origin="specified",
            units=units,
            template=process_template
        )
        gemd_material["parameters"].append(parameter_attr)
    
    return gemd_material

def process_ocr_output(ocr_dir: str = "ocr_output") -> List[Dict]:
    """Process all OCR output files and convert them to GEMD format."""
    ocr_path = Path(ocr_dir)
    gemd_materials = []
    
    # Get list of markdown files
    markdown_files = [f for f in ocr_path.rglob("output.md")]
    total_files = len(markdown_files)
    print(f"\nFound {total_files} papers to process")
    
    # Process files with progress bar
    with tqdm(total=total_files, desc="Overall Progress", unit="paper") as pbar:
        for markdown_file in markdown_files:
            # Extract material information
            with tqdm(total=100, desc="Extracting Information", leave=False, unit="%") as extract_pbar:
                material = parse_markdown_file(markdown_file)
                extract_pbar.update(50)
                
                # Convert to GEMD format
                gemd_material = create_gemd_material(material)
                extract_pbar.update(50)
            
            gemd_materials.append(gemd_material)
            pbar.update(1)
            
            # Show timing information
            pbar.set_postfix({
                "Processed": f"{len(gemd_materials)}/{total_files}",
                "Properties": len(material.properties),
                "Conditions": len(material.conditions),
                "Parameters": len(material.parameters)
            })
    
    return gemd_materials

def save_gemd_data(materials: List[Dict], output_file: str = "gemd_data.json"):
    """Save GEMD data to a JSON file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({"materials": materials}, f, indent=2, ensure_ascii=False)

def main():
    print("Starting GEMD data extraction...")
    start_time = datetime.now()
    
    # Process papers
    materials = process_ocr_output()
    
    # Save results
    print("\nSaving results...")
    save_gemd_data(materials)
    
    # Calculate and display timing information
    end_time = datetime.now()
    duration = end_time - start_time
    print(f"\nProcessing completed in {duration.total_seconds():.2f} seconds")
    print(f"Processed {len(materials)} papers")
    print(f"Average time per paper: {duration.total_seconds()/len(materials):.2f} seconds")
    print(f"GEMD data saved to gemd_data.json")

if __name__ == "__main__":
    main() 