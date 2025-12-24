import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

def merge_json_files(mode: str) -> None:
    """
    Merge all JSON files from the archival directory for the given mode.
    
    Args:
        mode: 'cs' or 'leetcode'
    """
    # Define source directory
    base_dir = Path("anki_cards_archival")
    source_dir = base_dir / mode
    
    if not source_dir.exists():
        print(f"❌ Error: Directory '{source_dir}' does not exist.")
        return

    # Find all JSON files
    json_files = list(source_dir.glob("*.json"))
    
    if not json_files:
        print(f"⚠️ No JSON files found in '{source_dir}'.")
        return

    print(f"Found {len(json_files)} JSON files in '{source_dir}'.")

    merged_data: List[Dict[str, Any]] = []
    
    # Read and merge files
    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ensure we are adding a dictionary (object)
                if isinstance(data, dict):
                    merged_data.append(data)
                else:
                    print(f"⚠️ Warning: Skipping '{file_path.name}' - expected a JSON object, got {type(data).__name__}.")
        except json.JSONDecodeError as e:
            print(f"❌ Error: Failed to parse '{file_path.name}' - {e}")
        except Exception as e:
            print(f"❌ Error: processing '{file_path.name}' - {e}")

    if not merged_data:
        print("❌ No valid data found to merge.")
        return

    # Generate output filename
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    output_filename = f"{mode}_anki_deck_{timestamp}.json"
    output_path = Path(output_filename)

    # Write merged data
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Successfully merged {len(merged_data)} files.")
        print(f"📄 Output saved to: {output_path.absolute()}")
        
    except Exception as e:
        print(f"❌ Error: Failed to write output file - {e}")

def main():
    parser = argparse.ArgumentParser(
        description='Merge Anki JSON files from archival directory'
    )
    parser.add_argument(
        'mode',
        choices=['cs', 'leetcode'],
        help='Mode to run: cs or leetcode'
    )
    
    args = parser.parse_args()
    merge_json_files(args.mode)

if __name__ == "__main__":
    main()
