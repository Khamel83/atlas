"""
Simple REST API for Atlas

Provides mobile and desktop integration endpoints for the simplified Atlas system.
FastAPI-based with automatic documentation and CORS support.
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio
import logging
import time
import json
from datetime import datetime
from pathlib import Path
import uvicorn

from core.database import get_database, Content, UniversalDatabase, reset_database
from core.processor import get_processor, ProcessingResult
from helpers.ingestion_reliability_manager import get_reliability_manager
from helpers.metrics_collector import get_metrics_collector, get_health_summary, get_prometheus_metrics
from helpers.logging_config import get_logger, PerformanceLogger
from helpers.alerting_service import get_alerting_service, Alert
from helpers.monitoring_dashboard_service import router as monitoring_router
from modules.gmail.auth import GmailAuthManager
from modules.gmail.processor import GmailProcessor
from modules.gmail.webhook import GmailWebhookManager


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = get_logger("api")
perf_logger = PerformanceLogger()

# Initialize FastAPI app
app = FastAPI(
    title="Atlas API",
    description="Simple API for Atlas content management system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for mobile/web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include monitoring dashboard router
app.include_router(monitoring_router)


# Gmail integration instances (lazy loading to avoid import issues)
gmail_auth_manager = None
gmail_processor = None
gmail_webhook_manager = None

def get_gmail_auth_manager():
    global gmail_auth_manager
    if gmail_auth_manager is None:
        gmail_auth_manager = GmailAuthManager()
    return gmail_auth_manager

def get_gmail_processor():
    global gmail_processor
    if gmail_processor is None:
        gmail_processor = GmailProcessor(get_gmail_auth_manager())
    return gmail_processor

def get_gmail_webhook_manager():
    global gmail_webhook_manager
    if gmail_webhook_manager is None:
        gmail_webhook_manager = GmailWebhookManager(get_gmail_auth_manager(), get_gmail_processor())
    return gmail_webhook_manager


# Pydantic models for API
class ContentRequest(BaseModel):
    """Request model for adding content"""
    content: str = Field(..., description="Content to process (URL, text, etc.)")
    title: Optional[str] = Field(None, description="Optional title for the content")
    source: Optional[str] = Field(None, description="Source of the content")


class ContentResponse(BaseModel):
    """Response model for content operations"""
    id: int
    title: str
    url: Optional[str]
    content_type: str
    created_at: str
    updated_at: str
    stage: int
    ai_summary: Optional[str]
    ai_tags: Optional[str]


class BatchContentRequest(BaseModel):
    """Request model for batch content processing"""
    items: List[ContentRequest] = Field(..., description="List of content items to process")


class SearchRequest(BaseModel):
    """Request model for search operations"""
    query: str = Field(..., description="Search query")
    limit: int = Field(50, description="Maximum number of results")
    offset: int = Field(0, description="Offset for pagination")


class HealthResponse(BaseModel):
    """Response model for health checks"""
    status: str
    database: str
    processor: str
    total_content: int
    timestamp: str


class MetricsResponse(BaseModel):
    """Response model for metrics queries"""
    timestamp: str
    metrics: Dict[str, Any]
    health_summary: Dict[str, Any]
    alerts: List[Dict[str, Any]]


class LogsResponse(BaseModel):
    """Response model for log queries"""
    logs: List[Dict[str, Any]]
    total_count: int
    page: int
    per_page: int


class SystemInfoResponse(BaseModel):
    """Response model for system information"""
    hostname: str
    os_version: str
    python_version: str
    uptime_seconds: float
    memory_usage_mb: float
    disk_usage_gb: float
    cpu_usage_percent: float
    load_average: List[float]
    timestamp: str


class GmailWebhookResponse(BaseModel):
    """Response model for Gmail webhook operations"""
    status: str
    message: str


class GmailAuthResponse(BaseModel):
    """Response model for Gmail authentication operations"""
    success: bool
    email_address: Optional[str] = None
    error: Optional[str] = None


# Dependency to get database instance
async def get_db():
    """Get database instance"""
    return get_database()


# Dependency to get processor instance
async def get_proc():
    """Get processor instance"""
    return get_processor()


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Atlas API",
        "version": "1.0.0",
        "description": "Simple content management system API",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "content": "/content",
            "search": "/search",
            "stats": "/stats"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        db = get_database()
        processor = get_processor()

        # Check database
        stats = db.get_statistics()
        db_status = "healthy" if stats else "unhealthy"

        # Check processor
        processor_health = await processor.health_check()
        proc_status = processor_health['status']

        overall_status = "healthy"
        if db_status == "unhealthy" or proc_status == "degraded":
            overall_status = "degraded"
        elif db_status == "unhealthy" and proc_status == "degraded":
            overall_status = "unhealthy"

        return HealthResponse(
            status=overall_status,
            database=db_status,
            processor=proc_status,
            total_content=stats.get('total_content', 0) if stats else 0,
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/content", response_model=ContentResponse)
async def add_content(
    request: ContentRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    processor=Depends(get_proc)
):
    """Add and process new content"""
    try:
        # Process content in background
        result = await processor.process(
            request.content,
            title=request.title or f"Content - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        )

        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)

        # Return processed content
        return ContentResponse(
            id=result.content.id,
            title=result.content.title,
            url=result.content.url,
            content_type=result.content.content_type,
            created_at=result.content.created_at,
            updated_at=result.content.updated_at,
            stage=result.content.stage,
            ai_summary=result.content.ai_summary,
            ai_tags=result.content.ai_tags
        )
    except Exception as e:
        logger.error(f"Failed to add content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/content/batch")
async def add_content_batch(
    request: BatchContentRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    processor=Depends(get_proc)
):
    """Add and process multiple content items"""
    try:
        results = await processor.process_batch([
            item.content for item in request.items
        ])

        successful = 0
        failed = 0
        processed_items = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed += 1
                logger.error(f"Item {i+1} failed: {result}")
            elif result.success:
                successful += 1
                processed_items.append({
                    "id": result.content.id,
                    "title": result.content.title,
                    "status": "success"
                })
            else:
                failed += 1
                logger.error(f"Item {i+1} failed: {result.error}")

        return {
            "total_items": len(request.items),
            "successful": successful,
            "failed": failed,
            "processed_items": processed_items
        }
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/content/{content_id}", response_model=ContentResponse)
async def get_content(content_id: int, db=Depends(get_db)):
    """Get specific content by ID"""
    try:
        content = db.get_content(content_id)
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        return ContentResponse(
            id=content.id,
            title=content.title,
            url=content.url,
            content_type=content.content_type,
            created_at=content.created_at,
            updated_at=content.updated_at,
            stage=content.stage,
            ai_summary=content.ai_summary,
            ai_tags=content.ai_tags
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get content {content_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search")
async def search_content(request: SearchRequest, db=Depends(get_db)):
    """Search content"""
    try:
        results = db.search_content(
            request.query,
            limit=request.limit,
            offset=request.offset
        )

        return {
            "query": request.query,
            "limit": request.limit,
            "offset": request.offset,
            "total_results": len(results),
            "results": [
                {
                    "id": content.id,
                    "title": content.title,
                    "url": content.url,
                    "content_type": content.content_type,
                    "created_at": content.created_at,
                    "stage": content.stage,
                    "ai_summary": content.ai_summary
                }
                for content in results
            ]
        }
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/content")
async def list_content(
    limit: int = 50,
    offset: int = 0,
    content_type: Optional[str] = None,
    stage: Optional[int] = None,
    db=Depends(get_db)
):
    """List content with optional filtering"""
    try:
        # Build query conditions
        conditions = []
        params = []

        if content_type:
            conditions.append("content_type = ?")
            params.append(content_type)

        if stage is not None:
            conditions.append("stage = ?")
            params.append(stage)

        # Build WHERE clause
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        # Build query
        query = f"""
            SELECT id, title, url, content_type, created_at, updated_at, stage, ai_summary
            FROM content
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        # Execute query
        conn = db.get_connection()
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        # Convert to response format
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "title": row[1],
                "url": row[2],
                "content_type": row[3],
                "created_at": row[4],
                "updated_at": row[5],
                "stage": row[6],
                "ai_summary": row[7]
            })

        return {
            "limit": limit,
            "offset": offset,
            "total_results": len(results),
            "results": results
        }
    except Exception as e:
        logger.error(f"Failed to list content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats(db=Depends(get_db)):
    """Get system statistics"""
    try:
        stats = db.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reliability")
async def get_reliability_status():
    """Get ingestion reliability status"""
    try:
        reliability_manager = get_reliability_manager()
        status = reliability_manager.get_reliability_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get reliability status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/content/{content_id}")
async def delete_content(content_id: int, db=Depends(get_db)):
    """Delete content by ID"""
    try:
        success = db.delete_content(content_id)
        if not success:
            raise HTTPException(status_code=404, detail="Content not found")

        return {"message": "Content deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete content {content_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/content/types")
async def get_content_types(db=Depends(get_db)):
    """Get available content types"""
    try:
        conn = db.get_connection()
        cursor = conn.execute("""
            SELECT DISTINCT content_type, COUNT(*) as count
            FROM content
            GROUP BY content_type
            ORDER BY count DESC
        """)
        results = cursor.fetchall()

        return {
            "content_types": [
                {"type": row[0], "count": row[1]}
                for row in results
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get content types: {e}", component="api", endpoint="/content/types")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Get comprehensive system metrics"""
    try:
        metrics_collector = get_metrics_collector()
        health_summary = get_health_summary()

        # Get all current metric values
        metrics_data = {}
        for metric_name, metric in metrics_collector._metrics.items():
            latest_value = metrics_collector.get_metric_value(metric_name)
            if latest_value is not None:
                metrics_data[metric_name] = latest_value

        return MetricsResponse(
            timestamp=datetime.utcnow().isoformat(),
            metrics=metrics_data,
            health_summary=health_summary,
            alerts=health_summary.get("alerts", [])
        )
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}", component="api", endpoint="/metrics")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/prometheus")
async def get_prometheus_endpoint():
    """Get metrics in Prometheus format"""
    try:
        prometheus_metrics = get_prometheus_metrics()
        return PlainTextResponse(content=prometheus_metrics, media_type="text/plain")
    except Exception as e:
        logger.error(f"Failed to get Prometheus metrics: {e}", component="api", endpoint="/metrics/prometheus")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/system/info", response_model=SystemInfoResponse)
async def get_system_info():
    """Get detailed system information"""
    try:
        import platform
        import psutil
        import os

        # System information
        hostname = platform.node()
        os_version = platform.platform()
        python_version = platform.python_version()

        # Performance metrics
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Uptime
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time

        # CPU and load
        cpu_usage = psutil.cpu_percent(interval=1)
        load_avg = os.getloadavg()

        return SystemInfoResponse(
            hostname=hostname,
            os_version=os_version,
            python_version=python_version,
            uptime_seconds=uptime_seconds,
            memory_usage_mb=memory.used / (1024 * 1024),
            disk_usage_gb=disk.used / (1024 * 1024 * 1024),
            cpu_usage_percent=cpu_usage,
            load_average=list(load_avg),
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        logger.error(f"Failed to get system info: {e}", component="api", endpoint="/system/info")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs")
async def get_logs(
    level: Optional[str] = None,
    component: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """Get system logs with filtering"""
    try:
        # This is a simplified implementation - in production you'd use proper log aggregation
        logger_instance = get_logger("api")

        # Get logs from the log file (simplified for demo)
        logs_dir = Path("/var/log/atlas")
        if not logs_dir.exists():
            logs_dir = Path("logs/atlas")

        logs = []
        log_file = logs_dir / "atlas.json.log"

        if log_file.exists():
            with open(log_file, 'r') as f:
                lines = f.readlines()

            # Parse JSON logs (in reverse order for newest first)
            for line in reversed(lines):
                try:
                    log_entry = json.loads(line.strip())

                    # Apply filters
                    if level and log_entry.get('level') != level:
                        continue
                    if component and log_entry.get('component') != component:
                        continue

                    logs.append(log_entry)

                    if len(logs) >= limit + offset:
                        break

                except (json.JSONDecodeError, KeyError):
                    continue

        # Paginate
        paginated_logs = logs[offset:offset + limit]

        return LogsResponse(
            logs=paginated_logs,
            total_count=len(logs),
            page=offset // limit + 1,
            per_page=limit
        )
    except Exception as e:
        logger.error(f"Failed to get logs: {e}", component="api", endpoint="/logs")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/metrics/performance-snapshot")
async def trigger_performance_snapshot():
    """Trigger an immediate performance snapshot"""
    try:
        perf_logger.log_performance_snapshot(force=True)
        return {"message": "Performance snapshot triggered", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Failed to trigger performance snapshot: {e}", component="api", endpoint="/metrics/performance-snapshot")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/alerts")
async def get_alerts():
    """Get current system alerts"""
    try:
        metrics_collector = get_metrics_collector()
        alerts = metrics_collector.get_alert_conditions()

        return {
            "alerts": alerts,
            "timestamp": datetime.utcnow().isoformat(),
            "total_alerts": len(alerts),
            "critical_alerts": len([a for a in alerts if a["severity"] == "critical"]),
            "warning_alerts": len([a for a in alerts if a["severity"] == "warning"])
        }
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}", component="api", endpoint="/alerts")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health/detailed")
async def get_detailed_health():
    """Get detailed health status with component breakdown"""
    try:
        # Get basic health
        db = get_database()
        processor = get_processor()
        reliability_manager = get_reliability_manager()
        metrics_collector = get_metrics_collector()

        # Database health
        try:
            stats = db.get_statistics()
            db_health = {
                "status": "healthy" if stats else "unhealthy",
                "total_content": stats.get('total_content', 0) if stats else 0,
                "last_update": stats.get('last_update') if stats else None
            }
        except Exception as e:
            db_health = {"status": "unhealthy", "error": str(e)}

        # Processor health
        try:
            processor_health = await processor.health_check()
        except Exception as e:
            processor_health = {"status": "unhealthy", "error": str(e)}

        # Reliability health
        reliability_status = reliability_manager.get_reliability_status()

        # Metrics health
        health_summary = get_health_summary()

        # Overall health determination
        component_status = [
            db_health.get("status", "unhealthy"),
            processor_health.get("status", "unhealthy"),
            health_summary.get("status", "unhealthy")
        ]

        if "critical" in component_status:
            overall_status = "critical"
        elif "unhealthy" in component_status:
            overall_status = "unhealthy"
        elif "warning" in component_status or "degraded" in component_status:
            overall_status = "warning"
        else:
            overall_status = "healthy"

        return {
            "overall_status": overall_status,
            "components": {
                "database": db_health,
                "processor": processor_health,
                "reliability": reliability_status,
                "metrics": health_summary
            },
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": time.time() - app.startup_time if hasattr(app, 'startup_time') else 0
        }
    except Exception as e:
        logger.error(f"Failed to get detailed health: {e}", component="api", endpoint="/health/detailed")
        raise HTTPException(status_code=500, detail=str(e))


# Alerting endpoints
class AlertRequest(BaseModel):
    """Request model for creating/updating alerts."""
    id: str = Field(..., description="Unique alert identifier")
    name: str = Field(..., description="Alert name")
    severity: str = Field(..., description="Alert severity: critical, warning, info")
    condition: str = Field(..., description="Alert condition description")
    description: str = Field(..., description="Alert description")
    metric_name: str = Field(..., description="Metric to monitor")
    threshold: float = Field(..., description="Alert threshold")
    operator: str = Field(..., description="Comparison operator: gt, lt, eq, gte, lte")
    duration: int = Field(..., description="Duration condition must be met (seconds)")
    cooldown: int = Field(300, description="Cooldown between alerts (seconds)")
    enabled: bool = Field(True, description="Whether alert is enabled")
    channels: List[str] = Field(["log"], description="Notification channels")


@app.get("/alerts")
async def get_all_alerts():
    """Get all alerts including active and history."""
    try:
        alerting_service = get_alerting_service()
        active_alerts = alerting_service.get_active_alerts()
        alert_history = alerting_service.get_alert_history(50)
        alert_status = alerting_service.get_alert_status()

        return {
            "active_alerts": active_alerts,
            "alert_history": alert_history,
            "alert_status": alert_status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}", component="api", endpoint="/alerts")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/alerts")
async def create_alert(alert_request: AlertRequest):
    """Create a new alert."""
    try:
        alerting_service = get_alerting_service()
        alert = Alert(**alert_request.model_dump())
        alerting_service.add_alert(alert)

        logger.info(f"Created new alert: {alert.name}", alert_id=alert.id)
        return {"message": "Alert created successfully", "alert_id": alert.id}
    except Exception as e:
        logger.error(f"Failed to create alert: {e}", component="api", endpoint="/alerts")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/alerts/{alert_id}")
async def update_alert(alert_id: str, alert_request: AlertRequest):
    """Update an existing alert."""
    try:
        alerting_service = get_alerting_service()
        alert = Alert(**alert_request.model_dump())
        alerting_service.remove_alert(alert_id)  # Remove old one
        alerting_service.add_alert(alert)  # Add updated one

        logger.info(f"Updated alert: {alert.name}", alert_id=alert.id)
        return {"message": "Alert updated successfully", "alert_id": alert.id}
    except Exception as e:
        logger.error(f"Failed to update alert: {e}", component="api", endpoint=f"/alerts/{alert_id}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str):
    """Delete an alert."""
    try:
        alerting_service = get_alerting_service()
        alerting_service.remove_alert(alert_id)

        logger.info(f"Deleted alert: {alert_id}")
        return {"message": "Alert deleted successfully", "alert_id": alert_id}
    except Exception as e:
        logger.error(f"Failed to delete alert: {e}", component="api", endpoint=f"/alerts/{alert_id}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/alerts/test")
async def test_alert_notification():
    """Send a test alert notification."""
    try:
        alerting_service = get_alerting_service()

        # Create a test alert
        test_alert = Alert(
            id="test_alert",
            name="Test Alert",
            severity="info",
            condition="test == true",
            description="This is a test alert",
            metric_name="test_metric",
            threshold=1,
            operator="eq",
            duration=0,
            cooldown=0,
            channels=["log"]  # Only log for testing
        )

        # Send test notification
        from helpers.alerting_service import AlertInstance
        test_instance = AlertInstance(
            alert_id="test_alert",
            triggered_at=time.time(),
            current_value=1.0
        )

        await alerting_service._send_notifications(test_alert, test_instance)

        return {
            "message": "Test alert notification sent",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to send test alert: {e}", component="api", endpoint="/alerts/test")
        raise HTTPException(status_code=500, detail=str(e))


# Gmail integration endpoints
@app.post("/gmail/webhook", response_model=GmailWebhookResponse)
async def gmail_webhook(request):
    """Handle Gmail Pub/Sub webhook notifications."""
    try:
        # Extract headers and body
        headers = dict(request.headers)
        body = await request.body()

        # Process the webhook
        webhook_manager = get_gmail_webhook_manager()
        result = await webhook_manager.handle_webhook(headers, body)

        return result
    except Exception as e:
        logger.error(f"Gmail webhook error: {e}", component="api", endpoint="/gmail/webhook")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/gmail/auth/status", response_model=GmailAuthResponse)
async def gmail_auth_status():
    """Check Gmail authentication status."""
    try:
        auth_manager = get_gmail_auth_manager()
        if auth_manager.is_authenticated():
            # Test the connection
            test_result = await auth_manager.test_connection()
            if test_result["success"]:
                return GmailAuthResponse(
                    success=True,
                    email_address=test_result["email_address"]
                )
            else:
                return GmailAuthResponse(
                    success=False,
                    error=test_result["error"]
                )
        else:
            return GmailAuthResponse(
                success=False,
                error="Not authenticated"
            )
    except Exception as e:
        logger.error(f"Gmail auth status check error: {e}", component="api", endpoint="/gmail/auth/status")
        return GmailAuthResponse(
            success=False,
            error=str(e)
        )


@app.post("/gmail/auth", response_model=GmailAuthResponse)
async def gmail_authenticate():
    """Start Gmail OAuth2 authentication flow."""
    try:
        # This will trigger the OAuth flow if not authenticated
        auth_manager = get_gmail_auth_manager()
        test_result = await auth_manager.test_connection()

        if test_result["success"]:
            return GmailAuthResponse(
                success=True,
                email_address=test_result["email_address"]
            )
        else:
            return GmailAuthResponse(
                success=False,
                error=test_result["error"]
            )
    except Exception as e:
        logger.error(f"Gmail authentication error: {e}", component="api", endpoint="/gmail/auth")
        return GmailAuthResponse(
            success=False,
            error=str(e)
        )


@app.get("/gmail/stats")
async def gmail_stats(db=Depends(get_db)):
    """Get Gmail integration statistics."""
    try:
        # Get Gmail content statistics
        gmail_content = db.search_content(
            query="content_type:gmail_atlas OR content_type:gmail_newsletter",
            limit=1000
        )

        atlas_count = len([c for c in gmail_content if c.content_type == "gmail_atlas"])
        newsletter_count = len([c for c in gmail_content if c.content_type == "gmail_newsletter"])

        auth_manager = get_gmail_auth_manager()

        return {
            "total_gmail_content": len(gmail_content),
            "atlas_content": atlas_count,
            "newsletter_content": newsletter_count,
            "authenticated": auth_manager.is_authenticated(),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Gmail stats error: {e}", component="api", endpoint="/gmail/stats")
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info("Atlas API starting up...")
    try:
        # Record startup time
        app.startup_time = time.time()

        # Initialize database and processor with absolute config path
        reset_database()  # Clear any cached instances
        db = UniversalDatabase(config_path="/home/ubuntu/dev/atlas/config/database.yaml")
        processor = get_processor()
        logger.info("Database and processor initialized successfully")

        # Initialize ingestion reliability manager
        reliability_manager = get_reliability_manager()
        reliability_manager.start_reliability_manager()
        logger.info("Ingestion reliability manager started")

        # Initialize metrics collection
        from helpers.metrics_collector import start_metrics_collection
        start_metrics_collection()
        logger.info("Metrics collection started")

        # Initialize alerting service
        from helpers.alerting_service import start_alerting
        start_alerting()
        logger.info("Alerting service started")

        # Log successful startup
        logger.info("Atlas API startup completed successfully",
                  startup_time=datetime.utcnow().isoformat())
    except Exception as e:
        logger.error(f"Startup failed: {e}", component="api", endpoint="startup")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info("Atlas API shutting down...")
    try:
        # Cleanup processor resources
        processor = get_processor()
        await processor.close()
        logger.info("Processor resources cleaned up")

        # Stop metrics collection
        from helpers.metrics_collector import stop_metrics_collection
        stop_metrics_collection()
        logger.info("Metrics collection stopped")

        # Stop reliability manager
        reliability_manager = get_reliability_manager()
        reliability_manager.stop_reliability_manager()
        logger.info("Reliability manager stopped")

        # Stop alerting service
        from helpers.alerting_service import stop_alerting
        stop_alerting()
        logger.info("Alerting service stopped")

        logger.info("Atlas API shutdown completed successfully")
    except Exception as e:
        logger.error(f"Shutdown cleanup failed: {e}", component="api", endpoint="shutdown")


if __name__ == "__main__":
    # Run the API server
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=7444,
        reload=True,
        log_level="info"
    )