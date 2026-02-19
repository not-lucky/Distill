import asyncio
import logging
from src.providers.google_antigravity import GoogleAntigravityProvider

logging.basicConfig(level=logging.DEBUG)

async def main():
    provider = GoogleAntigravityProvider(model='kimi-k2.5')
    try:
        res = await provider.generate_initial_cards(
            question='What is 2+2?',
            json_schema={'type': 'object'}
        )
        print(res)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())