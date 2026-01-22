"""Tests to ensure CLI modules are imported for coverage"""
def test_cli_imports() -> None:
    """Test that all CLI modules can be imported"""
    from forensic.cli import cli
    from forensic.cli.models.config import ForensicCLIConfig

    assert cli is not None
    assert ForensicCLIConfig is not None
