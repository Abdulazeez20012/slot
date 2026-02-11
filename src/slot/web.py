"""FastAPI Web UI for Slot Telegram Scraper."""

from pathlib import Path
import logging

from fastapi import BackgroundTasks, FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .config import TelegramConfig, config
from .exporters import get_exporter
from .scraper import TelegramScraper
from .storage import storage

# Initialize FastAPI app
app = FastAPI(
    title="Slot - Telegram Scraper",
    description="Web-based Telegram member scraper and exporter",
    version="0.1.0",
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Template directory
TEMPLATES_DIR = Path(__file__).parent / "templates"
TEMPLATES_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    await storage.initialize()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the main dashboard."""
    """Render the main dashboard."""
    is_authenticated = config.telegram is not None
    jobs = await storage.get_all_jobs()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "is_authenticated": is_authenticated,
            "jobs": jobs,
        }
    )


@app.get("/auth", response_class=HTMLResponse)
async def auth_page(request: Request):
    """Render the authentication page."""
    response = templates.TemplateResponse(
        "auth.html",
        {"request": request}
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


@app.post("/auth")
async def authenticate(
    api_id: int = Form(...),
    api_hash: str = Form(...),
):
    """Save Telegram credentials."""
    logger.info(f"Authenticating with api_id={api_id}, api_hash={api_hash[:4]}***")
    # Update config

    config.telegram = TelegramConfig(
        api_id=api_id,
        api_hash=api_hash,
    )
    
    # Save to .env
    env_path = Path(".env")
    env_content = f"""TELEGRAM_API_ID={api_id}
TELEGRAM_API_HASH={api_hash}
TELEGRAM_SESSION_NAME=slot_session
"""
    env_path.write_text(env_content)
    
    return RedirectResponse(url="/", status_code=303)


@app.get("/scrape", response_class=HTMLResponse)
async def scrape_page(request: Request):
    """Render the scrape form page."""
    """Render the scrape form page."""
    if config.telegram is None:
        return RedirectResponse(url="/auth", status_code=303)
    
    return templates.TemplateResponse(
        "scrape.html",
        {"request": request}
    )


async def run_scrape_job(job_id: str, group: str, limit: int | None, filter_status: str):
    """Background task to run scraping with persistent updates."""
    try:
        await storage.update_job(job_id, status="running", message="Connecting to Telegram...")
        
        async with TelegramScraper(config) as scraper:
            # Get group info
            group_info = await scraper.get_group_info(group)
            await storage.update_job(
                job_id, 
                group_title=group_info.title, 
                total_count=group_info.member_count,
                message=f"Scraping {group_info.title}..."
            )
            
            # Scrape members in batches and save
            members_batch = []
            async for member in scraper.scrape_members(group, limit):
                members_batch.append(member)
                
                # Save in batches of 50 to DB
                if len(members_batch) >= 50:
                    await storage.save_members(members_batch)
                    # Use length of gathered members or current progress if we tracked it differently
                    # Here we update based on how many we've seen
                    job = await storage.get_job(job_id)
                    if job:
                        current_progress = (job.get('progress') or 0) + len(members_batch)
                        await storage.update_job(job_id, progress=current_progress)
                    members_batch = []
            
            # Save any remaining
            if members_batch:
                await storage.save_members(members_batch)
                job = await storage.get_job(job_id)
                if job: # Added null check
                    current_progress = (job.get('progress') or 0) + len(members_batch)
                    await storage.update_job(job_id, progress=current_progress)
            
            # Final status update
            job = await storage.get_job(job_id)
            if job: # Added null check
                final_count = job.get('progress') or 0
                await storage.update_job(
                    job_id, 
                    status="complete", 
                    message=f"Scraped {final_count} members"
                )
    
    except Exception as e:
        logger.error(f"Scrape job {job_id} failed: {e}")
        await storage.update_job(job_id, status="error", message=str(e))


async def run_add_job(job_id: str, source_group: str, target_group: str, limit: int | None):
    """Background task to add members to a group."""
    try:
        await storage.update_job(job_id, status="running", message="Connecting to Telegram...")
        
        async with TelegramScraper(config) as scraper:
             # Get info
            source_info = await scraper.get_group_info(source_group)
            
            await storage.update_job(
                job_id, 
                group_title=f"{source_group} -> {target_group}",
                total_count=limit or source_info.member_count,
                message=f"Adding members from {source_group} to {target_group}..."
            )
            
            async for update in scraper.add_members(source_group, target_group, limit):
                if update["status"] == "added":
                    await storage.update_job(
                        job_id, 
                        progress=update["count"],
                        message=f"Added {update['user']}"
                    )
                elif update["status"] == "waiting":
                    await storage.update_job(
                        job_id, 
                        message=f"Safety sleep: {update['seconds']}s remaining"
                    )
                elif update["status"] == "error":
                     logger.error(f"Error adding member: {update['message']}")
            
            # Final
            job = await storage.get_job(job_id)
            final_count = job.get('progress') or 0
            await storage.update_job(
                job_id, 
                status="complete", 
                message=f"Finished. Added {final_count} members."
            )

    except Exception as e:
        logger.error(f"Add job {job_id} failed: {e}")
        await storage.update_job(job_id, status="error", message=str(e))


@app.post("/scrape")
async def start_scrape(
    background_tasks: BackgroundTasks,
    group: str = Form(...),
    limit: int | None = Form(None),
    filter_status: str = Form("all"),
):
    """Start a scraping job."""
    import uuid
    job_id = str(uuid.uuid4())[:8]
    
    await storage.create_job(job_id, group)
    background_tasks.add_task(run_scrape_job, job_id, group, limit, filter_status)
    
    return RedirectResponse(url=f"/results/{job_id}", status_code=303)


@app.get("/add", response_class=HTMLResponse)
async def add_page(request: Request):
    """Render the add members form page."""
    if config.telegram is None:
        return RedirectResponse(url="/auth", status_code=303)
    
    return templates.TemplateResponse(
        "add.html",
        {"request": request}
    )


@app.post("/add")
async def start_add(
    background_tasks: BackgroundTasks,
    source_group: str = Form(...),
    target_group: str = Form(...),
    limit: int | None = Form(None),
):
    """Start an add members job."""
    import uuid
    job_id = str(uuid.uuid4())[:8]
    
    # We treat it as a job with a special type/title for now
    await storage.create_job(job_id, f"{source_group} -> {target_group}")
    
    background_tasks.add_task(run_add_job, job_id, source_group, target_group, limit)
    
    return RedirectResponse(url=f"/results/{job_id}", status_code=303)


@app.get("/results/{job_id}", response_class=HTMLResponse)
async def results_page(request: Request, job_id: str):
    """Render the results page for a job."""
    job = await storage.get_job(job_id)
    if not job:
        return RedirectResponse(url="/", status_code=303)
        
    # For now, we show all members (could filter by group_id if we added it to member table)
    # Since we want performance, we just pull the last few members
    members = await storage.get_members(limit=100)
    
    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "job_id": job_id,
            "job": job,
            "members": members,
            "total": job.get('progress', 0),
        }
    )


@app.get("/api/job/{job_id}")
async def job_status(job_id: str):
    """Get job status (for polling)."""
    job = await storage.get_job(job_id)
    return job or {"status": "not_found"}


@app.get("/download/{job_id}/{format}")
async def download_results(job_id: str, format: str):
    """Download scraped results in specified format."""
    # Pull from database (all members for now)
    # Ideally we'd filter by group title or handle multiple groups better
    members = await storage.get_members(limit=100000) # Get all for now
    
    if not members:
        return {"error": "No data found"}
    
    # Export to temp file
    output_path = config.ensure_data_dir() / f"export_{job_id}"
    exporter = get_exporter(format)
    file_path = exporter.export(members, output_path)
    
    return FileResponse(
        path=str(file_path),
        filename=f"members_{job_id}.{format}",
        media_type="application/octet-stream",
    )


def run_server(host: str = "127.0.0.1", port: int = 8000):
    """Run the web server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)
