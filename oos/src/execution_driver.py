#!/usr/bin/env python3
"""
Execution Driver - Maintains momentum and drives strategic plan execution
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from src.archon_integration import ArchonIntegration, ArchonProject

logger = logging.getLogger(__name__)

@dataclass
class ExecutionStatus:
    """Status of strategic execution"""
    momentum_score: float  # 0-100
    velocity_trend: str  # "increasing", "stable", "decreasing"
    risk_level: str  # "low", "medium", "high"
    next_actions: List[str]
    blockers: List[str]
    recommendations: List[str]

class ExecutionDriver:
    """
    Drives strategic plan execution and maintains momentum
    """

    def __init__(self, archon_integration: ArchonIntegration):
        self.archon = archon_integration
        self.monitoring_active = False
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load execution driver configuration"""
        return {
            "monitoring": {
                "check_interval_hours": 24,
                "momentum_threshold": 70,
                "velocity_window_days": 7,
                "risk_escalation_threshold": 3
            },
            "momentum": {
                "task_completion_weight": 0.4,
                "milestone_progress_weight": 0.3,
                "timeline_adherence_weight": 0.2,
                "stakeholder_engagement_weight": 0.1
            },
            "interventions": {
                "low_momentum_threshold": 50,
                "blocked_task_escalation_days": 3,
                "milestone_risk_days": 7
            }
        }

    async def start_monitoring(self, project_ids: List[str]) -> None:
        """Start continuous monitoring of strategic projects"""
        logger.info(f"Starting execution monitoring for {len(project_ids)} projects")

        self.monitoring_active = True

        while self.monitoring_active:
            try:
                for project_id in project_ids:
                    await self._monitor_project_execution(project_id)

                # Wait for next check interval
                await asyncio.sleep(self.config["monitoring"]["check_interval_hours"] * 3600)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error

    async def stop_monitoring(self) -> None:
        """Stop execution monitoring"""
        logger.info("Stopping execution monitoring")
        self.monitoring_active = False

    async def _monitor_project_execution(self, project_id: str) -> ExecutionStatus:
        """Monitor execution of a specific project"""
        logger.debug(f"Monitoring project execution: {project_id}")

        # Get current project status
        status_data = await self.archon.update_project_status(project_id)
        if "error" in status_data:
            logger.error(f"Failed to get project status: {status_data['error']}")
            return self._create_error_status()

        # Calculate momentum score
        momentum_score = self._calculate_momentum_score(status_data)

        # Analyze velocity trend
        velocity_trend = self._analyze_velocity_trend(project_id, status_data)

        # Assess risk level
        risk_level = self._assess_risk_level(status_data)

        # Identify next actions
        next_actions = self._identify_next_actions(status_data)

        # Identify blockers
        blockers = self._identify_blockers(status_data)

        # Generate recommendations
        recommendations = self._generate_execution_recommendations(
            momentum_score, velocity_trend, risk_level, status_data
        )

        execution_status = ExecutionStatus(
            momentum_score=momentum_score,
            velocity_trend=velocity_trend,
            risk_level=risk_level,
            next_actions=next_actions,
            blockers=blockers,
            recommendations=recommendations
        )

        # Take automated actions if needed
        await self._take_automated_actions(project_id, execution_status, status_data)

        return execution_status

    def _calculate_momentum_score(self, status_data: Dict[str, Any]) -> float:
        """Calculate momentum score (0-100)"""
        progress = status_data.get("progress", {})

        # Task completion rate
        task_completion = 0
        if progress.get("tasks", {}).get("total", 0) > 0:
            completed = progress["tasks"]["completed"]
            total = progress["tasks"]["total"]
            task_completion = (completed / total) * 100

        # Milestone progress
        milestone_progress = 0
        if progress.get("milestones", {}).get("total", 0) > 0:
            completed = progress["milestones"]["completed"]
            total = progress["milestones"]["total"]
            milestone_progress = (completed / total) * 100

        # Timeline adherence (simplified)
        timeline_adherence = 80  # Default assumption

        # Stakeholder engagement (simplified)
        stakeholder_engagement = 75  # Default assumption

        # Weighted score
        weights = self.config["momentum"]
        momentum = (
            task_completion * weights["task_completion_weight"] +
            milestone_progress * weights["milestone_progress_weight"] +
            timeline_adherence * weights["timeline_adherence_weight"] +
            stakeholder_engagement * weights["stakeholder_engagement_weight"]
        )

        return min(100, max(0, momentum))

    def _analyze_velocity_trend(self, project_id: str, status_data: Dict[str, Any]) -> str:
        """Analyze velocity trend over time"""
        # Simplified implementation - would track historical data in production
        progress = status_data.get("progress", {})
        overall_progress = progress.get("overall_percentage", 0)

        if overall_progress >= 75:
            return "increasing"
        elif overall_progress >= 25:
            return "stable"
        else:
            return "decreasing"

    def _assess_risk_level(self, status_data: Dict[str, Any]) -> str:
        """Assess current risk level"""
        at_risk_tasks = len(status_data.get("at_risk_tasks", []))
        upcoming_milestones = status_data.get("next_milestones", [])

        # Count milestones at risk
        at_risk_milestones = len([m for m in upcoming_milestones if m.get("at_risk", False)])

        if at_risk_tasks >= 5 or at_risk_milestones >= 2:
            return "high"
        elif at_risk_tasks >= 2 or at_risk_milestones >= 1:
            return "medium"
        else:
            return "low"

    def _identify_next_actions(self, status_data: Dict[str, Any]) -> List[str]:
        """Identify immediate next actions needed"""
        actions = []

        at_risk_tasks = status_data.get("at_risk_tasks", [])
        if at_risk_tasks:
            actions.append(f"Address {len(at_risk_tasks)} at-risk tasks immediately")

        upcoming_milestones = status_data.get("next_milestones", [])
        near_milestones = [m for m in upcoming_milestones if m.get("days_until", 999) <= 7]
        if near_milestones:
            actions.append(f"Prepare for {len(near_milestones)} upcoming milestones")

        progress = status_data.get("progress", {})
        if progress.get("overall_percentage", 0) < 25:
            actions.append("Accelerate task execution to improve progress")

        if not actions:
            actions.append("Continue steady execution of current plan")

        return actions

    def _identify_blockers(self, status_data: Dict[str, Any]) -> List[str]:
        """Identify current blockers"""
        blockers = []

        at_risk_tasks = status_data.get("at_risk_tasks", [])
        overdue_tasks = [t for t in at_risk_tasks if t.get("days_overdue", 0) > 0]

        if overdue_tasks:
            blockers.append(f"{len(overdue_tasks)} overdue tasks blocking progress")

        # Check for dependency blockers (simplified)
        if len(at_risk_tasks) > 3:
            blockers.append("Multiple at-risk tasks suggest resource constraints")

        return blockers

    def _generate_execution_recommendations(self, momentum_score: float, velocity_trend: str,
                                          risk_level: str, status_data: Dict[str, Any]) -> List[str]:
        """Generate execution recommendations"""
        recommendations = []

        # Momentum-based recommendations
        if momentum_score < self.config["interventions"]["low_momentum_threshold"]:
            recommendations.append("🚨 Low momentum detected - immediate intervention needed")
            recommendations.append("Schedule emergency stakeholder review")
            recommendations.append("Re-prioritize tasks to focus on quick wins")

        # Velocity-based recommendations
        if velocity_trend == "decreasing":
            recommendations.append("📉 Velocity declining - investigate root causes")
            recommendations.append("Consider resource reallocation")

        # Risk-based recommendations
        if risk_level == "high":
            recommendations.append("⚠️ High risk level - escalate to leadership")
            recommendations.append("Implement daily check-ins")

        # Progress-based recommendations
        progress = status_data.get("progress", {})
        if progress.get("overall_percentage", 0) < 50:
            recommendations.append("📊 Progress below 50% - review timeline and scope")

        if not recommendations:
            recommendations.append("✅ Execution on track - maintain current approach")

        return recommendations

    async def _take_automated_actions(self, project_id: str, execution_status: ExecutionStatus,
                                    status_data: Dict[str, Any]) -> None:
        """Take automated actions based on execution status"""

        # Send alerts for low momentum
        if execution_status.momentum_score < self.config["interventions"]["low_momentum_threshold"]:
            await self._send_momentum_alert(project_id, execution_status)

        # Escalate blocked tasks
        for blocker in execution_status.blockers:
            if "overdue" in blocker.lower():
                await self._escalate_blocked_tasks(project_id, status_data.get("at_risk_tasks", []))

        # Update project status in Archon
        await self._update_archon_status(project_id, execution_status)

    async def _send_momentum_alert(self, project_id: str, execution_status: ExecutionStatus) -> None:
        """Send momentum alert to stakeholders"""
        logger.warning(f"Low momentum alert for project {project_id}: {execution_status.momentum_score:.1f}%")

        # In production, this would send actual alerts
        alert_message = f"""
        🚨 MOMENTUM ALERT: Project {project_id}

        Current Momentum: {execution_status.momentum_score:.1f}%
        Trend: {execution_status.velocity_trend}
        Risk Level: {execution_status.risk_level}

        Immediate Actions Required:
        {chr(10).join(f"• {action}" for action in execution_status.next_actions)}

        Recommendations:
        {chr(10).join(f"• {rec}" for rec in execution_status.recommendations)}
        """

        logger.info(f"Momentum alert sent: {alert_message}")

    async def _escalate_blocked_tasks(self, project_id: str, at_risk_tasks: List[Dict[str, Any]]) -> None:
        """Escalate blocked tasks to appropriate stakeholders"""
        overdue_tasks = [t for t in at_risk_tasks if t.get("days_overdue", 0) > 0]

        if overdue_tasks:
            logger.warning(f"Escalating {len(overdue_tasks)} overdue tasks for project {project_id}")

            # In production, this would create escalation tickets
            for task in overdue_tasks:
                logger.info(f"Escalating task: {task.get('title')} (overdue by {task.get('days_overdue')} days)")

    async def _update_archon_status(self, project_id: str, execution_status: ExecutionStatus) -> None:
        """Update project status in Archon with execution insights"""
        try:
            # Add execution status to project metadata
            status_update = {
                "execution_momentum": execution_status.momentum_score,
                "velocity_trend": execution_status.velocity_trend,
                "risk_level": execution_status.risk_level,
                "last_monitoring_check": datetime.now().isoformat(),
                "active_recommendations": len(execution_status.recommendations),
                "active_blockers": len(execution_status.blockers)
            }

            logger.debug(f"Updated Archon status for project {project_id}: {status_update}")

        except Exception as e:
            logger.error(f"Failed to update Archon status: {e}")

    def _create_error_status(self) -> ExecutionStatus:
        """Create error status when monitoring fails"""
        return ExecutionStatus(
            momentum_score=0,
            velocity_trend="unknown",
            risk_level="high",
            next_actions=["Investigate monitoring system issues"],
            blockers=["Unable to retrieve project status"],
            recommendations=["Check system connectivity and data availability"]
        )

    async def generate_execution_report(self, project_id: str) -> str:
        """Generate comprehensive execution report"""
        try:
            execution_status = await self._monitor_project_execution(project_id)

            report = [
                "🚀 **Strategic Execution Report**",
                f"**Project ID:** {project_id}",
                f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                f"📊 **Execution Metrics:**",
                f"• Momentum Score: {execution_status.momentum_score:.1f}%",
                f"• Velocity Trend: {execution_status.velocity_trend.title()}",
                f"• Risk Level: {execution_status.risk_level.title()}",
                "",
                "🎯 **Next Actions:**"
            ]

            for action in execution_status.next_actions:
                report.append(f"• {action}")

            if execution_status.blockers:
                report.extend([
                    "",
                    "🚫 **Current Blockers:**"
                ])
                for blocker in execution_status.blockers:
                    report.append(f"• {blocker}")

            report.extend([
                "",
                "💡 **Recommendations:**"
            ])

            for recommendation in execution_status.recommendations:
                report.append(f"• {recommendation}")

            report.extend([
                "",
                "---",
                "*Report generated by Strategic Consultant Execution Driver*"
            ])

            return "\n".join(report)

        except Exception as e:
            logger.error(f"Failed to generate execution report: {e}")
            return f"❌ Error generating execution report: {str(e)}"

    async def get_momentum_dashboard(self, project_ids: List[str]) -> Dict[str, Any]:
        """Get momentum dashboard for multiple projects"""
        dashboard = {
            "overview": {
                "total_projects": len(project_ids),
                "high_momentum": 0,
                "medium_momentum": 0,
                "low_momentum": 0,
                "at_risk": 0
            },
            "projects": []
        }

        for project_id in project_ids:
            try:
                execution_status = await self._monitor_project_execution(project_id)

                project_summary = {
                    "id": project_id,
                    "momentum_score": execution_status.momentum_score,
                    "velocity_trend": execution_status.velocity_trend,
                    "risk_level": execution_status.risk_level,
                    "blocker_count": len(execution_status.blockers),
                    "recommendation_count": len(execution_status.recommendations)
                }

                dashboard["projects"].append(project_summary)

                # Update overview counts
                if execution_status.momentum_score >= 80:
                    dashboard["overview"]["high_momentum"] += 1
                elif execution_status.momentum_score >= 50:
                    dashboard["overview"]["medium_momentum"] += 1
                else:
                    dashboard["overview"]["low_momentum"] += 1

                if execution_status.risk_level == "high":
                    dashboard["overview"]["at_risk"] += 1

            except Exception as e:
                logger.error(f"Error getting momentum for project {project_id}: {e}")

        return dashboard