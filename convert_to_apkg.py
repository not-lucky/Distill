import json
import genanki
import random
import hashlib
import argparse
import re
import html
from pathlib import Path
from typing import List, Dict, Any

import markdown
import bleach
from src.logging_config import setup_logging
import logging

logger = logging.getLogger(__name__)

class AnkiDeckGenerator:
    def __init__(self, json_file_path: str, mode: str = "leetcode"):
        """
        Initialize the Anki deck generator with a JSON file path.
        
        Args:
            json_file_path: Path to the JSON file containing card data
            mode: Generation mode ('leetcode' or 'cs' or 'physics')
        """
        self.json_file_path = json_file_path
        self.mode = mode
        self.decks = {}
        self.models = {}
        self.load_data()
        self.create_models()
    
    def load_data(self):
        """Load data from the JSON file."""
        with open(self.json_file_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
    
    def generate_id(self, text: str) -> int:
        """
        Generate a unique ID based on text content.
        
        Args:
            text: Text to generate ID from
            
        Returns:
            A unique integer ID
        """
        # Use hash to generate consistent IDs
        hash_obj = hashlib.md5(text.encode())
        # Take first 8 bytes and convert to int
        return int(hash_obj.hexdigest()[:8], 16)
    
    def render_markdown(self, text: str) -> str:
        """
        Convert markdown text to HTML using the markdown library.
        
        Args:
            text: Markdown text
            
        Returns:
            HTML formatted text
        """
        if not text:
            return ""

        # Fix double-escaped newlines inside code blocks only using regex split
        # This splits by code blocks (capturing the delimiters so we keep them)
        parts = re.split(r'(```.*?```)', text, flags=re.DOTALL)
        for i in range(len(parts)):
            # If it starts and ends with ```, it's a code block
            if parts[i].startswith('```') and parts[i].endswith('```'):
                parts[i] = parts[i].replace('\\n', '\n')
        
        text = "".join(parts)
            
        # Configure extensions
        html_content = markdown.markdown(
            text,
            extensions=['fenced_code', 'codehilite', 'tables', 'nl2br', 'sane_lists'],
            extension_configs={
                'codehilite': {
                    'css_class': 'highlight',
                    'linenums': False,
                    'use_pygments': True,
                    'noclasses': False
                }
            }
        )
        
        # Sanitize HTML to escape invalid tags (like <target) while preserving valid ones
        allowed_tags = [
            'a', 'b', 'blockquote', 'br', 'code', 'div', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
            'hr', 'i', 'li', 'ol', 'p', 'pre', 'span', 'strong', 'table', 'tbody', 'td', 'th', 
            'thead', 'tr', 'ul'
        ]
        allowed_attrs = {
            '*': ['class', 'style'],
            'a': ['href', 'title', 'target'],
            'img': ['src', 'alt', 'title'],
        }
        
        clean_html = bleach.clean(
            html_content, 
            tags=allowed_tags, 
            attributes=allowed_attrs, 
            strip=False
        )
        
        return clean_html
    
    def create_models(self):
        """Create Anki note models for different card types."""
        # Basic model for all card types with Catppuccin theme
        self.basic_model = genanki.Model(
            self.generate_id('leetcode_basic_model'),
            'LeetCode Basic',
            fields=[
                {'name': 'Front'},
                {'name': 'Back'},
                {'name': 'CardType'},
                {'name': 'Topic'},
                {'name': 'Problem'},
                {'name': 'Difficulty'},
                {'name': 'Tags'}
            ],
            templates=[
                {
                    'name': 'Card 1',
                    'qfmt': '''
                        <div class="card-type">{{CardType}}</div>
                        <div class="source">{{Topic}} - {{Problem}} ({{Difficulty}})</div>
                        <hr>
                        <div class="question">{{Front}}</div>
                    ''',
                    'afmt': '''
                        <div class="card-type">{{CardType}}</div>
                        <div class="source">{{Topic}} - {{Problem}} ({{Difficulty}})</div>
                        <hr>
                        <div class="question">{{Front}}</div>
                        <hr id="answer">
                        <div class="answer">{{Back}}</div>
                    ''',
                },
            ],
            css='''
                /* Catppuccin Mocha & Latte Theme Variables */
                .card {
                    /* Default to Latte (light) colors */
                    --ctp-base: #eff1f5;
                    --ctp-mantle: #e6e9ef;
                    --ctp-crust: #dce0e8;
                    --ctp-surface0: #ccd0da;
                    --ctp-surface1: #bcc0cc;
                    --ctp-surface2: #acb0be;
                    --ctp-overlay0: #9ca0b0;
                    --ctp-overlay1: #8c8fa1;
                    --ctp-overlay2: #7c7f93;
                    --ctp-text: #4c4f69;
                    --ctp-subtext1: #5c5f77;
                    --ctp-subtext0: #6c6f85;
                    --ctp-green: #40a02b;
                    --ctp-blue: #1e66f5;
                    --ctp-mauve: #8839ef;
                    --ctp-red: #d20f39;
                    --ctp-peach: #fe640b;
                    --ctp-yellow: #df8e1d;
                    --ctp-teal: #179299;
                    --ctp-pink: #ea76cb;
                    --ctp-lavender: #7287fd;
                    --ctp-rosewater: #dc8a78;
                    --ctp-flamingo: #dd7878;
                    --ctp-sky: #04a5e5;
                    --ctp-sapphire: #209fb5;
                    --ctp-maroon: #e64553;
                }
                
                /* Dark mode - Catppuccin Mocha */
                .night_mode .card,
                .nightMode .card,
                .night-mode .card,
                [class*="night"] .card {
                    --ctp-base: #1e1e2e;
                    --ctp-mantle: #181825;
                    --ctp-crust: #11111b;
                    --ctp-surface0: #313244;
                    --ctp-surface1: #45475a;
                    --ctp-surface2: #585b70;
                    --ctp-overlay0: #6c7086;
                    --ctp-overlay1: #7f849c;
                    --ctp-overlay2: #9399b2;
                    --ctp-text: #cdd6f4;
                    --ctp-subtext1: #bac2de;
                    --ctp-subtext0: #a6adc8;
                    --ctp-green: #a6e3a1;
                    --ctp-blue: #89b4fa;
                    --ctp-mauve: #cba6f7;
                    --ctp-red: #f38ba8;
                    --ctp-peach: #fab387;
                    --ctp-yellow: #f9e2af;
                    --ctp-teal: #94e2d5;
                    --ctp-pink: #f5c2e7;
                    --ctp-lavender: #b4befe;
                    --ctp-rosewater: #f5e0dc;
                    --ctp-flamingo: #f2cdcd;
                    --ctp-sky: #89dceb;
                    --ctp-sapphire: #74c7ec;
                    --ctp-maroon: #eba0ac;
                }
                
                .card {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
                    font-size: 18px;
                    text-align: left;
                    color: var(--ctp-text);
                    background-color: var(--ctp-base);
                    padding: 25px;
                    line-height: 1.7;
                    min-height: 100vh;
                    box-sizing: border-box;
                }
                
                .card-type {
                    background: linear-gradient(135deg, var(--ctp-mauve), var(--ctp-blue));
                    color: var(--ctp-crust);
                    padding: 6px 14px;
                    border-radius: 8px;
                    display: inline-block;
                    font-size: 13px;
                    margin-bottom: 12px;
                    text-transform: uppercase;
                    font-weight: 700;
                    letter-spacing: 0.5px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }
                
                .source {
                    color: var(--ctp-subtext0);
                    font-size: 15px;
                    font-style: italic;
                    margin-bottom: 12px;
                    padding: 8px 12px;
                    background-color: var(--ctp-mantle);
                    border-radius: 6px;
                    border-left: 3px solid var(--ctp-lavender);
                }
                
                .question {
                    font-size: 20px;
                    font-weight: 600;
                    color: var(--ctp-text);
                    margin: 25px 0;
                    padding: 15px;
                    background-color: var(--ctp-surface0);
                    border-radius: 10px;
                    border: 1px solid var(--ctp-surface1);
                    letter-spacing: 0.3px;
                }
                
                .answer {
                    font-size: 18px;
                    color: var(--ctp-subtext1);
                    margin: 25px 0;
                    padding: 15px;
                    background-color: var(--ctp-mantle);
                    border-radius: 10px;
                    border: 1px solid var(--ctp-surface0);
                    line-height: 1.8;
                }
                
                /* Code block styling */
                .highlight {
                    margin: 16px 0;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }
                
                .highlight pre {
                    background-color: var(--ctp-crust);
                    border: 1px solid var(--ctp-surface0);
                    padding: 16px;
                    margin: 0;
                    overflow-x: auto;
                    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace;
                    font-size: 15px;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                    line-height: 1.6;
                }
                
                /* Inline code styling */
                code {
                    background-color: var(--ctp-surface0);
                    color: var(--ctp-pink);
                    padding: 3px 6px;
                    border-radius: 4px;
                    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace;
                    font-size: 15px;
                    font-weight: 500;
                    border: 1px solid var(--ctp-surface1);
                }
                
                .highlight code {
                    background-color: transparent;
                    color: var(--ctp-text);
                    padding: 0;
                    border: none;
                    font-weight: normal;
                }
                
                /* Pygments Syntax Highlighting with Catppuccin */
                .highlight .hll { background-color: var(--ctp-surface2); }
                .highlight .c, .highlight .ch, .highlight .cm, .highlight .cpf, .highlight .c1, .highlight .cs { color: var(--ctp-overlay0); font-style: italic; } /* Comments */
                .highlight .err { color: var(--ctp-red); background-color: var(--ctp-mantle); } /* Error */
                .highlight .k, .highlight .kc, .highlight .kd, .highlight .kn, .highlight .kp, .highlight .kr, .highlight .kt { color: var(--ctp-mauve); font-weight: bold; } /* Keywords */
                .highlight .m, .highlight .mb, .highlight .mf, .highlight .mh, .highlight .mi, .highlight .mo, .highlight .il { color: var(--ctp-peach); } /* Numbers */
                .highlight .s, .highlight .sa, .highlight .sb, .highlight .sc, .highlight .dl, .highlight .sd, .highlight .s2, .highlight .se, .highlight .sh, .highlight .si, .highlight .sx, .highlight .sr, .highlight .s1, .highlight .ss { color: var(--ctp-green); } /* Strings */
                .highlight .na, .highlight .py { color: var(--ctp-teal); } /* Attributes */
                .highlight .nb, .highlight .bp { color: var(--ctp-lavender); } /* Builtins */
                .highlight .nc, .highlight .nn { color: var(--ctp-yellow); font-weight: bold; } /* Classes */
                .highlight .no, .highlight .nv, .highlight .vc, .highlight .vg, .highlight .vi, .highlight .vm { color: var(--ctp-blue); } /* Variables */
                .highlight .nd, .highlight .ni { color: var(--ctp-pink); } /* Decorators, Entities */
                .highlight .ne, .highlight .fm { color: var(--ctp-sapphire); font-weight: bold; } /* Exceptions, Functions */
                .highlight .nf { color: var(--ctp-blue); font-weight: bold; } /* Functions */
                .highlight .nl { color: var(--ctp-rosewater); } /* Labels */
                .highlight .nt { color: var(--ctp-red); font-weight: bold; } /* Tags */
                .highlight .ow { color: var(--ctp-sky); font-weight: bold; } /* Operators */
                .highlight .w { color: var(--ctp-surface1); } /* Whitespace */
                .highlight .cp { color: var(--ctp-flamingo); font-weight: bold; } /* Preprocessor */
                .highlight .gd { color: var(--ctp-red); background-color: var(--ctp-mantle); } /* Deleted */
                .highlight .ge { font-style: italic; color: var(--ctp-text); } /* Emph */
                .highlight .gh { color: var(--ctp-lavender); font-weight: bold; } /* Heading */
                .highlight .gi { color: var(--ctp-green); background-color: var(--ctp-mantle); } /* Inserted */
                .highlight .go { color: var(--ctp-subtext0); } /* Output */
                .highlight .gp { color: var(--ctp-overlay2); font-weight: bold; } /* Prompt */
                .highlight .gs { font-weight: bold; } /* Strong */
                .highlight .gu { color: var(--ctp-lavender); font-weight: bold; } /* Subheading */
                .highlight .gt { color: var(--ctp-red); } /* Traceback */
                .highlight .gr { color: var(--ctp-red); } /* Generic Error */
                
                hr {
                    border: none;
                    border-top: 2px solid var(--ctp-surface1);
                    margin: 20px 0;
                    opacity: 0.5;
                }
                
                /* Links styling */
                a {
                    color: var(--ctp-blue);
                    text-decoration: none;
                    border-bottom: 1px dotted var(--ctp-blue);
                    transition: all 0.2s ease;
                }
                
                a:hover {
                    color: var(--ctp-sky);
                    border-bottom-color: var(--ctp-sky);
                }
                
                /* Lists styling */
                ul, ol {
                    color: var(--ctp-text);
                    padding-left: 25px;
                    margin: 15px 0;
                }
                
                li {
                    margin: 8px 0;
                    color: var(--ctp-subtext1);
                }
                
                /* Strong and emphasis */
                strong, b {
                    color: var(--ctp-lavender);
                    font-weight: 600;
                }
                
                em, i {
                    color: var(--ctp-yellow);
                    font-style: italic;
                }
                
                /* Blockquotes */
                blockquote {
                    border-left: 4px solid var(--ctp-mauve);
                    padding-left: 20px;
                    margin: 20px 0;
                    color: var(--ctp-subtext0);
                    font-style: italic;
                    background-color: var(--ctp-mantle);
                    padding: 15px 20px;
                    border-radius: 0 8px 8px 0;
                }
                
                /* Tables */
                table {
                    border-collapse: collapse;
                    width: 100%;
                    margin: 20px 0;
                }
                
                th {
                    background-color: var(--ctp-surface0);
                    color: var(--ctp-lavender);
                    padding: 12px;
                    text-align: left;
                    font-weight: 600;
                    border: 1px solid var(--ctp-surface1);
                }
                
                td {
                    padding: 10px;
                    border: 1px solid var(--ctp-surface1);
                    color: var(--ctp-text);
                }
                
                tr:nth-child(even) {
                    background-color: var(--ctp-mantle);
                }
                
                /* Ensure good contrast for all text */
                * {
                    text-shadow: none !important;
                }
                
                /* Mobile responsiveness */
                @media (max-width: 600px) {
                    .card {
                        padding: 15px;
                        font-size: 16px;
                    }
                    
                    .question {
                        font-size: 18px;
                    }
                    
                    .answer {
                        font-size: 16px;
                    }
                }
            '''
        )
    
    def get_or_create_deck(self, deck_path: str) -> genanki.Deck:
        """
        Get an existing deck or create a new one.
        
        Args:
            deck_path: Hierarchical path for the deck (e.g., "LeetCode::Arrays::Two Sum")
            
        Returns:
            A genanki.Deck object
        """
        if deck_path not in self.decks:
            deck_id = self.generate_id(deck_path)
            self.decks[deck_path] = genanki.Deck(deck_id, deck_path)
        return self.decks[deck_path]
    
    def process_cards(self):
        """Process all cards from the JSON data and add them to appropriate decks."""
        for problem_data in self.data:
            title = problem_data['title']
            topic = problem_data['topic']
            difficulty = problem_data['difficulty']
            
            # Create hierarchical deck structure: Mode::Topic::Title
            if self.mode == "cs":
                prefix = "CS"
            elif self.mode == "physics":
                prefix = "Physics"
            else:
                prefix = "LeetCode"
                
            deck_path = f"{prefix}::{topic}::{title}"
            deck = self.get_or_create_deck(deck_path)
            
            # Process each card in the deck
            for card_data in problem_data['cards']:
                self.add_card_to_deck(deck, card_data, title, topic, difficulty)
    
    def add_card_to_deck(self, deck: genanki.Deck, card_data: Dict[str, Any], 
                         title: str, topic: str, difficulty: str):
        """
        Add a single card to a deck.
        
        Args:
            deck: The deck to add the card to
            card_data: Dictionary containing card information
            title: Problem title
            topic: Problem topic
            difficulty: Problem difficulty
        """
        # Format tags
        tags = card_data['tags']
        tags.append(f"topic::{topic.replace(' ', '_')}")
        tags.append(f"difficulty::{difficulty}")
        tags.append(f"type::{card_data['card_type']}")
        
        # Process front and back content to handle code formatting
        front_content = self.render_markdown(card_data['front'])
        back_content = self.render_markdown(card_data['back'])
        
        # Create the note
        note = genanki.Note(
            model=self.basic_model,
            fields=[
                front_content,
                back_content,
                card_data['card_type'],
                topic,
                title,
                difficulty,
                ' '.join(tags)
            ],
            tags=tags
        )
        
        deck.add_note(note)
    
    def generate_package(self, output_path: str = "leetcode_anki.apkg"):
        """
        Generate the Anki package file.
        
        Args:
            output_path: Path for the output .apkg file
        """
        # Process all cards
        self.process_cards()
        
        # Create the package
        package = genanki.Package(list(self.decks.values()))
        
        # Write the package
        package.write_to_file(output_path)
        
        # Log summary
        logger.info("\n✅ Anki package generated successfully!")
        logger.info(f"📦 Output file: {output_path}")
        logger.info(f"📚 Total decks created: {len(self.decks)}")
        
        total_cards = sum(len(deck.notes) for deck in self.decks.values())
        logger.info(f"🎴 Total cards created: {total_cards}")
        
        logger.info("\n📂 Deck structure:")
        for deck_path in sorted(self.decks.keys()):
            deck = self.decks[deck_path]
            indent_level = deck_path.count('::')
            indent = "  " * indent_level
            deck_short_name = deck_path.split('::')[-1]
            logger.info(f"{indent}└─ {deck_short_name} ({len(deck.notes)} cards)")

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(
        description='Generate Anki decks from LeetCode JSON data'
    )
    parser.add_argument(
        'input_file',
        help='Path to the input JSON file'
    )
    parser.add_argument(
        '-o', '--output',
        default=None,
        help='Output file name (default: leetcode_anki.apkg or cs_anki.apkg based on mode)'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate JSON schema before processing'
    )
    
    parser.add_argument(
        '--mode',
        choices=['leetcode', 'cs', 'physics'],
        default=None,
        help='Generation mode (default: inferred from filename or leetcode)'
    )
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not Path(args.input_file).exists():
        logger.error(f"❌ Error: Input file '{args.input_file}' not found!")
        return 1
        
    # Infer mode if not provided
    if args.mode is None:
        if "cs" in Path(args.input_file).name.lower() or "cs_" in Path(args.input_file).name.lower():
            args.mode = 'cs'
        elif "physics" in Path(args.input_file).name.lower():
            args.mode = 'physics'
        else:
            args.mode = 'leetcode'
            
    # Set default output filename if not provided
    if args.output is None:
        if args.mode == 'cs':
            args.output = 'cs_anki.apkg'
        elif args.mode == 'physics':
            args.output = 'physics_anki.apkg'
        else:
            args.output = 'leetcode_anki.apkg'
    
    try:
        # Create generator and process
        generator = AnkiDeckGenerator(args.input_file, args.mode)
        
        # Optional: Validate data structure
        if args.validate:
            logger.info("✓ JSON structure validated successfully")
        
        # Generate the package
        generator.generate_package(args.output)
        
        return 0
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error: Invalid JSON in input file - {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    setup_logging()
    exit(main())
