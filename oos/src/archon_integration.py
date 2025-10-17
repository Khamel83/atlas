#!/usr/bin/env python3
"""
Archon Integration for Strategic Consultant
Creates and manages projects in Archon for execution and PMO
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from src.strategic_consultant import ConsultantRecommendation, StrategicDirection

logger = logging.getLogger(__name__)

@dataclass
class ArchonProject:
    """Archon project structure"""
    id: str
    name: str
    description: str
    status: str
    phases: List[Dict[str, Any]]
    tasks: List[Dict[str, Any]]
    milestones: List[Dict[str, Any]]
    created_at: str
    updated_at: str

@dataclass
class ArchonTask:
    """Individual Archon task"""
    id: str
    title: str
    description: str
    priority: str
    status: str
    assignee: str
    due_date: str
    dependencies: List[str]
    tags: List[str]

class ArchonIntegration:
    """
    Integration with Archon MCP for project management and execution
    """

    def __init__(self):
        self.archon_connected = False
        self.active_projects: Dict[str, ArchonProject] = {}
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load Archon integration configuration"""
        return {
            "archon": {
                "host": "100.103.45.61",
                "mcp_enabled": True,
                "auto_create": True,
                "update_frequency": "daily",
                "project_prefix": "CONSULTANT_"
            },
            "tasks": {
                "default_assignee": "Strategic Team",
                "priority_mapping": {
                    "immediate": "high",
                    "medium_term": "medium",
                    "long_term": "low"
                }
            },
            "monitoring": {
                "status_update_frequency": "weekly",
                "milestone_check_frequency": "daily",
                "risk_assessment_frequency": "bi_weekly"
            }
        }

    async def create_strategic_project(self, recommendation: ConsultantRecommendation,
                                     analysis_question: str) -> ArchonProject:
        """Create a new strategic project in Archon"""
        logger.info(f"Creating strategic project in Archon for: {analysis_question}")

        project_id = self._generate_project_id(recommendation.direction)
        project_name = self._generate_project_name(analysis_question, recommendation.direction)

        # Create project structure
        project = ArchonProject(
            id=project_id,
            name=project_name,
            description=f"Strategic initiative: {analysis_question}",
            status="planning",
            phases=self._create_project_phases(recommendation),
            tasks=self._create_project_tasks(recommendation),
            milestones=self._create_project_milestones(recommendation),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )

        # Store project
        self.active_projects[project_id] = project

        # Create in Archon (if connected)
        if self.config["archon"]["mcp_enabled"]:
            await self._create_archon_project(project)

        logger.info(f"Strategic project created: {project_id}")
        return project

    def _generate_project_id(self, direction: StrategicDirection) -> str:
        """Generate unique project ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = self.config["archon"]["project_prefix"]
        return f"{prefix}{direction.value.upper()}_{timestamp}"

    def _generate_project_name(self, question: str, direction: StrategicDirection) -> str:
        """Generate descriptive project name"""
        # Extract key words from question
        key_words = []
        if "scale" in question.lower():
            key_words.append("Scaling")
        if "security" in question.lower():
            key_words.append("Security")
        if "rebuild" in question.lower() or direction == StrategicDirection.SCRAP_AND_REBUILD:
            key_words.append("Rebuild")
        if "compliance" in question.lower():
            key_words.append("Compliance")

        if not key_words:
            key_words = ["Strategic", "Initiative"]

        direction_name = direction.value.replace("_", " ").title()
        return f"{' '.join(key_words)} - {direction_name}"

    def _create_project_phases(self, recommendation: ConsultantRecommendation) -> List[Dict[str, Any]]:
        """Create project phases based on recommendation"""
        phases = []

        # Phase 1: Strategic Alignment
        phases.append({
            "id": "phase_1_alignment",
            "name": "Strategic Alignment",
            "description": "Establish strategic direction and stakeholder alignment",
            "duration_days": 14,
            "start_date": datetime.now().isoformat(),
            "end_date": (datetime.now() + timedelta(days=14)).isoformat(),
            "objectives": recommendation.immediate_actions[:3],
            "deliverables": [
                "Stakeholder alignment document",
                "Project charter approved",
                "Resource allocation plan"
            ],
            "status": "active"
        })

        # Phase 2: Foundation Building
        start_date = datetime.now() + timedelta(days=14)
        phases.append({
            "id": "phase_2_foundation",
            "name": "Foundation Building",
            "description": "Build foundation for strategic execution",
            "duration_days": 30,
            "start_date": start_date.isoformat(),
            "end_date": (start_date + timedelta(days=30)).isoformat(),
            "objectives": recommendation.immediate_actions[3:] + recommendation.medium_term_actions[:2],
            "deliverables": [
                "Architecture documentation",
                "Implementation plan",
                "Risk mitigation strategies"
            ],
            "status": "planned"
        })

        # Phase 3: Strategic Execution
        start_date = datetime.now() + timedelta(days=44)
        phases.append({
            "id": "phase_3_execution",
            "name": "Strategic Execution",
            "description": "Execute strategic plan and achieve objectives",
            "duration_days": 90,
            "start_date": start_date.isoformat(),
            "end_date": (start_date + timedelta(days=90)).isoformat(),
            "objectives": recommendation.medium_term_actions[2:] + recommendation.long_term_actions,
            "deliverables": [
                "Strategic objectives achieved",
                "Success metrics met",
                "Sustainable operations established"
            ],
            "status": "planned"
        })

        return phases

    def _create_project_tasks(self, recommendation: ConsultantRecommendation) -> List[Dict[str, Any]]:
        """Create detailed project tasks"""
        tasks = []
        task_counter = 1

        # Immediate action tasks
        for action in recommendation.immediate_actions:
            task_id = f"task_{task_counter:03d}"
            tasks.append({
                "id": task_id,
                "title": action,
                "description": f"Immediate action: {action}",
                "priority": "high",
                "status": "todo",
                "assignee": self.config["tasks"]["default_assignee"],
                "due_date": (datetime.now() + timedelta(days=7)).isoformat(),
                "estimated_hours": 8,
                "phase": "phase_1_alignment",
                "dependencies": [],
                "tags": ["immediate", "strategic", "high_priority"]
            })
            task_counter += 1

        # Medium-term action tasks
        for action in recommendation.medium_term_actions:
            task_id = f"task_{task_counter:03d}"
            tasks.append({
                "id": task_id,
                "title": action,
                "description": f"Medium-term action: {action}",
                "priority": "medium",
                "status": "todo",
                "assignee": self.config["tasks"]["default_assignee"],
                "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
                "estimated_hours": 16,
                "phase": "phase_2_foundation",
                "dependencies": [f"task_{i:03d}" for i in range(1, min(4, len(recommendation.immediate_actions) + 1))],
                "tags": ["medium_term", "strategic"]
            })
            task_counter += 1

        # Long-term action tasks
        for action in recommendation.long_term_actions:
            task_id = f"task_{task_counter:03d}"
            tasks.append({
                "id": task_id,
                "title": action,
                "description": f"Long-term action: {action}",
                "priority": "medium",
                "status": "todo",
                "assignee": self.config["tasks"]["default_assignee"],
                "due_date": (datetime.now() + timedelta(days=90)).isoformat(),
                "estimated_hours": 32,
                "phase": "phase_3_execution",
                "dependencies": [f"task_{i:03d}" for i in range(1, task_counter)],
                "tags": ["long_term", "strategic", "outcome"]
            })
            task_counter += 1

        return tasks

    def _create_project_milestones(self, recommendation: ConsultantRecommendation) -> List[Dict[str, Any]]:
        """Create project milestones"""
        return [
            {
                "id": "milestone_1",
                "name": "Strategic Direction Approved",
                "description": "Stakeholder alignment achieved and strategic direction approved",
                "due_date": (datetime.now() + timedelta(days=14)).isoformat(),
                "criteria": [
                    "Stakeholder sign-off received",
                    "Project charter approved",
                    "Resource allocation confirmed"
                ],
                "status": "pending"
            },
            {
                "id": "milestone_2",
                "name": "Foundation Complete",
                "description": "Strategic foundation built and ready for execution",
                "due_date": (datetime.now() + timedelta(days=44)).isoformat(),
                "criteria": [
                    "Architecture documented",
                    "Implementation plan finalized",
                    "Risk mitigation in place"
                ],
                "status": "pending"
            },
            {
                "id": "milestone_3",
                "name": "Strategic Objectives Achieved",
                "description": "Primary strategic objectives achieved and measured",
                "due_date": (datetime.now() + timedelta(days=134)).isoformat(),
                "criteria": recommendation.success_metrics,
                "status": "pending"
            }
        ]

    async def _create_archon_project(self, project: ArchonProject) -> bool:
        """Create project in Archon via MCP"""
        try:
            # This will connect to the existing Archon MCP integration
            # from src.oos_archon_integration import OOSArchonIntegration  # Self-reference, not needed

            archon_integration = OOSArchonIntegration()

            # Convert project to Archon format
            archon_project_data = {
                "name": project.name,
                "description": project.description,
                "phases": project.phases,
                "tasks": project.tasks,
                "milestones": project.milestones,
                "metadata": {
                    "created_by": "strategic_consultant",
                    "project_type": "strategic_initiative",
                    "consultant_id": project.id
                }
            }

            # Create project in Archon
            result = await archon_integration.create_project(archon_project_data)

            if result.get("success"):
                logger.info(f"Project created in Archon: {project.id}")
                self.archon_connected = True
                return True
            else:
                logger.warning(f"Failed to create project in Archon: {result.get('error')}")
                return False

        except Exception as e:
            logger.error(f"Error creating Archon project: {e}")
            return False

    async def update_project_status(self, project_id: str) -> Dict[str, Any]:
        """Update project status from Archon"""
        if project_id not in self.active_projects:
            return {"error": "Project not found"}

        project = self.active_projects[project_id]

        try:
            # Get updates from Archon
            if self.archon_connected:
                archon_status = await self._get_archon_project_status(project_id)
                if archon_status:
                    project = self._merge_archon_updates(project, archon_status)

            # Update local project
            project.updated_at = datetime.now().isoformat()
            self.active_projects[project_id] = project

            return {
                "project_id": project_id,
                "status": project.status,
                "progress": self._calculate_project_progress(project),
                "next_milestones": self._get_upcoming_milestones(project),
                "at_risk_tasks": self._identify_at_risk_tasks(project),
                "updated_at": project.updated_at
            }

        except Exception as e:
            logger.error(f"Error updating project status: {e}")
            return {"error": str(e)}

    async def _get_archon_project_status(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project status from Archon"""
        try:
            # from src.oos_archon_integration import OOSArchonIntegration  # Self-reference, not needed

            archon_integration = OOSArchonIntegration()
            return await archon_integration.get_project_status(project_id)

        except Exception as e:
            logger.error(f"Error getting Archon status: {e}")
            return None

    def _merge_archon_updates(self, project: ArchonProject, archon_status: Dict[str, Any]) -> ArchonProject:
        """Merge updates from Archon into local project"""
        # Update task statuses
        for archon_task in archon_status.get("tasks", []):
            for local_task in project.tasks:
                if local_task["id"] == archon_task.get("id"):
                    local_task["status"] = archon_task.get("status", local_task["status"])
                    local_task["progress"] = archon_task.get("progress", 0)

        # Update milestone statuses
        for archon_milestone in archon_status.get("milestones", []):
            for local_milestone in project.milestones:
                if local_milestone["id"] == archon_milestone.get("id"):
                    local_milestone["status"] = archon_milestone.get("status", local_milestone["status"])

        # Update overall project status
        project.status = archon_status.get("status", project.status)

        return project

    def _calculate_project_progress(self, project: ArchonProject) -> Dict[str, Any]:
        """Calculate project progress metrics"""
        total_tasks = len(project.tasks)
        completed_tasks = len([t for t in project.tasks if t["status"] == "completed"])
        in_progress_tasks = len([t for t in project.tasks if t["status"] == "in_progress"])

        total_milestones = len(project.milestones)
        completed_milestones = len([m for m in project.milestones if m["status"] == "completed"])

        return {
            "overall_percentage": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            "tasks": {
                "total": total_tasks,
                "completed": completed_tasks,
                "in_progress": in_progress_tasks,
                "pending": total_tasks - completed_tasks - in_progress_tasks
            },
            "milestones": {
                "total": total_milestones,
                "completed": completed_milestones,
                "upcoming": total_milestones - completed_milestones
            }
        }

    def _get_upcoming_milestones(self, project: ArchonProject) -> List[Dict[str, Any]]:
        """Get upcoming milestones for the project"""
        now = datetime.now()
        upcoming = []

        for milestone in project.milestones:
            if milestone["status"] != "completed":
                due_date = datetime.fromisoformat(milestone["due_date"].replace("Z", "+00:00").replace("+00:00", ""))
                days_until = (due_date - now).days

                upcoming.append({
                    "id": milestone["id"],
                    "name": milestone["name"],
                    "due_date": milestone["due_date"],
                    "days_until": days_until,
                    "status": milestone["status"],
                    "at_risk": days_until < 7 and milestone["status"] == "pending"
                })

        return sorted(upcoming, key=lambda x: x["days_until"])

    def _identify_at_risk_tasks(self, project: ArchonProject) -> List[Dict[str, Any]]:
        """Identify tasks that are at risk of delays"""
        now = datetime.now()
        at_risk = []

        for task in project.tasks:
            if task["status"] not in ["completed", "cancelled"]:
                due_date = datetime.fromisoformat(task["due_date"].replace("Z", "+00:00").replace("+00:00", ""))
                days_until = (due_date - now).days

                if days_until < 3 and task["status"] == "todo":
                    at_risk.append({
                        "id": task["id"],
                        "title": task["title"],
                        "due_date": task["due_date"],
                        "days_overdue": abs(days_until) if days_until < 0 else 0,
                        "priority": task["priority"],
                        "reason": "Overdue" if days_until < 0 else "Due soon"
                    })

        return at_risk

    async def generate_status_report(self, project_id: str) -> str:
        """Generate a comprehensive status report"""
        if project_id not in self.active_projects:
            return "❌ Project not found"

        project = self.active_projects[project_id]
        status_data = await self.update_project_status(project_id)

        if "error" in status_data:
            return f"❌ Error generating report: {status_data['error']}"

        progress = status_data["progress"]
        upcoming_milestones = status_data["next_milestones"]
        at_risk_tasks = status_data["at_risk_tasks"]

        report = [
            f"📊 **Strategic Project Status Report**",
            f"**Project:** {project.name}",
            f"**Status:** {project.status.title()}",
            f"**Last Updated:** {status_data['updated_at']}",
            "",
            f"📈 **Progress Overview:**",
            f"• Overall Progress: {progress['overall_percentage']:.1f}%",
            f"• Tasks: {progress['tasks']['completed']}/{progress['tasks']['total']} completed",
            f"• Milestones: {progress['milestones']['completed']}/{progress['milestones']['total']} achieved",
            ""
        ]

        if upcoming_milestones:
            report.extend([
                "🎯 **Upcoming Milestones:**"
            ])
            for milestone in upcoming_milestones[:3]:  # Show next 3
                status_emoji = "🔴" if milestone["at_risk"] else "🟢"
                report.append(f"{status_emoji} {milestone['name']} (Due in {milestone['days_until']} days)")

        if at_risk_tasks:
            report.extend([
                "",
                "⚠️ **At-Risk Tasks:**"
            ])
            for task in at_risk_tasks[:5]:  # Show top 5
                report.append(f"• {task['title']} - {task['reason']}")

        report.extend([
            "",
            "💡 **Next Actions:**",
            "• Review at-risk tasks with team",
            "• Update task progress in Archon",
            "• Prepare for upcoming milestones",
            "",
            "---",
            "*Report generated by Strategic Consultant PMO*"
        ])

        return "\n".join(report)

    def get_all_active_projects(self) -> List[Dict[str, Any]]:
        """Get summary of all active strategic projects"""
        summaries = []

        for project_id, project in self.active_projects.items():
            progress = self._calculate_project_progress(project)
            summaries.append({
                "id": project_id,
                "name": project.name,
                "status": project.status,
                "progress_percentage": progress["overall_percentage"],
                "total_tasks": progress["tasks"]["total"],
                "completed_tasks": progress["tasks"]["completed"],
                "created_at": project.created_at,
                "updated_at": project.updated_at
            })

        return sorted(summaries, key=lambda x: x["updated_at"], reverse=True)