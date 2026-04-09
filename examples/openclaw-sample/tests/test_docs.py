def test_workspace_has_readme():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    assert (root / "README.md").exists()
