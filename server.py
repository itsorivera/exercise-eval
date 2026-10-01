import uvicorn
from dotenv import load_dotenv
import os
import asyncio
import sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    

load_dotenv()

async def main():
  server_config = uvicorn.Config(
    "src.app:app",
    host=os.getenv("UVICORN_HOST", "127.0.0.1"),
    port=int(os.getenv("UVICORN_PORT", 8000)),
    reload=True
  )
  server = uvicorn.Server(server_config)
  await server.serve()

if __name__ == "__main__":
  asyncio.run(main())