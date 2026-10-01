import uvicorn
import os
import asyncio

async def create_server():
  config = uvicorn.Config("app:app",
                          host=os.getenv("UVICORN_HOST", "127.0.0.1"),
                          port=int(os.getenv("UVICORN_PORT", 8000)),
                          reload=os.getenv("UVICORN_RELOAD", "false").lower() == "true"
                          )

  server = uvicorn.Server(config)
  return server.serve()

if __name__ == "__main__":
  asyncio.run(create_server())