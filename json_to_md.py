import json
import os
from pathlib import Path
from src.logging_config import setup_logging
import logging

logger = logging.getLogger(__name__)

def convert_json_to_md(source_directory: str, target_directory: str):
    """
    Recursively converts all JSON files in source_directory to Markdown files in target_directory.
    """
    source_path = Path(source_directory)
    target_path = Path(target_directory)
    
    if not source_path.exists():
        logger.error(f"Error: Source directory '{source_directory}' does not exist.")
        return

    # Create target directory if it doesn't exist
    target_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {target_path.resolve()}")

    # Find all JSON files recursively
    json_file_list = list(source_path.rglob("*.json"))
    
    if not json_file_list:
        logger.warning("No JSON files found.")
        return

    logger.info(f"Found {len(json_file_list)} JSON files. Starting conversion...")

    for json_file_path in json_file_list:
        try:
            with open(json_file_path, 'r', encoding='utf-8') as input_file:
                card_data = json.load(input_file)
            
            # Determine relative path to maintain structure if needed, 
            # or just flatten. The user asked for "create another folder", 
            # usually implies a flat list or mirroring. 
            # Given the filenames are timestamped and unique, a flat structure in the target folder is safest and simplest.
            
            # Create a markdown filename based on the JSON filename
            markdown_filename = json_file_path.stem + ".md"
            markdown_file_path = target_path / markdown_filename
            
            with open(markdown_file_path, 'w', encoding='utf-8') as output_file:
                # Title of the document
                document_title = json_file_path.stem.replace('_', ' ').title()
                output_file.write(f"# {document_title}\n\n")
                
                if isinstance(card_data, dict):
                    if 'cards' in card_data:
                        card_data = card_data['cards']
                    else:
                        logger.warning(f"Warning: {json_file_path.name} is a dict but has no 'cards' key.")
                        continue

                if isinstance(card_data, list):
                    for card_number, card_item in enumerate(card_data, 1):
                        output_file.write(f"## Card {card_number}\n")
                        
                        # Metadata
                        card_type_value = card_item.get('card_type', 'N/A')
                        card_tags = card_item.get('tags', [])
                        if isinstance(card_tags, list):
                            tags_string = ", ".join(card_tags)
                        else:
                            tags_string = str(card_tags)
                            
                        output_file.write(f"**Type**: {card_type_value}  \n")
                        output_file.write(f"**Tags**: {tags_string}\n\n")
                        
                        # Front
                        output_file.write("### Front\n")
                        output_file.write(f"{card_item.get('front', '')}\n\n")
                        
                        # Back
                        output_file.write("### Back\n")
                        output_file.write(f"{card_item.get('back', '')}\n\n")
                        
                        output_file.write("---\n\n")
                else:
                    logger.warning(f"Warning: {json_file_path.name} does not contain a list of cards (found {type(card_data)}).")
            
            logger.info(f"Converted: {json_file_path.name} -> {markdown_filename}")
            
        except json.JSONDecodeError:
            logger.error(f"Error: Failed to decode JSON from {json_file_path.name}")
        except Exception as error:
            logger.error(f"Error processing {json_file_path.name}: {error}")

    logger.info("\nConversion complete.")

if __name__ == "__main__":
    setup_logging()
    SOURCE_DIRECTORY = "anki_cards_archival"
    TARGET_DIRECTORY = "anki_cards_markdown"
    convert_json_to_md(SOURCE_DIRECTORY, TARGET_DIRECTORY)
