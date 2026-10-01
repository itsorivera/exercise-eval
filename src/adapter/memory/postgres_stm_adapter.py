from src.core.ports.stm_port import STMProviderPort
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import os

class PostgresSTMAdapter(STMProviderPort):
  def __init__(self):
    self._pool = None
    self._connection = None

  async def get_state_manager(self):
    connection_kwargs = {
        "autocommit": True,
        "prepare_threshold": 0,
    }
    
    postgres_uri = self._build_postgres_uri()
    
    self._pool = AsyncConnectionPool(postgres_uri, kwargs=connection_kwargs, open=False)
    await self._pool.open()
    
    self._checkpointer = AsyncPostgresSaver(self._pool)
    await self._checkpointer.setup()
    
    return self._checkpointer

  def _build_postgres_uri(self) -> str:
        """Construye la URI de conexión a PostgreSQL"""
        if os.getenv("POSTGRES_CONNECTION_STRING"):
            return os.getenv("POSTGRES_CONNECTION_STRING")

        return (
            f"postgresql://{os.getenv('POSTGRES_USER')}:"
            f"{os.getenv('POSTGRES_PASSWORD')}@"
            f"{os.getenv('POSTGRES_HOST')}:"
            f"{os.getenv('POSTGRES_PORT')}/"
            f"{os.getenv('POSTGRES_DATABASE')}?"
            f"options=-csearch_path%3D{os.getenv('CONVERSATION_SCHEMA')}"
        )