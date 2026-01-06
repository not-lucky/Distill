
import genanki
import hashlib
from src.anki.styles import BASE_CSS, MCQ_CSS

class AnkiModelFactory:
    def __init__(self):
        self.basic_model = self._create_basic_model()
        self.mcq_model = self._create_mcq_model()

    def _generate_id(self, text_content: str) -> int:
        """
        Generate a unique ID based on text content.
        
        Args:
            text_content: Text to generate ID from
            
        Returns:
            A unique integer ID
        """
        # Use hash to generate consistent IDs
        hash_object = hashlib.md5(text_content.encode())
        # Take first 8 bytes and convert to int
        return int(hash_object.hexdigest()[:8], 16)

    def _create_basic_model(self) -> genanki.Model:
        return genanki.Model(
            self._generate_id('leetcode_basic_model'),
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
            css=BASE_CSS
        )

    def _create_mcq_model(self) -> genanki.Model:
        return genanki.Model(
            self._generate_id('mcq_model_v1'),
            'MCQ Card',
            fields=[
                {'name': 'Question'},
                {'name': 'OptionA'},
                {'name': 'OptionB'},
                {'name': 'OptionC'},
                {'name': 'OptionD'},
                {'name': 'CorrectAnswer'},
                {'name': 'Explanation'},
                {'name': 'CardType'},
                {'name': 'Topic'},
                {'name': 'Problem'},
                {'name': 'Difficulty'},
                {'name': 'Tags'}
            ],
            templates=[
                {
                    'name': 'MCQ Card',
                    'qfmt': '''
                        <div class="card-type">{{CardType}}</div>
                        <div class="source">{{Topic}} - {{Problem}} ({{Difficulty}})</div>
                        <hr>
                        <div class="question">{{Question}}</div>
                        <div class="options">
                            <div class="option" data-option="A"><span class="option-letter">A</span> {{OptionA}}</div>
                            <div class="option" data-option="B"><span class="option-letter">B</span> {{OptionB}}</div>
                            <div class="option" data-option="C"><span class="option-letter">C</span> {{OptionC}}</div>
                            <div class="option" data-option="D"><span class="option-letter">D</span> {{OptionD}}</div>
                        </div>
                    ''',
                    'afmt': '''
                        <div class="card-type">{{CardType}}</div>
                        <div class="source">{{Topic}} - {{Problem}} ({{Difficulty}})</div>
                        <hr>
                        <div class="question">{{Question}}</div>
                        <div class="options answer-revealed">
                            <div class="option {{#CorrectAnswer}}{{#OptionA}}{{/OptionA}}{{/CorrectAnswer}}" data-option="A"><span class="option-letter">A</span> {{OptionA}}</div>
                            <div class="option {{#CorrectAnswer}}{{#OptionB}}{{/OptionB}}{{/CorrectAnswer}}" data-option="B"><span class="option-letter">B</span> {{OptionB}}</div>
                            <div class="option {{#CorrectAnswer}}{{#OptionC}}{{/OptionC}}{{/CorrectAnswer}}" data-option="C"><span class="option-letter">C</span> {{OptionC}}</div>
                            <div class="option {{#CorrectAnswer}}{{#OptionD}}{{/OptionD}}{{/CorrectAnswer}}" data-option="D"><span class="option-letter">D</span> {{OptionD}}</div>
                        </div>
                        <hr id="answer">
                        <div class="correct-answer-badge">✓ Correct Answer: {{CorrectAnswer}}</div>
                        <div class="explanation">{{Explanation}}</div>
                    ''',
                },
            ],
            css=MCQ_CSS
        )
