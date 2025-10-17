#!/usr/bin/env python3
"""
Capture Validator - Verify capture integrity and completeness

This module validates that captured items are properly stored and accessible.
It checks for data integrity, file existence, and metadata consistency.

Key Functions:
- validate_capture(capture_id) - Verify specific capture integrity
- validate_all_captures() - Check all captured items
- repair_capture(capture_id) - Attempt to repair corrupted captures
- get_validation_report() - Generate comprehensive validation report
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of a validation operation."""

    def __init__(
        self,
        capture_id: str,
        valid: bool,
        errors: List[str] = [],
        warnings: List[str] = [],
        metadata: Dict[str, Any] = {},
    ):
        self.capture_id = capture_id
        self.valid = valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capture_id": self.capture_id,
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    def add_error(self, error: str):
        """Add an error to the validation result."""
        self.errors.append(error)
        self.valid = False

    def add_warning(self, warning: str):
        """Add a warning to the validation result."""
        self.warnings.append(warning)


def _calculate_file_hash(file_path: str) -> Optional[str]:
    """Calculate SHA-256 hash of a file."""
    try:
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        logger.error(f"Failed to calculate hash for {file_path}: {e}")
        return None


def _log_validation_operation(
    operation: str, success: bool, details: Dict[str, Any] = {}
) -> None:
    """Log validation operation to comprehensive log."""
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "success": success,
            "details": details or {},
        }

        log_path = "output/logs/validation.log"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        with open(log_path, "a") as log_file:
            log_file.write(json.dumps(log_entry) + "\n")

    except Exception as e:
        logger.error(f"Validation logging failed: {e}")


def validate_capture(capture_id: str) -> ValidationResult:
    """
    Verify capture integrity and completeness.

    Args:
        capture_id: The capture ID to validate

    Returns:
        ValidationResult with validation status and details
    """
    result = ValidationResult(capture_id, True)

    try:
        # Check if metadata file exists
        metadata_path = f"output/captured/metadata/{capture_id}_metadata.json"
        if not os.path.exists(metadata_path):
            result.add_error(f"Metadata file not found: {metadata_path}")
            return result

        # Read and validate metadata
        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
            result.metadata = metadata
        except json.JSONDecodeError as e:
            result.add_error(f"Invalid JSON in metadata file: {e}")
            return result
        except Exception as e:
            result.add_error(f"Failed to read metadata file: {e}")
            return result

        # Validate required metadata fields
        required_fields = ["capture_id", "type", "capture_timestamp", "status"]
        for field in required_fields:
            if field not in metadata:
                result.add_error(f"Missing required metadata field: {field}")

        # Validate capture_id matches
        if metadata.get("capture_id") != capture_id:
            result.add_error(
                f"Metadata capture_id mismatch: expected {capture_id}, got {metadata.get('capture_id')}"
            )

        # Validate based on item type
        item_type = metadata.get("type")

        if item_type == "url":
            _validate_url_capture(capture_id, metadata, result)
        elif item_type == "file":
            _validate_file_capture(capture_id, metadata, result)
        elif item_type == "text":
            _validate_text_capture(capture_id, metadata, result)
        else:
            result.add_error(f"Unknown item type: {item_type}")

        # Check backup existence
        _validate_backup_files(capture_id, metadata, result)

        # Log validation result
        _log_validation_operation(
            "validate_capture",
            result.valid,
            {
                "capture_id": capture_id,
                "errors": result.errors,
                "warnings": result.warnings,
            },
        )

        return result

    except Exception as e:
        result.add_error(f"Validation failed with exception: {str(e)}")
        logger.error(f"Validation failed for {capture_id}: {e}")
        return result


def _validate_url_capture(
    capture_id: str, metadata: Dict[str, Any], result: ValidationResult
) -> None:
    """Validate URL capture specific requirements."""
    # Check primary URL file
    primary_path = f"output/captured/urls/{capture_id}.json"
    if not os.path.exists(primary_path):
        result.add_error(f"Primary URL file not found: {primary_path}")
        return

    # Validate URL file content
    try:
        with open(primary_path, "r") as f:
            url_data = json.load(f)

        # Check that URL data matches metadata
        if url_data.get("url") != metadata.get("url"):
            result.add_error("URL mismatch between primary file and metadata")

        # Validate URL format
        url = metadata.get("url")
        if not url:
            result.add_error("No URL in metadata")
        elif not url.startswith(("http://", "https://")):
            result.add_warning(f"URL may not be valid: {url}")

        # Check parsed URL data
        parsed_url = metadata.get("parsed_url")
        if not parsed_url:
            result.add_warning("No parsed URL data in metadata")
        elif not parsed_url.get("netloc"):
            result.add_error("Invalid parsed URL: missing netloc")

    except json.JSONDecodeError as e:
        result.add_error(f"Invalid JSON in primary URL file: {e}")
    except Exception as e:
        result.add_error(f"Failed to validate URL file: {e}")


def _validate_file_capture(
    capture_id: str, metadata: Dict[str, Any], result: ValidationResult
) -> None:
    """Validate file capture specific requirements."""
    # Check captured file path
    captured_path = metadata.get("captured_path")
    if not captured_path:
        result.add_error("No captured_path in metadata")
        return

    if not os.path.exists(captured_path):
        result.add_error(f"Captured file not found: {captured_path}")
        return

    # Validate file size
    actual_size = os.path.getsize(captured_path)
    expected_size = metadata.get("file_size")
    if expected_size and actual_size != expected_size:
        result.add_error(
            f"File size mismatch: expected {expected_size}, got {actual_size}"
        )

    # Validate file modification time if available
    if metadata.get("file_mtime"):
        try:
            # Just check that the timestamp is valid
            datetime.fromisoformat(metadata["file_mtime"])
        except ValueError:
            result.add_warning("Invalid file modification time format in metadata")

    # Check original file information
    original_path = metadata.get("original_path")
    if not original_path:
        result.add_warning("No original_path in metadata")

    filename = metadata.get("filename")
    if not filename:
        result.add_warning("No filename in metadata")
    elif filename != os.path.basename(captured_path):
        result.add_warning("Filename mismatch between metadata and captured file")


def _validate_text_capture(
    capture_id: str, metadata: Dict[str, Any], result: ValidationResult
) -> None:
    """Validate text capture specific requirements."""
    # Check captured text file
    captured_path = metadata.get("captured_path")
    if not captured_path:
        result.add_error("No captured_path in metadata")
        return

    if not os.path.exists(captured_path):
        result.add_error(f"Captured text file not found: {captured_path}")
        return

    # Validate text length
    try:
        with open(captured_path, "r", encoding="utf-8") as f:
            text_content = f.read()

        actual_length = len(text_content)
        expected_length = metadata.get("text_length")
        if expected_length and actual_length != expected_length:
            result.add_error(
                f"Text length mismatch: expected {expected_length}, got {actual_length}"
            )

    except Exception as e:
        result.add_error(f"Failed to read text file: {e}")

    # Check content type
    content_type = metadata.get("content_type")
    if not content_type:
        result.add_warning("No content_type in metadata")


def _validate_backup_files(
    capture_id: str, metadata: Dict[str, Any], result: ValidationResult
) -> None:
    """Validate backup file existence and integrity."""
    item_type = metadata.get("type")

    if item_type == "url":
        backup_path = f"output/captured/backups/{capture_id}_backup.json"
        primary_path = f"output/captured/urls/{capture_id}.json"
    elif item_type in ["file", "text"]:
        captured_path = metadata.get("captured_path", "")
        if captured_path:
            filename = os.path.basename(captured_path)
            backup_path = f"output/captured/backups/{filename}"
            primary_path = captured_path
        else:
            result.add_warning("Cannot validate backup: no captured_path in metadata")
            return
    else:
        result.add_warning(f"Unknown item type for backup validation: {item_type}")
        return

    # Check if backup exists
    if not os.path.exists(backup_path):
        result.add_warning(f"Backup file not found: {backup_path}")
        return

    # Compare backup with primary file
    if os.path.exists(primary_path):
        try:
            primary_hash = _calculate_file_hash(primary_path)
            backup_hash = _calculate_file_hash(backup_path)

            if primary_hash and backup_hash:
                if primary_hash != backup_hash:
                    result.add_error("Backup file differs from primary file")
            else:
                result.add_warning(
                    "Could not verify backup integrity (hash calculation failed)"
                )

        except Exception as e:
            result.add_warning(f"Failed to compare backup with primary: {e}")


def validate_all_captures(limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Validate all captured items.

    Args:
        limit: Maximum number of items to validate (None for all)

    Returns:
        Dictionary with validation summary and results
    """
    try:
        metadata_dir = "output/captured/metadata"
        if not os.path.exists(metadata_dir):
            return {
                "total_items": 0,
                "valid_items": 0,
                "invalid_items": 0,
                "warnings": 0,
                "results": [],
            }

        # Get all metadata files
        metadata_files = [
            f for f in os.listdir(metadata_dir) if f.endswith("_metadata.json")
        ]

        # Limit if specified
        if limit:
            metadata_files = metadata_files[:limit]

        results = []
        valid_count = 0
        invalid_count = 0
        warning_count = 0

        for filename in metadata_files:
            # Extract capture_id from filename
            capture_id = filename.replace("_metadata.json", "")

            # Validate this capture
            validation_result = validate_capture(capture_id)
            results.append(validation_result.to_dict())

            if validation_result.valid:
                valid_count += 1
            else:
                invalid_count += 1

            warning_count += len(validation_result.warnings)

        summary = {
            "total_items": len(metadata_files),
            "valid_items": valid_count,
            "invalid_items": invalid_count,
            "warnings": warning_count,
            "validation_timestamp": datetime.now().isoformat(),
            "results": results,
        }

        # Log validation summary
        _log_validation_operation(
            "validate_all_captures",
            True,
            {
                "total_items": len(metadata_files),
                "valid_items": valid_count,
                "invalid_items": invalid_count,
                "warnings": warning_count,
            },
        )

        return summary

    except Exception as e:
        logger.error(f"Failed to validate all captures: {e}")
        return {"error": str(e), "validation_timestamp": datetime.now().isoformat()}


def repair_capture(capture_id: str) -> Dict[str, Any]:
    """
    Attempt to repair a corrupted capture.

    Args:
        capture_id: The capture ID to repair

    Returns:
        Dictionary with repair results
    """
    try:
        # First validate to identify issues
        validation_result = validate_capture(capture_id)

        if validation_result.valid:
            return {
                "success": True,
                "message": "Capture is already valid, no repair needed",
                "capture_id": capture_id,
            }

        repairs_attempted = []
        repairs_successful = []

        # Try to repair missing backup
        if any("Backup file not found" in error for error in validation_result.errors):
            if _repair_missing_backup(capture_id, validation_result.metadata):
                repairs_successful.append("Created missing backup file")
            else:
                repairs_attempted.append("Failed to create missing backup file")

        # Try to repair metadata issues
        if any("metadata" in error.lower() for error in validation_result.errors):
            if _repair_metadata_issues(capture_id, validation_result.metadata):
                repairs_successful.append("Fixed metadata issues")
            else:
                repairs_attempted.append("Failed to fix metadata issues")

        # Re-validate after repairs
        final_validation = validate_capture(capture_id)

        result = {
            "success": final_validation.valid,
            "capture_id": capture_id,
            "repairs_attempted": repairs_attempted,
            "repairs_successful": repairs_successful,
            "remaining_errors": final_validation.errors,
            "remaining_warnings": final_validation.warnings,
        }

        # Log repair attempt
        _log_validation_operation("repair_capture", final_validation.valid, result)

        return result

    except Exception as e:
        logger.error(f"Failed to repair capture {capture_id}: {e}")
        return {"success": False, "error": str(e), "capture_id": capture_id}


def _repair_missing_backup(capture_id: str, metadata: Dict[str, Any]) -> bool:
    """Attempt to recreate missing backup file."""
    try:
        item_type = metadata.get("type")

        if item_type == "url":
            primary_path = f"output/captured/urls/{capture_id}.json"
            backup_path = f"output/captured/backups/{capture_id}_backup.json"
        elif item_type in ["file", "text"]:
            captured_path = metadata.get("captured_path", "")
            if not captured_path:
                return False
            filename = os.path.basename(captured_path)
            primary_path = captured_path
            backup_path = f"output/captured/backups/{filename}"
        else:
            return False

        # Check if primary file exists
        if not os.path.exists(primary_path):
            return False

        # Create backup directory if needed
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)

        # Copy primary to backup
        import shutil

        shutil.copy2(primary_path, backup_path)

        return True

    except Exception as e:
        logger.error(f"Failed to repair missing backup for {capture_id}: {e}")
        return False


def _repair_metadata_issues(capture_id: str, metadata: Dict[str, Any]) -> bool:
    """Attempt to fix metadata issues."""
    try:
        # For now, just ensure required fields are present
        required_fields = {"capture_id": capture_id, "status": "captured"}

        updated = False
        for field, default_value in required_fields.items():
            if field not in metadata:
                metadata[field] = default_value
                updated = True

        if updated:
            # Save updated metadata
            metadata_path = f"output/captured/metadata/{capture_id}_metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            return True

        return False

    except Exception as e:
        logger.error(f"Failed to repair metadata for {capture_id}: {e}")
        return False


def get_validation_report() -> Dict[str, Any]:
    """
    Generate comprehensive validation report.

    Returns:
        Dictionary with comprehensive validation statistics
    """
    try:
        # Validate all captures
        validation_summary = validate_all_captures()

        # Get additional statistics
        metadata_dir = "output/captured/metadata"
        if not os.path.exists(metadata_dir):
            return validation_summary

        # Analyze error patterns
        error_patterns: Dict[str, int] = {}
        warning_patterns: Dict[str, int] = {}

        for result in validation_summary.get("results", []):
            for error in result.get("errors", []):
                error_patterns[error] = error_patterns.get(error, 0) + 1
            for warning in result.get("warnings", []):
                warning_patterns[warning] = warning_patterns.get(warning, 0) + 1

        # Check directory integrity
        directory_status = _check_directory_integrity()

        # Generate recommendations
        recommendations = _generate_recommendations(
            validation_summary, error_patterns, warning_patterns
        )

        report = {
            **validation_summary,
            "error_patterns": error_patterns,
            "warning_patterns": warning_patterns,
            "directory_status": directory_status,
            "recommendations": recommendations,
            "report_timestamp": datetime.now().isoformat(),
        }

        return report

    except Exception as e:
        logger.error(f"Failed to generate validation report: {e}")
        return {"error": str(e), "report_timestamp": datetime.now().isoformat()}


def _check_directory_integrity() -> Dict[str, Any]:
    """Check integrity of capture directory structure."""
    try:
        expected_dirs = [
            "output/captured/urls",
            "output/captured/files",
            "output/captured/metadata",
            "output/captured/backups",
            "output/processing_queue",
            "output/logs",
        ]

        directory_status = {}
        for dir_path in expected_dirs:
            directory_status[dir_path] = {
                "exists": os.path.exists(dir_path),
                "is_directory": (
                    os.path.isdir(dir_path) if os.path.exists(dir_path) else False
                ),
                "file_count": (
                    len(os.listdir(dir_path))
                    if os.path.exists(dir_path) and os.path.isdir(dir_path)
                    else 0
                ),
            }

        return directory_status

    except Exception as e:
        logger.error(f"Failed to check directory integrity: {e}")
        return {"error": str(e)}


def _generate_recommendations(
    validation_summary: Dict[str, Any],
    error_patterns: Dict[str, int],
    warning_patterns: Dict[str, int],
) -> List[str]:
    """Generate recommendations based on validation results."""
    recommendations = []

    # Check for common issues
    if validation_summary.get("invalid_items", 0) > 0:
        recommendations.append(
            "Run repair_capture() on invalid items to attempt automatic fixes"
        )

    if "Backup file not found" in error_patterns:
        recommendations.append("Enable backup creation to prevent data loss")

    if any("metadata" in error.lower() for error in error_patterns.keys()):
        recommendations.append("Review metadata generation to ensure consistency")

    if (
        validation_summary.get("warnings", 0)
        > validation_summary.get("total_items", 1) * 0.1
    ):
        recommendations.append("High warning rate detected - review capture process")

    # Add general recommendations
    if validation_summary.get("total_items", 0) > 100:
        recommendations.append("Consider implementing automated validation checks")

    return recommendations


if __name__ == "__main__":
    # Simple test of validation functions
    print("Testing capture validation system...")

    # Test validation report
    report = get_validation_report()
    print(
        f"Validation report: {report.get('total_items', 0)} items, {report.get('valid_items', 0)} valid"
    )

    # Show error patterns if any
    if report.get("error_patterns"):
        print("Error patterns:")
        for error, count in report["error_patterns"].items():
            print(f"  {error}: {count}")

    # Show recommendations
    if report.get("recommendations"):
        print("Recommendations:")
        for rec in report["recommendations"]:
            print(f"  - {rec}")
