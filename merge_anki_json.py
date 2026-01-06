import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from src.logging_config import setup_logging
import logging

logger = logging.getLogger(__name__)

def merge_json_files(generation_mode: str) -> None:
    """
    Merge all JSON files from the archival directory for the given mode.
    
    Args:
        generation_mode: 'cs' or 'leetcode'
    """
    # Define source directory
    base_directory = Path("anki_cards_archival")
    source_directory = base_directory / generation_mode
    
    if not source_directory.exists():
        logger.error(f"❌ Error: Directory '{source_directory}' does not exist.")
        return

    # Find all JSON files
    json_file_list = list(source_directory.glob("*.json"))
    
    if not json_file_list:
        logger.warning(f"⚠️ No JSON files found in '{source_directory}'.")
        return

    logger.info(f"Found {len(json_file_list)} JSON files in '{source_directory}'.")

    merged_card_data: List[Dict[str, Any]] = []
    
    # Read and merge files
    for json_file_path in json_file_list:
        try:
            with open(json_file_path, 'r', encoding='utf-8') as input_file:
                file_data = json.load(input_file)
                # Ensure we are adding a dictionary (object)
                if isinstance(file_data, dict):
                    merged_card_data.append(file_data)
                else:
                    logger.warning(f"⚠️ Warning: Skipping '{json_file_path.name}' - expected a JSON object, got {type(file_data).__name__}.")
        except json.JSONDecodeError as decode_error:
            logger.error(f"❌ Error: Failed to parse '{json_file_path.name}' - {decode_error}")
        except Exception as error:
            logger.error(f"❌ Error: processing '{json_file_path.name}' - {error}")

    if not merged_card_data:
        logger.error("❌ No valid data found to merge.")
        return

    # Generate output filename
    current_timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    output_filename = f"{generation_mode}_anki_deck_{current_timestamp}.json"
    output_file_path = Path(output_filename)

    # Write merged data
    try:
        with open(output_file_path, 'w', encoding='utf-8') as output_file:
            json.dump(merged_card_data, output_file, indent=2, ensure_ascii=False)
        
        logger.info(f"\n✅ Successfully merged {len(merged_card_data)} files.")
        logger.info(f"📄 Output saved to: {output_file_path.absolute()}")
        
    except Exception as error:
        logger.error(f"❌ Error: Failed to write output file - {error}")

def main():
    argument_parser = argparse.ArgumentParser(
        description='Merge Anki JSON files from archival directory'
    )
    argument_parser.add_argument(
        'mode',
        choices=['cs', 'leetcode'],
        help='Mode to run: cs or leetcode'
    )
    
    parsed_arguments = argument_parser.parse_args()
    merge_json_files(parsed_arguments.mode)

if __name__ == "__main__":
    setup_logging()
    main()
