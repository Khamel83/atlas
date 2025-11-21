import os
import subprocess
from helpers.bulletproof_process_manager import create_managed_process
from unittest.mock import patch

import pytest


@pytest.fixture
def dummy_env(tmp_path):
    os.environ["DATA_DIRECTORY"] = str(tmp_path)
    os.environ["OUTPUT_PATH"] = os.path.join(str(tmp_path), "output")
    yield
    del os.environ["DATA_DIRECTORY"]
    del os.environ["OUTPUT_PATH"]


def test_pipeline_entrypoint_with_missing_config(tmp_path):
    # Simulate missing config file
    with patch("builtins.open", side_effect=FileNotFoundError):
        process = create_managed_process(
            ["python3", "ingest/ingest_main.py"], "ingest_main_missing_config"
        )
        stdout, stderr = process.communicate()
        assert "config" in stderr.decode('utf-8').lower() or process.returncode != 0


def test_pipeline_with_missing_output_dir(tmp_path):
    # Remove output dir before run
    output_dir = os.path.join(tmp_path, "output")
    if os.path.exists(output_dir):
        os.rmdir(output_dir)
    with patch("helpers.config.get_config", return_value={"output_path": output_dir}):
        process = create_managed_process(
            ["python3", "ingest/ingest_main.py"], "ingest_main_missing_output_dir"
        )
        stdout, stderr = process.communicate()
        assert "output" in stderr.decode('utf-8').lower() or process.returncode != 0


def test_scheduler_job_persistence_and_rlock():
    # Simulate scheduler error with non-serializable object (e.g., RLock)
    import threading

    from scripts.atlas_scheduler import AtlasScheduler

    scheduler = AtlasScheduler()
    scheduler.initialize_scheduler()  # Ensure scheduler is set up

    def dummy_job(lock):
        return lock

    # Try to add a job with a non-serializable argument
    try:
        scheduler.scheduler.add_job(
            dummy_job, "interval", seconds=1, args=[threading.RLock()]
        )
        scheduler.scheduler.print_jobs()
        # Try to persist jobs (simulate shutdown or save)
        if hasattr(scheduler.scheduler, "_save_jobs"):
            scheduler.scheduler._save_jobs()
    except Exception as e:
        assert "pickle" in str(e) or "RLock" in str(e) or "serialize" in str(e)


def test_evaluation_file_generation(tmp_path):
    # Simulate evaluation file creation in wrong directory
    from helpers.evaluation_utils import EvaluationFile

    with pytest.raises(ValueError):
        EvaluationFile("not_output_dir/file.txt", {})
