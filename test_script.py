import asyncio
import logging
from src.providers.google_antigravity import GoogleAntigravityProvider

logging.basicConfig(level=logging.DEBUG)

async def main():
    provider = GoogleAntigravityProvider(model='glm-5')
    res = await provider.generate_initial_cards(
        question='What is 2+2?',
        json_schema={'type': 'object'}
    )
    print(res)

if __name__ == '__main__':
    asyncio.run(main())