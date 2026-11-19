import json

import pytest

from kg_pipeline.cli import connection_settings, main


def test_validate_and_plan_without_database(dataset_path, monkeypatch, capsys):
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    assert main(["validate", str(dataset_path)]) == 0
    assert json.loads(capsys.readouterr().out)["valid"] is True
    assert main(["plan", str(dataset_path)]) == 0
    assert len(json.loads(capsys.readouterr().out)["nodes"]) > 0


def test_schema_and_registry_exports(capsys):
    assert main(["schema"]) == 0
    assert json.loads(capsys.readouterr().out)["properties"]["schema_version"]["enum"] == ["1.0.0", "1.1.0"]
    assert main(["registry"]) == 0
    assert json.loads(capsys.readouterr().out)["crm_version"] == "7.1.3"


def test_output_is_not_overwritten(dataset_path, tmp_path, capsys):
    output = tmp_path / "plan.json"
    assert main(["plan", str(dataset_path), "--output", str(output)]) == 0
    original = output.read_bytes()
    assert main(["plan", str(dataset_path), "--output", str(output)]) == 1
    assert output.read_bytes() == original
    assert "Chyba" in capsys.readouterr().err


def test_connection_errors_do_not_expose_password(monkeypatch):
    monkeypatch.setenv("NEO4J_PASSWORD", "do-not-print-this")
    monkeypatch.setenv("NEO4J_URI", "bolt://user:embedded-secret@localhost:7687")
    with pytest.raises(ValueError) as exc:
        connection_settings()
    assert "embedded-secret" not in str(exc.value)
    assert "do-not-print-this" not in str(exc.value)


def test_run_command_uses_automatic_pipeline(dataset_path, raw_dataset, tmp_path, monkeypatch, capsys):
    from kg_pipeline.extraction.pipeline import run_pipeline
    from test_pipeline import FakeBackend

    config = tmp_path / "models.toml"
    config.write_text("\n".join(f'[models.{role}]\nmodel = "{role}-model:local"\n'
                                for role in ("entities", "events", "review", "identity")))
    monkeypatch.setattr("kg_pipeline.cli.run_pipeline", lambda manifest, config_path, output, progress:
                        run_pipeline(manifest, config_path, output, FakeBackend(raw_dataset), progress))
    output = tmp_path / "automatic-run"
    assert main(["run", str(dataset_path.parent / "input.json"), "--config", str(config), "--output", str(output)]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["accepted_events"] == 3
    assert "extrakce entit" in captured.err
    assert (output / "run.json").is_file()


def test_run_skips_graph_if_no_events_accepted(tmp_path, monkeypatch, capsys):
    summary = {"output": str(tmp_path), "accepted_events": 0}
    monkeypatch.setattr("kg_pipeline.cli.run_pipeline", lambda *args, **kwargs: summary)
    assert main(["run", "input.json", "--import"]) == 0
    assert json.loads(capsys.readouterr().out)["graph_import"]["status"] == "skipped_no_accepted_events"
    assert json.loads((tmp_path / "import.json").read_text())["status"] == "skipped_no_accepted_events"


def test_graph_configuration_failure_keeps_pipeline_output_audited(tmp_path, monkeypatch, capsys):
    summary = {"output": str(tmp_path), "accepted_events": 1}
    monkeypatch.setattr("kg_pipeline.cli.run_pipeline", lambda *args, **kwargs: summary)
    monkeypatch.setattr("kg_pipeline.cli.connection_settings", lambda: (_ for _ in ()).throw(ValueError("Chybí konfigurace.")))
    assert main(["run", "input.json", "--import"]) == 1
    assert "Chybí konfigurace" in capsys.readouterr().err
    assert json.loads((tmp_path / "import.json").read_text()) == {"status": "failed", "error_type": "ValueError"}
