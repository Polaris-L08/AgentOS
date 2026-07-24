from runtime.checkpoint import CheckpointStore, Checkpoint
from runtime.checkpoint.checkpoint import AgentCheckpoint
from runtime.context import RuntimeContext, AgentExecutionContext


class CheckpointManager:
    """
    Manage checkpoint lifecycle.

    Responsibilities:
        Runtime state aggregation
        Checkpoint creation
        Persistence

    Does NOT:
        execute agents
        manage storage details
    """

    def __init__(self, store: CheckpointStore) -> None:
        self._store = store

    async def save(self,
                   task_id: str,
                   runtime_context: RuntimeContext,
                   agents: list[AgentExecutionContext]
    ) -> str:
        checkpoint = Checkpoint(
            runtime_id=runtime_context.runtime_id,
            task_id=task_id,
            shared_context=runtime_context.shared_context,
            agents={
                agent.agent_identity.agent_id:
                    AgentCheckpoint(
                        agent_id=agent.agent_identity.agent_id,
                        state=agent.state,
                        loop=agent.loop
                    )
                for agent in agents
            }
        )

        await self._store.save(checkpoint.checkpoint_id, checkpoint)

        return checkpoint.checkpoint_id
    

    async def load(self, checkpoint_id: str) -> Checkpoint | None:

        return await self._store.load(checkpoint_id)
