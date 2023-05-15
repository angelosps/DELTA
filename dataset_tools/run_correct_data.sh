#!/bin/bash

# Source directory
src_dir="../DATA_copy"

# Destination directory
dst_dir="../DATA_CORRECT"

# Iterate over all files in src_dir and its subdirectories
find "$src_dir" -type f | while read -r file; do
    # Remove the src_dir part of the file path
    relative_path="${file#$src_dir/}"
    
    # Create the same directory structure in dst_dir
    mkdir -p "$dst_dir/$(dirname "$relative_path")"
    
    # Apply the Python command to the file and redirect the output to a file in dst_dir with the same relative path
    python3 datafix.py --input-file "$file" --output-file "$dst_dir/$relative_path"
done
