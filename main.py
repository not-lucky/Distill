import asyncio
from dotenv import load_dotenv

from src.config import QUESTIONS, CONCURRENT_REQUESTS
from src.setup import initialize_providers
from src.generator import CardGenerator
from src.utils import save_final_deck

async def main():
    load_dotenv()
    
    # Initialize Providers
    providers = await initialize_providers()
    if not providers:
        return

    # Combiner (Use the first provider as the combiner)
    combiner = providers[0]

    # Initialize Generator
    generator = CardGenerator(providers, combiner)
    
    # Process Questions
    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
    all_problems = []

    async def sem_task(question):
        async with semaphore:
            result = await generator.process_question(question)
            if result:
                all_problems.append(result)

    print(f"Starting generation for {len(QUESTIONS)} questions...")
    tasks = [sem_task(q) for q in QUESTIONS]
    await asyncio.gather(*tasks)

    # Save Results
    if all_problems:
        save_final_deck(all_problems)
    else:
        print("No cards generated.")

if __name__ == "__main__":
    asyncio.run(main())
