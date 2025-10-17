#!/usr/bin/env python3
"""
Atlas Deployment Manager

Handles deployment operations including version management, rollbacks, and blue-green deployments.
"""

import os
import sys
import json
import shutil
import hashlib
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.configuration_manager import ConfigurationManager, Environment
from helpers.secret_manager import SecretManager


@dataclass
class DeploymentVersion:
    """Deployment version information."""
    version: str
    commit_hash: str
    timestamp: datetime
    environment: str
    status: str
    config_hash: str
    deployment_path: str
    rollback_available: bool


@dataclass
class DeploymentResult:
    """Result of a deployment operation."""
    success: bool
    version: str
    message: str
    deployment_time: datetime
    rollback_version: Optional[str] = None


class DeploymentManager:
    """Manages Atlas deployments."""

    def __init__(self, base_dir: str = "/opt/atlas", config_dir: str = "config"):
        """Initialize deployment manager."""
        self.base_dir = Path(base_dir)
        self.config_dir = Path(config_dir)
        self.deployments_dir = self.base_dir / "deployments"
        self.current_dir = self.base_dir / "current"
        self.shared_dir = self.base_dir / "shared"
        self.versions_file = self.base_dir / "versions.json"

        # Create directories
        for dir_path in [self.base_dir, self.deployments_dir, self.shared_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Load deployment history
        self.versions = self._load_versions()

    def _load_versions(self) -> List[DeploymentVersion]:
        """Load deployment versions from file."""
        if self.versions_file.exists():
            try:
                with open(self.versions_file, 'r') as f:
                    data = json.load(f)
                    return [DeploymentVersion(**v) for v in data]
            except Exception:
                return []
        return []

    def _save_versions(self):
        """Save deployment versions to file."""
        data = [asdict(v) for v in self.versions]
        with open(self.versions_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def _get_config_hash(self, config_dir: Path) -> str:
        """Calculate hash of configuration files."""
        hasher = hashlib.sha256()
        for config_file in config_dir.glob("*.env"):
            if config_file.is_file():
                with open(config_file, 'rb') as f:
                    hasher.update(f.read())
        return hasher.hexdigest()[:16]

    def _get_commit_hash(self) -> str:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "unknown"

    def prepare_deployment(
        self,
        source_path: str,
        environment: str,
        version: Optional[str] = None
    ) -> DeploymentVersion:
        """Prepare a new deployment."""
        source_path = Path(source_path)
        if not source_path.exists():
            raise ValueError(f"Source path does not exist: {source_path}")

        if not version:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create deployment directory
        deployment_path = self.deployments_dir / version
        deployment_path.mkdir(exist_ok=True)

        # Copy source files
        for item in source_path.iterdir():
            if item.name not in [".git", "__pycache__", "*.pyc", ".pytest_cache"]:
                dest = deployment_path / item.name
                if item.is_dir():
                    shutil.copytree(item, dest, ignore=shutil.ignore_patterns('.git', '__pycache__', '*.pyc'))
                else:
                    shutil.copy2(item, dest)

        # Install dependencies
        requirements_file = deployment_path / "requirements.txt"
        if requirements_file.exists():
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
            ], check=True, cwd=deployment_path)

        # Create version record
        deployment_version = DeploymentVersion(
            version=version,
            commit_hash=self._get_commit_hash(),
            timestamp=datetime.now(),
            environment=environment,
            status="prepared",
            config_hash=self._get_config_hash(self.config_dir),
            deployment_path=str(deployment_path),
            rollback_available=False
        )

        self.versions.append(deployment_version)
        self._save_versions()

        return deployment_version

    def deploy(
        self,
        version: str,
        environment: str,
        strategy: str = "rolling",
        backup: bool = True
    ) -> DeploymentResult:
        """Deploy a specific version."""
        # Find version
        target_version = None
        for v in self.versions:
            if v.version == version:
                target_version = v
                break

        if not target_version:
            raise ValueError(f"Version {version} not found")

        # Record rollback version
        rollback_version = None
        if self.current_dir.exists() and self.current_dir.is_symlink():
            current_target = self.current_dir.resolve()
            for v in self.versions:
                if v.deployment_path == str(current_target):
                    rollback_version = v.version
                    break

        # Backup current deployment if requested
        if backup and rollback_version:
            self._backup_current_deployment(rollback_version)

        deployment_start = datetime.now()

        try:
            if strategy == "rolling":
                result = self._rolling_deploy(target_version, environment)
            elif strategy == "blue_green":
                result = self._blue_green_deploy(target_version, environment)
            else:
                raise ValueError(f"Unknown deployment strategy: {strategy}")

            # Update version status
            target_version.status = "deployed"
            self._save_versions()

            return DeploymentResult(
                success=result.success,
                version=version,
                message=result.message,
                deployment_time=deployment_start,
                rollback_version=rollback_version
            )

        except Exception as e:
            # Update version status
            target_version.status = "failed"
            self._save_versions()

            # Attempt rollback if we have a previous version
            if rollback_version and strategy == "rolling":
                try:
                    self._rolling_deploy(
                        next(v for v in self.versions if v.version == rollback_version),
                        environment
                    )
                    message = f"Deployment failed: {e}. Rolled back to {rollback_version}"
                except Exception as rollback_error:
                    message = f"Deployment failed: {e}. Rollback failed: {rollback_error}"
            else:
                message = f"Deployment failed: {e}"

            return DeploymentResult(
                success=False,
                version=version,
                message=message,
                deployment_time=deployment_start,
                rollback_version=rollback_version
            )

    def _rolling_deploy(self, version: DeploymentVersion, environment: str) -> DeploymentResult:
        """Perform rolling deployment."""
        deployment_path = Path(version.deployment_path)

        # Stop services
        self._stop_services()

        try:
            # Update current symlink
            if self.current_dir.exists():
                if self.current_dir.is_symlink():
                    self.current_dir.unlink()
                else:
                    # Move existing deployment to backup
                    backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    self.current_dir.rename(self.deployments_dir / backup_name)

            self.current_dir.symlink_to(deployment_path)

            # Update configuration
            self._update_configuration(deployment_path, environment)

            # Start services
            self._start_services()

            # Health check
            if self._health_check():
                return DeploymentResult(
                    success=True,
                    version=version.version,
                    message="Rolling deployment completed successfully",
                    deployment_time=datetime.now()
                )
            else:
                raise RuntimeError("Health check failed")

        except Exception as e:
            # Attempt to restore previous state
            self._emergency_restore()
            raise e

    def _blue_green_deploy(self, version: DeploymentVersion, environment: str) -> DeploymentResult:
        """Perform blue-green deployment."""
        deployment_path = Path(version.deployment_path)

        # Determine which is currently active (blue or green)
        green_dir = self.base_dir / "green"
        blue_dir = self.base_dir / "blue"

        if self.current_dir.exists() and self.current_dir.is_symlink():
            current_target = self.current_dir.resolve()
            if str(current_target) == str(green_dir):
                active_color = "green"
                inactive_color = "blue"
                inactive_dir = blue_dir
            else:
                active_color = "blue"
                inactive_color = "green"
                inactive_dir = green_dir
        else:
            # First deployment, use green
            active_color = "blue"
            inactive_color = "green"
            inactive_dir = green_dir

        # Prepare inactive environment
        if inactive_dir.exists():
            shutil.rmtree(inactive_dir)
        shutil.copytree(deployment_path, inactive_dir)

        # Update configuration in inactive environment
        self._update_configuration(inactive_dir, environment)

        # Start services in inactive environment
        self._start_services(inactive_dir)

        # Health check inactive environment
        if self._health_check(inactive_dir):
            # Switch symlink
            if self.current_dir.exists() and self.current_dir.is_symlink():
                self.current_dir.unlink()
            self.current_dir.symlink_to(inactive_dir)

            # Stop old services
            if active_color == "green":
                self._stop_services(green_dir)
            else:
                self._stop_services(blue_dir)

            return DeploymentResult(
                success=True,
                version=version.version,
                message=f"Blue-green deployment completed. Switched to {inactive_color}",
                deployment_time=datetime.now()
            )
        else:
            # Clean up failed deployment
            if inactive_dir.exists():
                self._stop_services(inactive_dir)
                shutil.rmtree(inactive_dir)
            raise RuntimeError("Health check failed for new deployment")

    def _stop_services(self, service_dir: Optional[Path] = None):
        """Stop Atlas services."""
        services = ["atlas-api", "atlas-monitoring", "atlas-scheduler"]
        for service in services:
            subprocess.run(["sudo", "systemctl", "stop", service], capture_output=True)

    def _start_services(self, service_dir: Optional[Path] = None):
        """Start Atlas services."""
        services = ["atlas-scheduler", "atlas-monitoring", "atlas-api"]
        for service in services:
            subprocess.run(["sudo", "systemctl", "start", service], capture_output=True)

    def _update_configuration(self, deployment_path: Path, environment: str):
        """Update configuration for deployment."""
        # Create environment-specific config
        env_config = deployment_path / ".env"
        config_manager = ConfigurationManager(
            environment=Environment(environment),
            config_dir=str(self.config_dir)
        )

        # Export configuration
        config_content = config_manager.export_config(format="env", include_sensitive=False)
        with open(env_config, 'w') as f:
            f.write(config_content)

        # Set correct permissions
        env_config.chmod(0o600)

    def _health_check(self, service_dir: Optional[Path] = None) -> bool:
        """Perform health check on deployed services."""
        import time
        max_attempts = 10
        wait_time = 5

        for attempt in range(max_attempts):
            try:
                # Check API health
                import requests
                response = requests.get("http://localhost:7444/health", timeout=5)
                if response.status_code == 200:
                    return True
            except:
                pass

            if attempt < max_attempts - 1:
                time.sleep(wait_time)

        return False

    def _backup_current_deployment(self, version: str):
        """Backup current deployment before update."""
        backup_dir = self.base_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        backup_name = f"backup_{version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = backup_dir / backup_name

        if self.current_dir.exists():
            shutil.copytree(self.current_dir, backup_path)

    def _emergency_restore(self):
        """Emergency restore to last known good state."""
        # Find most recent successful deployment
        successful_versions = [v for v in self.versions if v.status == "deployed"]
        if successful_versions:
            latest_version = max(successful_versions, key=lambda v: v.timestamp)
            self._rolling_deploy(latest_version, latest_version.environment)

    def rollback(self, target_version: str) -> DeploymentResult:
        """Rollback to a specific version."""
        # Find target version
        version_info = None
        for v in self.versions:
            if v.version == target_version:
                version_info = v
                break

        if not version_info:
            raise ValueError(f"Version {target_version} not found")

        # Record current version for potential rollback
        current_version = None
        if self.current_dir.exists() and self.current_dir.is_symlink():
            current_target = self.current_dir.resolve()
            for v in self.versions:
                if v.deployment_path == str(current_target):
                    current_version = v.version
                    break

        # Perform rollback
        try:
            result = self._rolling_deploy(version_info, version_info.environment)

            # Update version status
            version_info.status = "deployed"
            self._save_versions()

            return DeploymentResult(
                success=result.success,
                version=target_version,
                message=f"Rollback to {target_version} completed",
                deployment_time=datetime.now(),
                rollback_version=current_version
            )

        except Exception as e:
            return DeploymentResult(
                success=False,
                version=target_version,
                message=f"Rollback failed: {e}",
                deployment_time=datetime.now(),
                rollback_version=current_version
            )

    def list_versions(self) -> List[Dict[str, Any]]:
        """List all deployment versions."""
        return [asdict(v) for v in sorted(self.versions, key=lambda v: v.timestamp, reverse=True)]

    def cleanup_old_versions(self, keep_count: int = 5) -> List[str]:
        """Clean up old deployment versions."""
        if len(self.versions) <= keep_count:
            return []

        # Keep versions with status "deployed" and the most recent ones
        deployed_versions = [v for v in self.versions if v.status == "deployed"]
        sorted_versions = sorted(self.versions, key=lambda v: v.timestamp, reverse=True)

        versions_to_keep = set()
        versions_to_keep.update(v.version for v in deployed_versions)
        versions_to_keep.update(v.version for v in sorted_versions[:keep_count])

        removed_versions = []
        remaining_versions = []

        for version in self.versions:
            if version.version not in versions_to_keep:
                # Remove deployment directory
                deployment_path = Path(version.deployment_path)
                if deployment_path.exists():
                    shutil.rmtree(deployment_path)
                removed_versions.append(version.version)
            else:
                remaining_versions.append(version)

        self.versions = remaining_versions
        self._save_versions()

        return removed_versions

    def get_deployment_status(self) -> Dict[str, Any]:
        """Get current deployment status."""
        current_version = None
        if self.current_dir.exists() and self.current_dir.is_symlink():
            current_target = self.current_dir.resolve()
            for v in self.versions:
                if v.deployment_path == str(current_target):
                    current_version = v
                    break

        return {
            "current_version": asdict(current_version) if current_version else None,
            "total_versions": len(self.versions),
            "deployed_versions": len([v for v in self.versions if v.status == "deployed"]),
            "base_directory": str(self.base_dir),
            "current_symlink": str(self.current_dir) if self.current_dir.exists() else None,
            "timestamp": datetime.now().isoformat()
        }


def create_parser():
    """Create command line parser."""
    parser = argparse.ArgumentParser(
        description="Atlas Deployment Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--base-dir", default="/opt/atlas", help="Base deployment directory")
    parser.add_argument("--config-dir", default="config", help="Configuration directory")

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Prepare deployment
    prepare_parser = subparsers.add_parser("prepare", help="Prepare deployment")
    prepare_parser.add_argument("source_path", help="Source code path")
    prepare_parser.add_argument("--environment", required=True, help="Target environment")
    prepare_parser.add_argument("--version", help="Version identifier")

    # Deploy
    deploy_parser = subparsers.add_parser("deploy", help="Deploy version")
    deploy_parser.add_argument("version", help="Version to deploy")
    deploy_parser.add_argument("--environment", required=True, help="Target environment")
    deploy_parser.add_argument("--strategy", choices=["rolling", "blue-green"], default="rolling", help="Deployment strategy")
    deploy_parser.add_argument("--no-backup", action="store_true", help="Skip backup")

    # Rollback
    rollback_parser = subparsers.add_parser("rollback", help="Rollback to version")
    rollback_parser.add_argument("version", help="Target version for rollback")

    # List versions
    subparsers.add_parser("list", help="List deployment versions")

    # Status
    subparsers.add_parser("status", help="Show deployment status")

    # Cleanup
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old versions")
    cleanup_parser.add_argument("--keep", type=int, default=5, help="Number of versions to keep")

    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        # Initialize deployment manager
        deploy_manager = DeploymentManager(args.base_dir, args.config_dir)

        # Execute command
        if args.command == "prepare":
            version = deploy_manager.prepare_deployment(args.source_path, args.environment, args.version)
            print(f"✅ Deployment prepared: {version.version}")

        elif args.command == "deploy":
            result = deploy_manager.deploy(args.version, args.environment, args.strategy, not args.no_backup)
            if result.success:
                print(f"✅ Deployment successful: {result.version}")
                if result.rollback_version:
                    print(f"   Rollback available: {result.rollback_version}")
            else:
                print(f"❌ Deployment failed: {result.message}")

        elif args.command == "rollback":
            result = deploy_manager.rollback(args.version)
            if result.success:
                print(f"✅ Rollback successful: {result.version}")
            else:
                print(f"❌ Rollback failed: {result.message}")

        elif args.command == "list":
            versions = deploy_manager.list_versions()
            for version in versions:
                status_icon = "✅" if version["status"] == "deployed" else "📦" if version["status"] == "prepared" else "❌"
                print(f"{status_icon} {version['version']} - {version['environment']} ({version['status']})")

        elif args.command == "status":
            status = deploy_manager.get_deployment_status()
            print(json.dumps(status, indent=2))

        elif args.command == "cleanup":
            removed = deploy_manager.cleanup_old_versions(args.keep)
            print(f"✅ Cleaned up {len(removed)} old versions")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()