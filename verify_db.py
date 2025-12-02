import asyncio
import os
from dotenv import load_dotenv
import common.db_helpers as db_helpers

async def verify():
    load_dotenv()
    print(f"Testing connection with URI: {os.getenv('MONGO_URI')}")
    await db_helpers.init_db()
    if db_helpers.client:
        print("Verification Successful!")
    else:
        print("Verification Failed!")

if __name__ == "__main__":
    asyncio.run(verify())
