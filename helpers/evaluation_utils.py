import json
import os
from datetime import datetime, timezone

EVALUATION_DIR = "evaluation"


class EvaluationFile:
    def __init__(self, source_file_path: str, config: dict):
        self.config = config
        data_dir = self.config.get("data_directory", "output")

        # Ensure the source file is within the configured data directory
        if not os.path.abspath(source_file_path).startswith(os.path.abspath(data_dir)):
            raise ValueError(
                f"Evaluation files can only be created for files in the '{data_dir}' directory."
            )

        self.source_file_path = source_file_path
        self.eval_file_path = self._generate_eval_path(source_file_path)
        self.data = self._load_or_initialize()

    def _generate_eval_path(self, source_path: str) -> str:
        """Generates the corresponding .eval.json path from a source path inside the data directory."""
        data_dir = self.config.get("data_directory", "output")
        relative_path = os.path.relpath(source_path, data_dir)
        # e.g., articles/markdown/file.md -> evaluation/articles/file.eval.json
        parts = relative_path.split(os.sep)
        content_type = parts[0]  # articles, podcasts, etc.
        base_name = os.path.basename(source_path)
        file_name = os.path.splitext(base_name)[0]
        return os.path.join(EVALUATION_DIR, content_type, f"{file_name}.eval.json")

    def _load_or_initialize(self) -> dict:
        """Loads the evaluation file if it exists, otherwise creates a new structure."""
        if os.path.exists(self.eval_file_path):
            with open(self.eval_file_path, "r") as f:
                return json.load(f)
        else:
            return {
                "source_file": self.source_file_path,
                "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
                "evaluations": [],
                "user_feedback": [],
            }

    def add_evaluation(self, evaluator_id: str, eval_type: str, result: dict):
        """Adds a new evaluation result from an automated evaluator."""
        evaluation = {
            "evaluator_id": evaluator_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": eval_type,
            "result": result,
            "feedback": None,  # Placeholder for direct feedback on this evaluation
        }
        self.data["evaluations"].append(evaluation)

    def add_user_feedback(
        self, target_evaluator_id: str, feedback_type: str, payload: dict
    ):
        """Adds feedback from a user."""
        feedback = {
            "feedback_timestamp": datetime.now(timezone.utc).isoformat(),
            "target_evaluator_id": target_evaluator_id,
            "feedback_type": feedback_type,  # e.g., 'correction', 'rating', 'comment'
            "payload": payload,
        }
        self.data["user_feedback"].append(feedback)

    def save(self):
        """Saves the evaluation data to its JSON file."""
        os.makedirs(os.path.dirname(self.eval_file_path), exist_ok=True)
        with open(self.eval_file_path, "w") as f:
            json.dump(self.data, f, indent=2)


if __name__ == "__main__":
    # Example Usage:
    # This demonstrates how to create and update an evaluation file.
    from helpers.config import load_config

    # 0. Load master config
    config = load_config()
    data_dir = config.get("data_directory", "output")

    # 1. Create a dummy output file to track
    dummy_output_path = os.path.join(data_dir, "articles/markdown/example_article.md")
    os.makedirs(os.path.dirname(dummy_output_path), exist_ok=True)
    with open(dummy_output_path, "w") as f:
        f.write("This is a test article.")

    # 2. Initialize its evaluation file
    eval_file = EvaluationFile(source_file_path=dummy_output_path, config=config)
    print(f"Created/loaded evaluation file at: {eval_file.eval_file_path}")

    # 3. Add a summary evaluation
    eval_file.add_evaluation(
        evaluator_id="summary_v1_test",
        eval_type="summary_accuracy",
        result={
            "summary_text": "This is a test summary.",
            "score": 0.8,
            "explanation": "Looks okay.",
        },
    )

    # 4. Add user feedback on that summary
    eval_file.add_user_feedback(
        target_evaluator_id="summary_v1_test",
        feedback_type="rating",
        payload={"rating": "good", "comment": "The summary was concise."},
    )

    # 5. Save the changes
    eval_file.save()
    print("Evaluation file saved.")

    # 6. Verify content
    with open(eval_file.eval_file_path, "r") as f:
        print("\nFinal content of evaluation file:")
        print(f.read())
