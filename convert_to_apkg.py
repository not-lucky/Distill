import argparse
import re
import sys
from pathlib import Path
from src.anki.generator import DeckGenerator
from src.logging_config import setup_logging
import logging

logger = logging.getLogger(__name__)

VALID_MODES = ["cs", "physics", "leetcode", "cs_mcq", "physics_mcq", "leetcode_mcq", "mcq"]

def detect_mode_from_filename(filename: str) -> str:
    """
    Auto-detect mode from JSON filename.
    
    Examples:
        cs_anki_deck_20251230.json -> cs
        physics_mcq_anki_deck_20251230.json -> physics_mcq
        leetcode_anki_deck_20251230.json -> leetcode
    
    Returns:
        Detected mode, or 'leetcode' as fallback
    """
    stem = Path(filename).stem.lower()
    
    # Try to match mcq variants first (more specific)
    for mode in ["cs_mcq", "physics_mcq", "leetcode_mcq"]:
        if stem.startswith(mode):
            return mode
    
    # Then try base modes
    for mode in ["cs", "physics", "leetcode"]:
        if stem.startswith(mode):
            return mode
    
    # Check for generic mcq
    if "mcq" in stem:
        return "mcq"
    
    return "leetcode"  # Default fallback

def main():
    setup_logging()
    
    argument_parser = argparse.ArgumentParser(description="Convert LLM JSON output to Anki .apkg")
    argument_parser.add_argument("json_file", help="Path to the JSON file containing synthesized cards")
    argument_parser.add_argument("--mode", default=None, 
                        choices=VALID_MODES,
                        help="Mode of generation (auto-detected from filename if not specified)")
    
    parsed_arguments = argument_parser.parse_args()
    
    # Auto-detect mode if not specified
    if parsed_arguments.mode is None:
        detected_mode = detect_mode_from_filename(parsed_arguments.json_file)
        logger.info(f"Auto-detected mode: {detected_mode}")
        parsed_arguments.mode = detected_mode
    
    input_file_path = Path(parsed_arguments.json_file)
    if not input_file_path.exists():
        logger.error(f"Input file not found: {input_file_path}")
        sys.exit(1)
        
    # Determine output filename
    # physics_mcq_anki_deck_20251226T182012.json -> physics_mcq_anki.apkg (approximated)
    # But usually we just take stem and changing extension, or simplify name based on mode
    
    # Simple logic: {mode}_anki.apkg
    # Or preserve original filename stem
    output_filename = f"{input_file_path.stem}.apkg"
    
    # Better yet, use the logic from the old script to keep consistent simple names if desired:
    # but using stem is safer for multiple files.
    # However, user's previous output example was `cs_mcq_anki.apkg` from `cs_mcq_...json`
    # Let's stick to {stem}.apkg to allow multiple distinct generations without overwrites, 
    # OR we can replicate the old logic if "latest" file overlap is intended.
    # The old logic seemed to output `{mode}_anki.apkg` which overwrites.
    
    # Let's try to match the mode to the filename for cleaner output if possible
    final_output_path = f"{parsed_arguments.mode}_anki.apkg"
    
    # Wait, the user logic before was a bit weird on filenames. 
    # Let's just output to {input_filename_stem}.apkg to be safe and avoid overwrites
    final_output_path = f"{input_file_path.stem}.apkg"

    logger.info(f"Converting {input_file_path} to {final_output_path} in mode {parsed_arguments.mode}")
    
    try:
        deck_generator = DeckGenerator(str(input_file_path), mode=parsed_arguments.mode)
        deck_generator.process()
        deck_generator.save_package(final_output_path)
        print(f"Successfully created: {final_output_path}")
    except Exception as error:
        logger.error(f"Failed to create Anki deck: {error}")
        sys.exit(1)

if __name__ == "__main__":
    main()
