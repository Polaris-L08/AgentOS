from agents.research.domain.goal import ResearchGoal
from agents.research.domain.report import ResearchReport
from agents.research.domain.task import ResearchTask


def test_research_task():

    task = ResearchTask(
        task_id="research-001",
        subject="NVIDIA",
        objective="Analyze the company's investment outlook.",
    )

    assert task.task_id == "research-001"
    assert task.subject == "NVIDIA"
    assert (
        task.objective
        == "Analyze the company's investment outlook."
    )

    assert (
        task.description
        == (
            "Research subject: NVIDIA. "
            "Objective: Analyze the company's investment outlook."
        )
    )


def test_research_goal():

    goal = ResearchGoal(
        objective="Evaluate NVIDIA's investment outlook.",
        required_topics=(
            "business",
            "financials",
            "valuation",
            "risks",
        ),
        success_criteria=(
            "All required topics are addressed.",
            "Major investment risks are identified.",
        ),
    )

    assert (
        goal.objective
        == "Evaluate NVIDIA's investment outlook."
    )

    assert goal.required_topics == (
        "business",
        "financials",
        "valuation",
        "risks",
    )

    assert len(goal.success_criteria) == 2


def test_research_report():

    report = ResearchReport(
        task_id="research-001",
        subject="NVIDIA",
        summary="NVIDIA has strong growth potential.",
        findings=(
            "Strong AI accelerator demand.",
            "High revenue growth.",
        ),
        risks=(
            "Valuation risk.",
            "Competition risk.",
        ),
        evidence=(
            {
                "source": "test",
                "description": "Test evidence",
            },
        ),
    )

    assert report.task_id == "research-001"
    assert report.subject == "NVIDIA"

    assert len(report.findings) == 2
    assert len(report.risks) == 2
    assert len(report.evidence) == 1