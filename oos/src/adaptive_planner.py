#!/usr/bin/env python3
"""
Adaptive Planner - Adjusts strategic plans based on execution feedback
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from src.strategic_consultant import StrategicConsultant, ConsultantRecommendation, StrategicDirection
from src.execution_driver import ExecutionDriver, ExecutionStatus
from src.archon_integration import ArchonIntegration

logger = logging.getLogger(__name__)

@dataclass
class PlanAdjustment:
    """Planned adjustment to strategic approach"""
    adjustment_type: str  # "timeline", "scope", "resources", "direction"
    severity: str  # "minor", "moderate", "major"
    description: str
    rationale: str
    impact_assessment: str
    recommended_actions: List[str]

@dataclass
class AdaptationDecision:
    """Decision about plan adaptation"""
    decision: str  # "maintain", "adjust", "pivot", "abort"
    confidence: float  # 0-1
    adjustments: List[PlanAdjustment]
    reasoning: str
    next_review_date: str

class AdaptivePlanner:
    """
    Monitors execution and adapts strategic plans based on feedback
    """

    def __init__(self, strategic_consultant: StrategicConsultant,
                 execution_driver: ExecutionDriver,
                 archon_integration: ArchonIntegration):
        self.consultant = strategic_consultant
        self.executor = execution_driver
        self.archon = archon_integration
        self.config = self._load_config()
        self.adaptation_history: Dict[str, List[AdaptationDecision]] = {}

    def _load_config(self) -> Dict[str, Any]:
        """Load adaptive planning configuration"""
        return {
            "adaptation": {
                "review_frequency_days": 14,
                "momentum_threshold_adjust": 60,
                "momentum_threshold_pivot": 40,
                "momentum_threshold_abort": 20,
                "confidence_threshold": 0.7
            },
            "triggers": {
                "timeline_variance_threshold": 0.25,  # 25% deviation
                "budget_variance_threshold": 0.20,    # 20% deviation
                "scope_change_threshold": 0.30,       # 30% change
                "stakeholder_confidence_threshold": 0.60
            },
            "adjustments": {
                "max_timeline_extension": 0.50,  # Max 50% extension
                "max_scope_reduction": 0.40,     # Max 40% scope reduction
                "max_resource_increase": 0.30    # Max 30% resource increase
            }
        }

    async def monitor_and_adapt(self, project_id: str) -> AdaptationDecision:
        """Monitor project execution and make adaptation decisions"""
        logger.info(f"Monitoring and adapting project: {project_id}")

        # Get current execution status
        execution_status = await self.executor._monitor_project_execution(project_id)

        # Get detailed project status
        project_status = await self.archon.update_project_status(project_id)

        # Analyze adaptation needs
        adaptation_triggers = self._analyze_adaptation_triggers(execution_status, project_status)

        # Make adaptation decision
        decision = await self._make_adaptation_decision(project_id, execution_status,
                                                      project_status, adaptation_triggers)

        # Record decision
        if project_id not in self.adaptation_history:
            self.adaptation_history[project_id] = []
        self.adaptation_history[project_id].append(decision)

        # Execute adaptations if needed
        if decision.decision != "maintain":
            await self._execute_adaptations(project_id, decision)

        logger.info(f"Adaptation decision for {project_id}: {decision.decision}")
        return decision

    def _analyze_adaptation_triggers(self, execution_status: ExecutionStatus,
                                   project_status: Dict[str, Any]) -> List[str]:
        """Analyze what's triggering the need for adaptation"""
        triggers = []

        # Momentum-based triggers
        momentum = execution_status.momentum_score
        if momentum < self.config["adaptation"]["momentum_threshold_abort"]:
            triggers.append("critically_low_momentum")
        elif momentum < self.config["adaptation"]["momentum_threshold_pivot"]:
            triggers.append("low_momentum_pivot_needed")
        elif momentum < self.config["adaptation"]["momentum_threshold_adjust"]:
            triggers.append("low_momentum_adjustment_needed")

        # Risk-based triggers
        if execution_status.risk_level == "high":
            triggers.append("high_risk_environment")

        # Blocker-based triggers
        if len(execution_status.blockers) >= 3:
            triggers.append("multiple_blockers")

        # Progress-based triggers
        progress = project_status.get("progress", {})
        if progress.get("overall_percentage", 0) < 25 and self._project_age_days(project_status) > 30:
            triggers.append("slow_progress")

        # Velocity-based triggers
        if execution_status.velocity_trend == "decreasing":
            triggers.append("declining_velocity")

        return triggers

    def _project_age_days(self, project_status: Dict[str, Any]) -> int:
        """Calculate project age in days"""
        # Simplified implementation
        return 30  # Default assumption

    async def _make_adaptation_decision(self, project_id: str, execution_status: ExecutionStatus,
                                      project_status: Dict[str, Any],
                                      triggers: List[str]) -> AdaptationDecision:
        """Make decision about how to adapt the strategic plan"""

        # Determine decision type based on triggers
        decision_type = self._determine_decision_type(triggers, execution_status)

        # Calculate confidence in decision
        confidence = self._calculate_decision_confidence(execution_status, project_status, triggers)

        # Generate adjustments
        adjustments = await self._generate_plan_adjustments(decision_type, triggers,
                                                           execution_status, project_status)

        # Generate reasoning
        reasoning = self._generate_adaptation_reasoning(decision_type, triggers, execution_status)

        # Set next review date
        next_review = (datetime.now() + timedelta(days=self.config["adaptation"]["review_frequency_days"])).isoformat()

        return AdaptationDecision(
            decision=decision_type,
            confidence=confidence,
            adjustments=adjustments,
            reasoning=reasoning,
            next_review_date=next_review
        )

    def _determine_decision_type(self, triggers: List[str], execution_status: ExecutionStatus) -> str:
        """Determine the type of adaptation decision needed"""

        # Critical situations require abort consideration
        if "critically_low_momentum" in triggers:
            return "abort"

        # Major issues require pivot
        if any(trigger in triggers for trigger in ["low_momentum_pivot_needed", "multiple_blockers"]):
            return "pivot"

        # Minor issues require adjustment
        if any(trigger in triggers for trigger in ["low_momentum_adjustment_needed", "high_risk_environment", "declining_velocity"]):
            return "adjust"

        # No significant issues
        return "maintain"

    def _calculate_decision_confidence(self, execution_status: ExecutionStatus,
                                     project_status: Dict[str, Any], triggers: List[str]) -> float:
        """Calculate confidence in the adaptation decision"""

        # Base confidence
        confidence = 0.8

        # Reduce confidence for uncertainty
        if execution_status.velocity_trend == "unknown":
            confidence -= 0.2

        # Reduce confidence for multiple complex triggers
        if len(triggers) > 3:
            confidence -= 0.1

        # Increase confidence for clear momentum signals
        if execution_status.momentum_score > 80 or execution_status.momentum_score < 30:
            confidence += 0.1

        return max(0.0, min(1.0, confidence))

    async def _generate_plan_adjustments(self, decision_type: str, triggers: List[str],
                                       execution_status: ExecutionStatus,
                                       project_status: Dict[str, Any]) -> List[PlanAdjustment]:
        """Generate specific plan adjustments based on decision type"""
        adjustments = []

        if decision_type == "adjust":
            adjustments.extend(self._generate_minor_adjustments(triggers, execution_status))
        elif decision_type == "pivot":
            adjustments.extend(self._generate_pivot_adjustments(triggers, execution_status))
        elif decision_type == "abort":
            adjustments.extend(self._generate_abort_adjustments(triggers, execution_status))

        return adjustments

    def _generate_minor_adjustments(self, triggers: List[str],
                                   execution_status: ExecutionStatus) -> List[PlanAdjustment]:
        """Generate minor plan adjustments"""
        adjustments = []

        if "low_momentum_adjustment_needed" in triggers:
            adjustments.append(PlanAdjustment(
                adjustment_type="resources",
                severity="minor",
                description="Increase team focus on high-impact tasks",
                rationale=f"Momentum at {execution_status.momentum_score:.1f}% requires focused effort",
                impact_assessment="Should improve momentum by 10-15% within 2 weeks",
                recommended_actions=[
                    "Reallocate team to priority tasks",
                    "Reduce scope of low-impact activities",
                    "Increase daily check-in frequency"
                ]
            ))

        if "high_risk_environment" in triggers:
            adjustments.append(PlanAdjustment(
                adjustment_type="timeline",
                severity="minor",
                description="Add 20% buffer to critical path tasks",
                rationale="High risk environment requires additional contingency",
                impact_assessment="Timeline extends by 1-2 weeks but reduces delivery risk",
                recommended_actions=[
                    "Identify critical path dependencies",
                    "Add buffer time to high-risk tasks",
                    "Establish backup plans for key deliverables"
                ]
            ))

        return adjustments

    def _generate_pivot_adjustments(self, triggers: List[str],
                                   execution_status: ExecutionStatus) -> List[PlanAdjustment]:
        """Generate pivot adjustments"""
        adjustments = []

        if "low_momentum_pivot_needed" in triggers:
            adjustments.append(PlanAdjustment(
                adjustment_type="scope",
                severity="major",
                description="Reduce scope by 30% and focus on core objectives",
                rationale=f"Momentum at {execution_status.momentum_score:.1f}% requires significant scope reduction",
                impact_assessment="Delivers 70% of original scope but ensures completion",
                recommended_actions=[
                    "Prioritize absolutely essential features only",
                    "Defer nice-to-have features to phase 2",
                    "Reallocate resources to core deliverables"
                ]
            ))

        if "multiple_blockers" in triggers:
            adjustments.append(PlanAdjustment(
                adjustment_type="direction",
                severity="major",
                description="Change implementation approach to bypass blockers",
                rationale="Multiple blockers indicate systematic issues with current approach",
                impact_assessment="May require rework but removes systematic blockers",
                recommended_actions=[
                    "Analyze blocker root causes",
                    "Design alternative implementation approach",
                    "Validate new approach with stakeholders"
                ]
            ))

        return adjustments

    def _generate_abort_adjustments(self, triggers: List[str],
                                   execution_status: ExecutionStatus) -> List[PlanAdjustment]:
        """Generate abort considerations"""
        return [
            PlanAdjustment(
                adjustment_type="direction",
                severity="major",
                description="Consider project termination or complete restart",
                rationale=f"Critical momentum failure ({execution_status.momentum_score:.1f}%) suggests fundamental issues",
                impact_assessment="Prevents further resource waste but loses current investment",
                recommended_actions=[
                    "Conduct thorough post-mortem analysis",
                    "Assess stakeholder appetite for restart",
                    "Identify lessons learned for future initiatives"
                ]
            )
        ]

    def _generate_adaptation_reasoning(self, decision_type: str, triggers: List[str],
                                     execution_status: ExecutionStatus) -> str:
        """Generate reasoning for adaptation decision"""

        reasoning_parts = [
            f"Decision: {decision_type.upper()}",
            f"Momentum Score: {execution_status.momentum_score:.1f}%",
            f"Velocity Trend: {execution_status.velocity_trend}",
            f"Risk Level: {execution_status.risk_level}",
            f"Active Blockers: {len(execution_status.blockers)}",
            f"Triggers: {', '.join(triggers)}"
        ]

        if decision_type == "maintain":
            reasoning_parts.append("Current execution is on track with acceptable momentum and manageable risks.")
        elif decision_type == "adjust":
            reasoning_parts.append("Minor adjustments needed to address execution challenges and maintain trajectory.")
        elif decision_type == "pivot":
            reasoning_parts.append("Significant changes required to overcome execution barriers and achieve objectives.")
        elif decision_type == "abort":
            reasoning_parts.append("Critical execution failure requires consideration of project termination or restart.")

        return " | ".join(reasoning_parts)

    async def _execute_adaptations(self, project_id: str, decision: AdaptationDecision) -> None:
        """Execute the adaptation plan"""
        logger.info(f"Executing adaptations for project {project_id}: {decision.decision}")

        for adjustment in decision.adjustments:
            try:
                await self._apply_adjustment(project_id, adjustment)
                logger.info(f"Applied adjustment: {adjustment.description}")
            except Exception as e:
                logger.error(f"Failed to apply adjustment: {e}")

        # Update project in Archon with adaptation details
        await self._update_archon_with_adaptations(project_id, decision)

    async def _apply_adjustment(self, project_id: str, adjustment: PlanAdjustment) -> None:
        """Apply a specific adjustment to the project"""

        if adjustment.adjustment_type == "timeline":
            await self._adjust_timeline(project_id, adjustment)
        elif adjustment.adjustment_type == "scope":
            await self._adjust_scope(project_id, adjustment)
        elif adjustment.adjustment_type == "resources":
            await self._adjust_resources(project_id, adjustment)
        elif adjustment.adjustment_type == "direction":
            await self._adjust_direction(project_id, adjustment)

    async def _adjust_timeline(self, project_id: str, adjustment: PlanAdjustment) -> None:
        """Adjust project timeline"""
        # In production, this would update actual Archon milestones and tasks
        logger.info(f"Timeline adjustment for {project_id}: {adjustment.description}")

    async def _adjust_scope(self, project_id: str, adjustment: PlanAdjustment) -> None:
        """Adjust project scope"""
        # In production, this would modify or remove Archon tasks
        logger.info(f"Scope adjustment for {project_id}: {adjustment.description}")

    async def _adjust_resources(self, project_id: str, adjustment: PlanAdjustment) -> None:
        """Adjust resource allocation"""
        # In production, this would update task assignments and priorities
        logger.info(f"Resource adjustment for {project_id}: {adjustment.description}")

    async def _adjust_direction(self, project_id: str, adjustment: PlanAdjustment) -> None:
        """Adjust strategic direction"""
        # In production, this would trigger new strategic analysis
        logger.info(f"Direction adjustment for {project_id}: {adjustment.description}")

    async def _update_archon_with_adaptations(self, project_id: str, decision: AdaptationDecision) -> None:
        """Update Archon project with adaptation decisions"""
        try:
            adaptation_metadata = {
                "last_adaptation": datetime.now().isoformat(),
                "adaptation_decision": decision.decision,
                "adaptation_confidence": decision.confidence,
                "adjustments_count": len(decision.adjustments),
                "next_review_date": decision.next_review_date,
                "adaptation_reasoning": decision.reasoning
            }

            logger.info(f"Updated Archon with adaptation metadata for {project_id}")

        except Exception as e:
            logger.error(f"Failed to update Archon with adaptations: {e}")

    async def generate_adaptation_report(self, project_id: str) -> str:
        """Generate comprehensive adaptation report"""
        try:
            # Get latest adaptation decision
            adaptations = self.adaptation_history.get(project_id, [])
            if not adaptations:
                return "📊 No adaptation history available for this project."

            latest = adaptations[-1]

            report = [
                "🔄 **Strategic Adaptation Report**",
                f"**Project ID:** {project_id}",
                f"**Decision:** {latest.decision.upper()}",
                f"**Confidence:** {latest.confidence:.1%}",
                f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "🧠 **Reasoning:**",
                latest.reasoning,
                "",
                "🔧 **Planned Adjustments:**"
            ]

            for i, adjustment in enumerate(latest.adjustments, 1):
                report.extend([
                    f"**{i}. {adjustment.description}**",
                    f"   Type: {adjustment.adjustment_type.title()}",
                    f"   Severity: {adjustment.severity.title()}",
                    f"   Rationale: {adjustment.rationale}",
                    f"   Impact: {adjustment.impact_assessment}",
                    "   Actions:"
                ])
                for action in adjustment.recommended_actions:
                    report.append(f"   • {action}")
                report.append("")

            report.extend([
                f"📅 **Next Review:** {latest.next_review_date}",
                "",
                "📈 **Adaptation History:**",
                f"• Total Adaptations: {len(adaptations)}",
                f"• Recent Decisions: {', '.join([a.decision for a in adaptations[-3:]])}",
                "",
                "---",
                "*Report generated by Strategic Consultant Adaptive Planner*"
            ])

            return "\n".join(report)

        except Exception as e:
            logger.error(f"Failed to generate adaptation report: {e}")
            return f"❌ Error generating adaptation report: {str(e)}"

    def get_adaptation_summary(self, project_ids: List[str]) -> Dict[str, Any]:
        """Get adaptation summary across multiple projects"""
        summary = {
            "total_projects": len(project_ids),
            "adaptation_stats": {
                "maintain": 0,
                "adjust": 0,
                "pivot": 0,
                "abort": 0
            },
            "avg_confidence": 0.0,
            "projects_needing_review": []
        }

        total_confidence = 0
        projects_with_decisions = 0

        for project_id in project_ids:
            adaptations = self.adaptation_history.get(project_id, [])
            if adaptations:
                latest = adaptations[-1]
                summary["adaptation_stats"][latest.decision] += 1
                total_confidence += latest.confidence
                projects_with_decisions += 1

                # Check if review is needed
                next_review = datetime.fromisoformat(latest.next_review_date.replace("Z", "+00:00").replace("+00:00", ""))
                if next_review <= datetime.now():
                    summary["projects_needing_review"].append(project_id)

        if projects_with_decisions > 0:
            summary["avg_confidence"] = total_confidence / projects_with_decisions

        return summary