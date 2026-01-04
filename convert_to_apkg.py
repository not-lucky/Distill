import argparse
import sys
from pathlib import Path
from src.anki.generator import DeckGenerator
from src.logging_config import setup_logging
import logging

logger = logging.getLogger(__name__)

def main():
    setup_logging()
    
    parser = argparse.ArgumentParser(description="Convert LLM JSON output to Anki .apkg")
    parser.add_argument("json_file", help="Path to the JSON file containing synthesized cards")
    parser.add_argument("--mode", default="leetcode", 
                        choices=["cs", "physics", "leetcode", "cs_mcq", "physics_mcq", "leetcode_mcq", "mcq"],
                        help="Mode of generation")
    
    args = parser.parse_args()
    
    input_path = Path(args.json_file)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)
        
    # Determine output filename
    # physics_mcq_anki_deck_20251226T182012.json -> physics_mcq_anki.apkg (approximated)
    # But usually we just take stem and changing extension, or simplify name based on mode
    
    # Simple logic: {mode}_anki.apkg
    # Or preserve original filename stem
    output_filename = f"{input_path.stem}.apkg"
    
    # Better yet, use the logic from the old script to keep consistent simple names if desired:
    # but using stem is safer for multiple files.
    # However, user's previous output example was `cs_mcq_anki.apkg` from `cs_mcq_...json`
    # Let's stick to {stem}.apkg to allow multiple distinct generations without overwrites, 
    # OR we can replicate the old logic if "latest" file overlap is intended.
    # The old logic seemed to output `{mode}_anki.apkg` which overwrites.
    
    # Let's try to match the mode to the filename for cleaner output if possible
    final_output = f"{args.mode}_anki.apkg"
    
    # Wait, the user logic before was a bit weird on filenames. 
    # Let's just output to {input_filename_stem}.apkg to be safe and avoid overwrites
    final_output = f"{input_path.stem}.apkg"

    logger.info(f"Converting {input_path} to {final_output} in mode {args.mode}")
    
    try:
        generator = DeckGenerator(str(input_path), mode=args.mode)
        generator.process()
        generator.save_package(final_output)
        print(f"Successfully created: {final_output}")
    except Exception as e:
        logger.error(f"Failed to create Anki deck: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
