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
    args = sys.argv[1:]
    
    subject = "leetcode"
    card_type = "standard"
    
    for arg in args:
        if arg in ["cs", "physics", "leetcode"]:
            subject = arg
        elif arg == "mcq":
            card_type = "mcq"
    
    print(f"Running: Subject={subject.upper()}, Card Type={card_type.upper()}")
    
    # Retrieve configuration from Registry
    is_mcq = (card_type == "mcq")
    config = SubjectRegistry.get_config(subject, is_mcq)
    
    prompt_template = config.prompt_template
    target_model = config.target_model
    
    # Configure mode identifier
    mode = f"{subject}_{card_type}" if is_mcq else subject
    
    # Initialize Providers
    providers = await initialize_providers()
    if not providers:
        return

    # Combiner (Use the first provider as the combiner)
    combiner = providers[0]

    # Initialize Generator
    generator = CardGenerator(providers, combiner, mode=mode)
    
    # Build question list with metadata
    # Format: List of (category_index, category_name, problem_index, problem_name)
    # For flat lists (cs, physics): (None, None, idx, problem_name)
    questions_with_metadata: List[Tuple] = []
    
    if config.is_categorized:
        # Categorized format (leetcode)
        questions_with_metadata = get_indexed_questions(config.target_questions)
    else:
        # Flat list format (cs, physics)
        for idx, q in enumerate(config.target_questions, start=1):
            questions_with_metadata.append((None, None, idx, q))
    
    # Process Questions
    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
    all_problems = []

    async def sem_task(cat_idx, cat_name, prob_idx, question):
        async with semaphore:
            result = await generator.process_question(
                question, 
                prompt_template, 
                target_model,
                category_index=cat_idx,
                category_name=cat_name,
                problem_index=prob_idx
            )
            if result:
                all_problems.append(result)

    print(f"Starting generation for {len(questions_with_metadata)} questions...")
    tasks = [sem_task(cat_idx, cat_name, prob_idx, q) 
             for cat_idx, cat_name, prob_idx, q in questions_with_metadata]
    await asyncio.gather(*tasks)

    # Save Results
    if all_problems:
        filename = f"{mode}_anki_deck"
        save_final_deck(all_problems, filename)
    else:
        print("No cards generated.")

if __name__ == "__main__":
    asyncio.run(main())
