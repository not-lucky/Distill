import asyncio
from dotenv import load_dotenv

import sys
from src.config import CONCURRENT_REQUESTS
from src.questions import QUESTIONS, CS_QUESTIONS, PHYSICS_QUESTIONS
from src.models import CSProblem, LeetCodeProblem, PhysicsProblem, MCQProblem
from src.prompts import GENIUS_PERSONA_PROMPT_TEMPLATE, PHYSICS_PROMPT_TEMPLATE, MCQ_PROMPT_TEMPLATE, PHYSICS_MCQ_PROMPT_TEMPLATE
from src.setup import initialize_providers
from src.generator import CardGenerator
from src.utils import save_final_deck
from src.logging_config import setup_logging

async def main():
    setup_logging()
    load_dotenv()
    
    # Parse arguments: subject [card_type]
    # Subject: leetcode, cs, physics
    # Card Type: mcq (optional, default is traditional/standard)
    args = sys.argv[1:]
    
    subject = "leetcode"
    card_type = "standard"  # or "mcq"
    
    for arg in args:
        if arg in ["cs", "physics", "leetcode"]:
            subject = arg
        elif arg == "mcq":
            card_type = "mcq"
    
    print(f"Running: Subject={subject.upper()}, Card Type={card_type.upper()}")
    
    # Configure subject-specific settings (questions)
    if subject == "cs":
        target_questions = CS_QUESTIONS
    elif subject == "physics":
        target_questions = PHYSICS_QUESTIONS
    else:  # leetcode
        target_questions = QUESTIONS
    
    # Configure card type-specific settings (prompt and model)
    if card_type == "mcq":
        # Use subject-specific MCQ prompts
        if subject == "physics":
            prompt_template = PHYSICS_MCQ_PROMPT_TEMPLATE
        else:
            prompt_template = MCQ_PROMPT_TEMPLATE
        target_model = MCQProblem
    else:
        # Standard card types based on subject
        if subject == "cs":
            prompt_template = GENIUS_PERSONA_PROMPT_TEMPLATE
            target_model = CSProblem
        elif subject == "physics":
            prompt_template = PHYSICS_PROMPT_TEMPLATE
            target_model = PhysicsProblem
        else:  # leetcode
            prompt_template = None
            target_model = LeetCodeProblem
    
    # Combine subject and card_type for mode identifier
    mode = f"{subject}_{card_type}" if card_type == "mcq" else subject
    
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
