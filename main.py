import asyncio
import uuid
from dotenv import load_dotenv
import sys
from typing import List, Tuple

from src.config import CONCURRENT_REQUESTS, DATABASE_PATH
from src.config.subjects import SubjectRegistry
from src.setup import initialize_providers
from src.generator import CardGenerator
from src.utils import save_final_deck
from src.logging_config import setup_logging
from src.questions import get_indexed_questions
from src.database import init_database, create_run, update_run, get_session


async def main():
    setup_logging()
    load_dotenv()

    # Parse arguments: subject [card_type] [--label=<name>]
    command_line_arguments = sys.argv[1:]

    subject_name = "leetcode"
    card_type_name = "standard"
    run_label = None

    for argument in command_line_arguments:
        if argument in ["cs", "physics", "leetcode"]:
            subject_name = argument
        elif argument == "mcq":
            card_type_name = "mcq"
        elif argument.startswith("--label="):
            run_label = argument.split("=", 1)[1]

    print(
        f"Running: Subject={subject_name.upper()}, Card Type={card_type_name.upper()}"
    )
    if run_label:
        print(f"Run Label: {run_label}")

    # Retrieve configuration from Registry
    is_multiple_choice = card_type_name == "mcq"
    subject_config = SubjectRegistry.get_config(subject_name, is_multiple_choice)

    prompt_template = subject_config.prompt_template
    target_model_class = subject_config.target_model

    # Configure mode identifier
    generation_mode = (
        f"{subject_name}_{card_type_name}" if is_multiple_choice else subject_name
    )

    # Initialize database
    print(f"Initializing database at {DATABASE_PATH}")
    init_database(DATABASE_PATH)

    # Create run entry
    run_id = str(uuid.uuid4())
    session = get_session()
    run = create_run(
        session=session,
        id=run_id,
        user_label=run_label,
        mode=generation_mode,
        subject=subject_name,
        card_type=card_type_name,
        status="running",
    )
    session.close()

    print(f"Run ID: {run_id}")
    print("=" * 60)

    # Initialize Providers
    llm_providers = await initialize_providers()
    if not llm_providers:
        # Update run status to failed
        session = get_session()
        update_run(session, run_id, status="failed")
        session.close()
        return

    # Combiner (Use the first provider as the combiner)
    card_combiner_provider = llm_providers[0]
    llm_providers.remove(card_combiner_provider)

    # Initialize Generator with run_id
    card_generator = CardGenerator(
        llm_providers, card_combiner_provider, mode=generation_mode, run_id=run_id
    )

    # Build question list with metadata
    # Format: List of (category_index, category_name, problem_index, problem_name)
    # All subjects now use categorized format
    questions_with_metadata: List[Tuple] = get_indexed_questions(
        subject_config.target_questions
    )

    # Process Questions
    concurrency_semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
    all_generated_problems = []

    async def process_question_with_semaphore(
        category_index, category_name, problem_index, question_text
    ):
        async with concurrency_semaphore:
            generation_result = await card_generator.process_question(
                question_text,
                prompt_template,
                target_model_class,
                category_index=category_index,
                category_name=category_name,
                problem_index=problem_index,
            )
            if generation_result:
                all_generated_problems.append(generation_result)

    print(f"Starting generation for {len(questions_with_metadata)} questions...")
    generation_tasks = [
        process_question_with_semaphore(
            category_index, category_name, problem_index, question_text
        )
        for category_index, category_name, problem_index, question_text in questions_with_metadata
    ]
    await asyncio.gather(*generation_tasks)

    # Update run status
    session = get_session()
    update_run(
        session=session,
        run_id=run_id,
        status="completed",
        total_problems=len(questions_with_metadata),
        successful_problems=len(all_generated_problems),
        failed_problems=len(questions_with_metadata) - len(all_generated_problems),
    )
    session.close()

    # Save Results (for backward compatibility with anki import)
    if all_generated_problems:
        output_filename = f"{generation_mode}_anki_deck"
        save_final_deck(all_generated_problems, output_filename)
        print("=" * 60)
        print(f"✓ Run completed successfully!")
        print(f"✓ Run ID: {run_id}")
        print(f"✓ Database: {DATABASE_PATH}")
        print(
            f"✓ Generated {len(all_generated_problems)}/{len(questions_with_metadata)} problems"
        )
        print(f"✓ Final deck: {output_filename}_<timestamp>.json")
    else:
        print("No cards generated.")


if __name__ == "__main__":
    asyncio.run(main())
