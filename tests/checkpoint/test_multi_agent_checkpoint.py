from runtime.checkpoint.checkpoint import (
    Checkpoint,
    AgentCheckpoint
)


from runtime.context.context_state import ContextState
from runtime.context.shared_context import SharedContext
from runtime.loop.loop_state import LoopState



def test_multi_agent_checkpoint():


    research_checkpoint = AgentCheckpoint(

        agent_id="research",

        state=ContextState(),

        loop=LoopState()

    )


    risk_checkpoint = AgentCheckpoint(

        agent_id="risk",

        state=ContextState(),

        loop=LoopState()

    )


    checkpoint = Checkpoint(
        runtime_id="runtime001",
        shared_context=SharedContext(),
        agents={
            "research":
                research_checkpoint,
            "risk":
                risk_checkpoint
        }
    )


    assert (
        checkpoint.agents["research"]
        .agent_id
        ==
        "research"
    )


    assert (
        checkpoint.agents["risk"]
        .agent_id
        ==
        "risk"
    )