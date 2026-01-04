import asyncio
from dotenv import load_dotenv
import sys

from src.config import CONCURRENT_REQUESTS
from src.config.subjects import SubjectRegistry
from src.setup import initialize_providers
from src.generator import CardGenerator
from src.utils import save_final_deck
from src.logging_config import setup_logging

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
    
    target_questions = config.target_questions
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
    
    # Process Questions
    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
    all_problems = []

    async def sem_task(question):
        async with semaphore:
            result = await generator.process_question(question, prompt_template, target_model)
            if result:
                all_problems.append(result)

    print(f"Starting generation for {len(target_questions)} questions...")
    tasks = [sem_task(q) for q in target_questions]
    await asyncio.gather(*tasks)

    # Save Results
    if all_problems:
        filename = f"{mode}_anki_deck"
        save_final_deck(all_problems, filename)
    else:
        print("No cards generated.")

if __name__ == "__main__":
    asyncio.run(main())
