def test_agent_runs():
    from workspace_scripts.agent import run

    assert run() == "ready"
