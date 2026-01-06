import asyncio
from dotenv import load_dotenv
import sys
from typing import List, Tuple

from src.config import CONCURRENT_REQUESTS
from src.config.subjects import SubjectRegistry
from src.setup import initialize_providers
from src.generator import CardGenerator
from src.utils import save_final_deck
from src.logging_config import setup_logging
from src.questions import get_indexed_questions

async def main():
    setup_logging()
    load_dotenv()
    
    # Parse arguments: subject [card_type]
    command_line_arguments = sys.argv[1:]
    
    subject_name = "leetcode"
    card_type_name = "standard"
    
    for argument in command_line_arguments:
        if argument in ["cs", "physics", "leetcode"]:
            subject_name = argument
        elif argument == "mcq":
            card_type_name = "mcq"
    
    print(f"Running: Subject={subject_name.upper()}, Card Type={card_type_name.upper()}")
    
    # Retrieve configuration from Registry
    is_multiple_choice = (card_type_name == "mcq")
    subject_config = SubjectRegistry.get_config(subject_name, is_multiple_choice)
    
    prompt_template = subject_config.prompt_template
    target_model_class = subject_config.target_model
    
    # Configure mode identifier
    generation_mode = f"{subject_name}_{card_type_name}" if is_multiple_choice else subject_name
    
    # Initialize Providers
    llm_providers = await initialize_providers()
    if not llm_providers:
        return

    # Combiner (Use the first provider as the combiner)
    card_combiner_provider = llm_providers[0]

    # Initialize Generator
    card_generator = CardGenerator(llm_providers, card_combiner_provider, mode=generation_mode)
    
    # Build question list with metadata
    # Format: List of (category_index, category_name, problem_index, problem_name)
    # For flat lists (cs, physics): (None, None, idx, problem_name)
    questions_with_metadata: List[Tuple] = []
    
    if subject_config.is_categorized:
        # Categorized format (leetcode)
        questions_with_metadata = get_indexed_questions(subject_config.target_questions)
    else:
        # Flat list format (cs, physics)
        for question_index, question_text in enumerate(subject_config.target_questions, start=1):
            questions_with_metadata.append((None, None, question_index, question_text))
    
    # Process Questions
    concurrency_semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
    all_generated_problems = []

    async def process_question_with_semaphore(category_index, category_name, problem_index, question_text):
        async with concurrency_semaphore:
            generation_result = await card_generator.process_question(
                question_text, 
                prompt_template, 
                target_model_class,
                category_index=category_index,
                category_name=category_name,
                problem_index=problem_index
            )
            if generation_result:
                all_generated_problems.append(generation_result)

    print(f"Starting generation for {len(questions_with_metadata)} questions...")
    generation_tasks = [process_question_with_semaphore(category_index, category_name, problem_index, question_text) 
             for category_index, category_name, problem_index, question_text in questions_with_metadata]
    await asyncio.gather(*generation_tasks)

    # Save Results
    if all_generated_problems:
        output_filename = f"{generation_mode}_anki_deck"
        save_final_deck(all_generated_problems, output_filename)
    else:
        print("No cards generated.")

if __name__ == "__main__":
    asyncio.run(main())
