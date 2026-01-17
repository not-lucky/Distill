from g4f.client import AsyncClient
import asyncio

async def main():
    client = AsyncClient()
    response = await client.chat.completions.create(
        model="claude-opus-4-5-20251101-thinking-32k",
        provider="LMArena",
        messages=[{"role": "user", "content": "explain kadanes algorithm with example and its variations."}],
    )
    print(response.choices[0].message.content)


    # stream = client.chat.completions.stream(
    #     model="claude-opus-4-5-20251101-thinking-32k",
    #     provider="LMArena",
    #     messages=[{"role": "user", "content": "explain kadanes algorithm with example and its variations."}],
    # )
    # async for chunk in stream:
    #     if chunk.choices and chunk.choices[0].delta.content:
    #         print(chunk.choices[0].delta.content, end="")

asyncio.run(main())
