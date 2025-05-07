#!/bin/bash

trap 'pkill -P $$' SIGINT

# Define years to process
YEARS=(2017)
VISIBLE_DEVICES=(4 5 6 7)
NUM_DEVICES=${#VISIBLE_DEVICES[@]}
NUM_WORKERS=10

# Process each year sequentially
for YEAR in "${YEARS[@]}"; do
    echo "Processing year: $YEAR"
    INPUT_FOLDER="data_arxiv/cond-mat/pdfs/$YEAR"
    OUTPUT_FOLDER="data_arxiv/cond-mat/parsed/$YEAR"
    echo "INPUT_FOLDER: $INPUT_FOLDER"
    
    # Ensure output folder exists
    mkdir -p "$OUTPUT_FOLDER"
    
    # Loop from 0 to NUM_DEVICES and run the marker command in parallel
    IT=0
    for DEVICE_NUM in "${VISIBLE_DEVICES[@]}"; do
        export DEVICE_NUM
        export NUM_DEVICES
        export NUM_WORKERS
        echo "Running marker on GPU $DEVICE_NUM for year $YEAR"
        cmd="CUDA_VISIBLE_DEVICES=$DEVICE_NUM marker $INPUT_FOLDER --output_dir $OUTPUT_FOLDER --num_chunks $NUM_DEVICES --chunk_idx $IT --workers $NUM_WORKERS"
        eval $cmd &
        IT=$((IT+1))
        sleep 5
    done
    
    # Wait for all background processes to finish for current year
    wait
    echo "Finished processing year $YEAR"
    echo "----------------------------------------"
done


