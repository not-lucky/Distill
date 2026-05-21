"""
MCQ (multiple-choice question) shuffling for LLM2Deck.

The pipeline emits cards with the correct answer letter fixed (A/B/C/D); we
shuffle the option order at compile time so the correct letter is not always
in the same slot. Duplicate option text is handled correctly by tracking
original indices instead of using list.index().
"""

import random


def shuffle_mcq_options(
    options: list[str], correct_answer: str
) -> tuple[list[str], str]:
    """
    Shuffles MCQ options while preserving the correct answer index mapping.
    Pads options list with fewer than 4 choices with empty strings.
    Returns: (shuffled_options, new_correct_answer_letter)
    """
    # Enforce safe type handling for choices list
    if not isinstance(options, (list, tuple)):
        options = []
    else:
        options = [str(o) for o in options if o is not None]

    # Enforce safe type handling for correct answer letter
    if not isinstance(correct_answer, str):
        correct_answer = "A"

    # Map correct answer letter to index (A->0, B->1, C->2, D->3)
    correct_letter = correct_answer.upper()
    correct_idx = ord(correct_letter) - ord("A")

    # Fallback to first option if the correct index is out of bounds
    if correct_idx < 0 or correct_idx >= len(options):
        correct_idx = 0

    # Bundle each option with its original index to prevent loss of correct answer mapping
    # when options contain duplicate values (standard list.index() would only find the first one).
    indexed_options = list(enumerate(options))

    random.shuffle(indexed_options)

    shuffled_texts: list[str] = []
    new_correct_idx = 0
    for new_idx, (orig_idx, text) in enumerate(indexed_options):
        if orig_idx == correct_idx:
            new_correct_idx = new_idx
        shuffled_texts.append(text)

    # Pad to exactly 4 choices since MCQ card templates strictly expect OptionA through OptionD
    while len(shuffled_texts) < 4:
        shuffled_texts.append("")

    # Map new index back to letter
    new_correct_answer_letter = chr(ord("A") + new_correct_idx)

    return shuffled_texts, new_correct_answer_letter
