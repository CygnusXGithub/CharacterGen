# test_init.py
import asyncio
from main import ApplicationManager

async def test_init():
    app = ApplicationManager()
    await app.initialize()
    
if __name__ == "__main__":
    asyncio.run(test_init())