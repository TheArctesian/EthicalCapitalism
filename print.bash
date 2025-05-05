#!/bin/bash

# Define the output file name
output_file="print.txt"
# Define the starting directory (current directory)
start_dir="."

# --- Safety Check ---
# Check if the output file already exists in the start directory
# If we don't exclude it, 'find' might find it and try to cat it into itself.
# We will exclude it using -path and -prune in the find command below.
output_path="./${output_file}" # Construct the relative path for exclusion

# --- Initialization ---
# Clear the output file or create it if it doesn't exist
# The '>' operator truncates the file if it exists or creates it if it doesn't.
> "$output_file"
echo "Initialized (or cleared) $output_file."

echo "Starting to process files recursively from '$start_dir'..."

# --- Core Logic: Find and Process Files ---
# Use 'find' to locate files and execute commands for each file found.
#
# Explanation of the find command:
# '.'                 : Start searching from the current directory.
# -path "$output_path" : Match the exact relative path of our output file.
# -prune              : If the path matches, do not descend into it (if it were a directory)
#                       and do not process it further. This effectively excludes print.txt.
# -o                  : OR operator. The action applies if the '-prune' wasn't triggered.
# -type f             : Consider only regular files (not directories, links, etc.).
# -exec sh -c '...' _ {} \; : For each file found (represented by {}):
#   sh -c '...'       : Execute a mini-shell script.
#   _                 : A placeholder for the script name ($0 inside the sh -c).
#   {}                : The found file path is passed as the first argument ($1) to the mini-script.
#   \;                : Terminates the -exec command.
#
# Inside the sh -c '...' script:
#   filepath="$1"     : Assign the passed file path ($1) to a variable for clarity.
#   echo "--- File: ${filepath} ---" >> "$output_file" : Append the header with the file path.
#   cat "${filepath}" >> "$output_file"               : Append the content of the file.
#                                                       Using quotes handles filenames with spaces/special chars.
#   echo "" >> "$output_file"                         : Append a blank line for separation between files.
#   echo "" >> "$output_file"                         : Append another blank line for better readability.
#   We use '>>' for appending to the output file.
#   The '&&' ensures that cat only runs if echo succeeds, and the final echo only if cat succeeds.

find "$start_dir" -path "$output_path" -prune -o -type f -exec sh -c '
    filepath="$1"
    # Append header and content to the output file
    {
        echo "--- File: ${filepath} ---"
        cat "${filepath}"
        echo "" # Add a blank line after content
        echo "" # Add another blank line for separation
    } >> "'"$output_file"'" || echo "Error processing ${filepath}" >&2
' _ {} \;

# --- Completion ---
echo "Processing complete. All file contents appended to '$output_file'."

# Optional: Print the number of files processed (requires counting lines with "--- File:")
file_count=$(grep -c -- "--- File: " "$output_file")
echo "Processed $file_count files."

exit 0