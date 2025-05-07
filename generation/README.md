# Dataset Generation Pipeline

This document describes the step-by-step process for generating the dataset used in this project.

## Pipeline Overview

The dataset generation process consists of the following steps:

1. Download Kaggle JSON
2. Check Downloaded Files
3. Filter JSON
4. Download Cloud
5. Parse Data
6. Filter LLM
7. Generate Recipe

## Detailed Steps

### 1. Download Kaggle JSON
- Downloads the raw JSON data from Kaggle
- This is the initial source of our dataset
- Requires Kaggle API credentials to be properly configured
- **File**: `download_kaggle.py`
  - Uses `kagglehub` to download the Cornell University arXiv dataset
  - Downloads the latest version of the dataset
  - Returns the path to the downloaded dataset files

### 2. Check Downloaded Files
- Verifies the integrity of downloaded files
- Ensures all required files are present
- Validates file formats and basic structure
- **Files**: 
  - `check_downloaded_files.py`: 
    - Processes metadata and checks PDF existence
    - Uses parallel processing to handle large datasets
    - Verifies that PDF files exist for each metadata entry
    - Creates a new JSON with only existing files
  - `count_recipes.py`: Counts and analyzes the number of recipes in the dataset

### 3. Filter JSON
- Processes the raw JSON data
- Removes irrelevant or malformed entries
- Applies initial quality filters
- Creates a cleaned version of the JSON dataset
- **File**: `filter_json.py`
  - Specifically filters for cond-mat papers from arXiv metadata
  - Reads input JSON file line by line
  - Filters entries based on 'cond-mat' category
  - Writes filtered data to output JSON file

### 4. Download Cloud
- Downloads additional cloud-based resources
- May include supplementary data or models
- Ensures all necessary cloud resources are available
- **Files**:
  - `download_gcloud.py`: Basic Google Cloud download implementation
  - `download_gcloud_multithread.py`: Multi-threaded version for faster downloads

### 5. Parse Data
- Uses a dedicated parsing script
- Converts the filtered JSON into a structured format
- Extracts relevant information and metadata
- Creates intermediate data representations
- **Files**:
  - `parse_pdf_marker.py`: Parses PDF files and extracts markers
  - `script_marker.sh`: Shell script to run the marker parsing process

### 6. Filter LLM
- Applies language model-based filtering
- Removes low-quality or irrelevant content
- Ensures consistency and quality of the dataset
- May use specific criteria for content selection
- **Files**:
  - `filter_llm.py`: Main LLM filtering implementation
  - `llm.py`: Core LLM functionality and utilities
  - `script_filter_llm.sh`: Shell script to run the LLM filtering process

### 7. Generate Recipe
- Creates the final recipe dataset
- Combines all processed information
- Formats data according to project requirements
- Produces the final dataset ready for use
- **File**: `generate_recipe.py`
  - Generates the final recipe dataset from processed data
  - Combines all previous processing steps
  - Creates the final formatted dataset

## Additional Files

- `dataset_stastistics.ipynb`: Jupyter notebook for analyzing dataset statistics and visualizations

## Notes

- Each step in the pipeline can be run independently if needed
- Intermediate results are saved to allow for pipeline resumption
- Logs are maintained for debugging and verification purposes
