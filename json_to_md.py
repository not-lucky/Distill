import json
import os
from pathlib import Path

def convert_json_to_md(source_dir, target_dir):
    """
    Recursively converts all JSON files in source_dir to Markdown files in target_dir.
    """
    source_path = Path(source_dir)
    target_path = Path(target_dir)
    
    if not source_path.exists():
        print(f"Error: Source directory '{source_dir}' does not exist.")
        return

    # Create target directory if it doesn't exist
    target_path.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {target_path.resolve()}")

    # Find all JSON files recursively
    json_files = list(source_path.rglob("*.json"))
    
    if not json_files:
        print("No JSON files found.")
        return

    print(f"Found {len(json_files)} JSON files. Starting conversion...")

    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                cards = json.load(f)
            
            # Determine relative path to maintain structure if needed, 
            # or just flatten. The user asked for "create another folder", 
            # usually implies a flat list or mirroring. 
            # Given the filenames are timestamped and unique, a flat structure in the target folder is safest and simplest.
            
            # Create a markdown filename based on the JSON filename
            md_filename = json_file.stem + ".md"
            md_file_path = target_path / md_filename
            
            with open(md_file_path, 'w', encoding='utf-8') as md_file:
                # Title of the document
                title = json_file.stem.replace('_', ' ').title()
                md_file.write(f"# {title}\n\n")
                
                if isinstance(cards, dict):
                    if 'cards' in cards:
                        cards = cards['cards']
                    else:
                        print(f"Warning: {json_file.name} is a dict but has no 'cards' key.")
                        continue

                if isinstance(cards, list):
                    for i, card in enumerate(cards, 1):
                        md_file.write(f"## Card {i}\n")
                        
                        # Metadata
                        card_type = card.get('card_type', 'N/A')
                        tags = card.get('tags', [])
                        if isinstance(tags, list):
                            tags_str = ", ".join(tags)
                        else:
                            tags_str = str(tags)
                            
                        md_file.write(f"**Type**: {card_type}  \n")
                        md_file.write(f"**Tags**: {tags_str}\n\n")
                        
                        # Front
                        md_file.write("### Front\n")
                        md_file.write(f"{card.get('front', '')}\n\n")
                        
                        # Back
                        md_file.write("### Back\n")
                        md_file.write(f"{card.get('back', '')}\n\n")
                        
                        md_file.write("---\n\n")
                else:
                    print(f"Warning: {json_file.name} does not contain a list of cards (found {type(cards)}).")
            
            print(f"Converted: {json_file.name} -> {md_filename}")
            
        except json.JSONDecodeError:
            print(f"Error: Failed to decode JSON from {json_file.name}")
        except Exception as e:
            print(f"Error processing {json_file.name}: {e}")

    print("\nConversion complete.")

if __name__ == "__main__":
    SOURCE_DIR = "anki_cards_archival"
    TARGET_DIR = "anki_cards_markdown"
    convert_json_to_md(SOURCE_DIR, TARGET_DIR)
