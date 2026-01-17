
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
    def __init__(self, json_file_path: str, deck_prefix: str = "LeetCode"):
        """
        Initialize the Anki deck generator.

        Args:
            json_file_path: Path to the JSON file containing card data
            deck_prefix: Deck name prefix (e.g., "LeetCode", "CS_MCQ")
        """
        self.json_file_path = json_file_path
        self.deck_prefix = deck_prefix
        self.deck_collection: Dict[str, genanki.Deck] = {}
        self.model_factory = AnkiModelFactory()
        self.basic_card_model = self.model_factory.basic_model
        self.mcq_card_model = self.model_factory.mcq_model
        self.card_data = self._load_data()
    
    def _load_data(self) -> List[Dict[str, Any]]:
        """Load data from the JSON file."""
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as input_file:
                return json.load(input_file)
        except Exception as error:
            logger.error(f"Failed to load data from {self.json_file_path}: {error}")
            raise error

    def _generate_id(self, text_content: str) -> int:
        """Generate a unique ID based on text content."""
        hash_object = hashlib.md5(text_content.encode())
        return int(hash_object.hexdigest()[:8], 16)
    
    def get_or_create_deck(self, deck_path: str) -> genanki.Deck:
        """Get an existing deck or create a new one."""
        if deck_path not in self.deck_collection:
            deck_id = self._generate_id(deck_path)
            self.deck_collection[deck_path] = genanki.Deck(deck_id, deck_path)
        return self.deck_collection[deck_path]
    
    def _get_prefix(self) -> str:
        """Get the deck prefix."""
        return self.deck_prefix
    
    def _build_deck_path(
        self, 
        problem_title: str, 
        topic_name: str,
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
        deck_prefix = self._get_prefix()
        
        if category_index is not None and category_name is not None and problem_index is not None:
            # Use explicit category metadata with numbering
            formatted_category = f"{category_index:03d} {category_name}"
            formatted_problem = f"{problem_index:03d} {problem_title}"
            return f"{deck_prefix}::{formatted_category}::{formatted_problem}"
        else:
            # Fall back to topic-based naming (legacy behavior)
            return f"{deck_prefix}::{topic_name}::{problem_title}"
    
    def process(self):
        """Process all cards from the JSON data and add them to appropriate decks."""
        for problem_data in self.card_data:
            problem_title = problem_data.get('title', 'Unknown Title')
            topic_name = problem_data.get('topic', 'Unknown Topic')
            difficulty_level = problem_data.get('difficulty', 'Unknown').replace(" ", "_")
            
            # Get category metadata if available
            category_index = problem_data.get('category_index')
            category_name = problem_data.get('category_name')
            problem_index = problem_data.get('problem_index')
            
            deck_path = self._build_deck_path(
                problem_title, 
                topic_name,
                category_index=category_index,
                category_name=category_name,
                problem_index=problem_index
            )
            target_deck = self.get_or_create_deck(deck_path)
            
            for card_data in problem_data.get('cards', []):
                self._add_card_to_deck(target_deck, card_data, problem_title, topic_name, difficulty_level)

    def _add_card_to_deck(self, target_deck: genanki.Deck, card_data: Dict[str, Any], 
                          problem_title: str, topic_name: str, difficulty_level: str):
        """Add a single card to a deck."""
        
        card_tags = card_data.get('tags', []).copy()
        card_tags.append(f"topic::{topic_name.replace(' ', '_')}")
        card_tags.append(f"difficulty::{difficulty_level}")
        card_type_value = card_data.get('card_type', 'General')
        card_tags.append(f"type::{card_type_value}")
        
        # Check if MCQ mode (based on deck prefix containing MCQ)
        is_mcq_mode = 'MCQ' in self.deck_prefix
        
        if 'options' in card_data and is_mcq_mode:
            self._add_mcq_card(target_deck, card_data, problem_title, topic_name, difficulty_level, card_tags)
        else:
            self._add_basic_card(target_deck, card_data, problem_title, topic_name, difficulty_level, card_tags)

    def _add_mcq_card(self, target_deck: genanki.Deck, card_data: Dict[str, Any],
                      problem_title: str, topic_name: str, difficulty_level: str, card_tags: List[str]):
        question_html = render_markdown(card_data.get('question', ''))
        answer_options = card_data.get('options', [])
        explanation_html = render_markdown(card_data.get('explanation', ''))
        correct_answer_letter = card_data.get('correct_answer', 'A').upper()
        
        # Shuffle options
        shuffled_options, new_correct_answer_letter = self._shuffle_options(answer_options, correct_answer_letter)
        
        # Pad options if less than 4 (though schema dictates 4)
        while len(shuffled_options) < 4:
            shuffled_options.append("")

        note_fields = [
            question_html,
            render_markdown(shuffled_options[0]),
            render_markdown(shuffled_options[1]),
            render_markdown(shuffled_options[2]),
            render_markdown(shuffled_options[3]),
            new_correct_answer_letter,
            explanation_html,
            card_data.get('card_type', 'MCQ'),
            topic_name,
            problem_title,
            difficulty_level,
            ' '.join(card_tags)
        ]
        
        anki_note = genanki.Note(
            model=self.mcq_card_model,
            fields=note_fields,
            tags=card_tags
        )
        target_deck.add_note(anki_note)

    def _shuffle_options(self, answer_options: List[str], correct_answer_letter: str):
        if len(answer_options) != 4:
            return answer_options, correct_answer_letter
            
        letter_to_index_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
        original_correct_index = letter_to_index_map.get(correct_answer_letter, 0)
        
        indexed_options = list(enumerate(answer_options))
        random.shuffle(indexed_options)
        
        shuffled_option_texts = [option_text for _, option_text in indexed_options]
        
        # Find where the original correct answer went
        new_correct_index = next(index for index, (original_index, _) in enumerate(indexed_options) if original_index == original_correct_index)
        new_correct_letter = ['A', 'B', 'C', 'D'][new_correct_index]
        
        return shuffled_option_texts, new_correct_letter

    def _add_basic_card(self, target_deck: genanki.Deck, card_data: Dict[str, Any],
                        problem_title: str, topic_name: str, difficulty_level: str, card_tags: List[str]):
        front_content = card_data.get('front', card_data.get('question', ''))
        back_content = card_data.get('back', card_data.get('explanation', ''))
        
        note_fields = [
            render_markdown(front_content),
            render_markdown(back_content),
            card_data.get('card_type', 'Basic'),
            topic_name,
            problem_title,
            difficulty_level,
            ' '.join(card_tags)
        ]
        
        anki_note = genanki.Note(
            model=self.basic_card_model,
            fields=note_fields,
            tags=card_tags
        )
        target_deck.add_note(anki_note)

    def save_package(self, output_file_path: str):
        """Save all decks to a single .apkg package."""
        if not self.deck_collection:
            logger.warning("No decks generated to save.")
            return

        anki_package = genanki.Package(self.deck_collection.values())
        anki_package.write_to_file(output_file_path)
        logger.info(f"Anki package saved to: {output_file_path}")
