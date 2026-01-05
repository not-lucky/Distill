
import logging
import json
import genanki
import random
import hashlib
from typing import Dict, Any, List, Optional

from src.anki.models import AnkiModelFactory
from src.anki.renderer import render_markdown

logger = logging.getLogger(__name__)

class DeckGenerator:
    def __init__(self, json_file_path: str, mode: str = "leetcode"):
        """
        Initialize the Anki deck generator.
        
        Args:
            json_file_path: Path to the JSON file containing card data
            mode: Generation mode ('leetcode' or 'cs' or 'physics')
        """
        self.json_file_path = json_file_path
        self.mode = mode
        self.decks: Dict[str, genanki.Deck] = {}
        self.factory = AnkiModelFactory()
        self.basic_model = self.factory.basic_model
        self.mcq_model = self.factory.mcq_model
        self.data = self._load_data()
    
    def _load_data(self) -> List[Dict[str, Any]]:
        """Load data from the JSON file."""
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load data from {self.json_file_path}: {e}")
            raise e

    def _generate_id(self, text: str) -> int:
        """Generate a unique ID based on text content."""
        hash_obj = hashlib.md5(text.encode())
        return int(hash_obj.hexdigest()[:8], 16)
    
    def get_or_create_deck(self, deck_path: str) -> genanki.Deck:
        """Get an existing deck or create a new one."""
        if deck_path not in self.decks:
            deck_id = self._generate_id(deck_path)
            self.decks[deck_path] = genanki.Deck(deck_id, deck_path)
        return self.decks[deck_path]
    
    def _get_prefix(self) -> str:
        """Get the deck prefix based on mode."""
        subject = self.mode.replace('_mcq', '')
        is_mcq_mode = '_mcq' in self.mode or self.mode == 'mcq'
        
        if subject == "cs":
            return "CS_MCQ" if is_mcq_mode else "CS"
        elif subject == "physics":
            return "Physics_MCQ" if is_mcq_mode else "Physics"
        else:
            return "LeetCode_MCQ" if is_mcq_mode else "LeetCode"
    
    def _build_deck_path(
        self, 
        title: str, 
        topic: str,
        category_index: Optional[int] = None,
        category_name: Optional[str] = None,
        problem_index: Optional[int] = None
    ) -> str:
        """
        Build the deck path with optional numbered prefixes.
        
        If category metadata is provided, uses format:
            Prefix::001 Category Name::001 Problem Title
        Otherwise falls back to:
            Prefix::Topic::Title
        """
        prefix = self._get_prefix()
        
        if category_index is not None and category_name is not None and problem_index is not None:
            # Use explicit category metadata with numbering
            cat_str = f"{category_index:03d} {category_name}"
            prob_str = f"{problem_index:03d} {title}"
            return f"{prefix}::{cat_str}::{prob_str}"
        else:
            # Fall back to topic-based naming (legacy behavior)
            return f"{prefix}::{topic}::{title}"
    
    def process(self):
        """Process all cards from the JSON data and add them to appropriate decks."""
        for problem_data in self.data:
            title = problem_data.get('title', 'Unknown Title')
            topic = problem_data.get('topic', 'Unknown Topic')
            difficulty = problem_data.get('difficulty', 'Unknown').replace(" ", "_")
            
            # Get category metadata if available
            category_index = problem_data.get('category_index')
            category_name = problem_data.get('category_name')
            problem_index = problem_data.get('problem_index')
            
            deck_path = self._build_deck_path(
                title, 
                topic,
                category_index=category_index,
                category_name=category_name,
                problem_index=problem_index
            )
            deck = self.get_or_create_deck(deck_path)
            
            for card_data in problem_data.get('cards', []):
                self._add_card_to_deck(deck, card_data, title, topic, difficulty)

    def _add_card_to_deck(self, deck: genanki.Deck, card_data: Dict[str, Any], 
                          title: str, topic: str, difficulty: str):
        """Add a single card to a deck."""
        
        tags = card_data.get('tags', []).copy()
        tags.append(f"topic::{topic.replace(' ', '_')}")
        tags.append(f"difficulty::{difficulty}")
        card_type = card_data.get('card_type', 'General')
        tags.append(f"type::{card_type}")
        
        # Check if MCQ
        is_mcq_mode = 'mcq' in self.mode
        
        if 'options' in card_data and is_mcq_mode:
            self._add_mcq_card(deck, card_data, title, topic, difficulty, tags)
        else:
            self._add_basic_card(deck, card_data, title, topic, difficulty, tags)

    def _add_mcq_card(self, deck: genanki.Deck, card_data: Dict[str, Any],
                      title: str, topic: str, difficulty: str, tags: List[str]):
        question_content = render_markdown(card_data.get('question', ''))
        options = card_data.get('options', [])
        explanation_content = render_markdown(card_data.get('explanation', ''))
        correct_answer = card_data.get('correct_answer', 'A').upper()
        
        # Shuffle options
        shuffled_options, new_correct_answer = self._shuffle_options(options, correct_answer)
        
        # Pad options if less than 4 (though schema dictates 4)
        while len(shuffled_options) < 4:
            shuffled_options.append("")

        fields = [
            question_content,
            render_markdown(shuffled_options[0]),
            render_markdown(shuffled_options[1]),
            render_markdown(shuffled_options[2]),
            render_markdown(shuffled_options[3]),
            new_correct_answer,
            explanation_content,
            card_data.get('card_type', 'MCQ'),
            topic,
            title,
            difficulty,
            ' '.join(tags)
        ]
        
        note = genanki.Note(
            model=self.mcq_model,
            fields=fields,
            tags=tags
        )
        deck.add_note(note)

    def _shuffle_options(self, options: List[str], correct_answer: str):
        if len(options) != 4:
            return options, correct_answer
            
        answer_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
        original_correct_idx = answer_map.get(correct_answer, 0)
        
        indexed_options = list(enumerate(options))
        random.shuffle(indexed_options)
        
        shuffled_opts = [opt for _, opt in indexed_options]
        
        # Find where the original correct answer went
        new_correct_idx = next(i for i, (orig_idx, _) in enumerate(indexed_options) if orig_idx == original_correct_idx)
        new_correct_char = ['A', 'B', 'C', 'D'][new_correct_idx]
        
        return shuffled_opts, new_correct_char

    def _add_basic_card(self, deck: genanki.Deck, card_data: Dict[str, Any],
                        title: str, topic: str, difficulty: str, tags: List[str]):
        front = card_data.get('front', card_data.get('question', ''))
        back = card_data.get('back', card_data.get('explanation', ''))
        
        fields = [
            render_markdown(front),
            render_markdown(back),
            card_data.get('card_type', 'Basic'),
            topic,
            title,
            difficulty,
            ' '.join(tags)
        ]
        
        note = genanki.Note(
            model=self.basic_model,
            fields=fields,
            tags=tags
        )
        deck.add_note(note)

    def save_package(self, output_file: str):
        """Save all decks to a single .apkg package."""
        if not self.decks:
            logger.warning("No decks generated to save.")
            return

        package = genanki.Package(self.decks.values())
        package.write_to_file(output_file)
        logger.info(f"Anki package saved to: {output_file}")
