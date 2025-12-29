import asyncio
from dotenv import load_dotenv

import sys
from src.config import CONCURRENT_REQUESTS
from src.questions import QUESTIONS, CS_QUESTIONS, PHYSICS_QUESTIONS
from src.models import CSProblem, LeetCodeProblem, PhysicsProblem
from src.prompts import GENIUS_PERSONA_PROMPT_TEMPLATE, PHYSICS_PROMPT_TEMPLATE
from src.setup import initialize_providers
from src.generator import CardGenerator
from src.utils import save_final_deck
from src.logging_config import setup_logging

async def main():
    setup_logging()
    load_dotenv()
    
    # Mode Selection
    mode = "leetcode"
    if len(sys.argv) > 1 and sys.argv[1] == "cs":
        mode = "cs"
    elif len(sys.argv) > 1 and sys.argv[1] == "physics":
        mode = "physics"
        
    print(f"Running in {mode.upper()} mode.")
    
    target_questions = CS_QUESTIONS if mode == "cs" else (PHYSICS_QUESTIONS if mode == "physics" else QUESTIONS)
    prompt_template = GENIUS_PERSONA_PROMPT_TEMPLATE if mode == "cs" else (PHYSICS_PROMPT_TEMPLATE if mode == "physics" else None)
    target_model = CSProblem if mode == "cs" else (PhysicsProblem if mode == "physics" else LeetCodeProblem)
    
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
        filename = f"cs_anki_deck" if mode == "cs" else (f"physics_anki_deck" if mode == "physics" else "leetcode_anki_deck")
        save_final_deck(all_problems, filename)
    else:
        print("No cards generated.")

if __name__ == "__main__":
    asyncio.run(main())
