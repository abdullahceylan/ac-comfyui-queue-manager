"""
ComfyUI Queue Manager Custom Node
A comprehensive queue management system for ComfyUI workflows.
"""

import os
import mimetypes
from pathlib import Path
import shutil
import sys

# Add the current directory to Python path for imports
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Import ComfyUI modules with error handling
try:
    from aiohttp import web as aiohttp_web
    import folder_paths
    import server
except ImportError:
    # ComfyUI modules not available, will handle gracefully
    folder_paths = None
    server = None
    aiohttp_web = None

from queue_manager_node import QueueManagerNode

# ComfyUI custom node registration
NODE_CLASS_MAPPINGS = {
    "QueueManagerNode": QueueManagerNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "QueueManagerNode": "Queue Manager",
}

# Web directory for serving static files (following official convention)
WEB_DIRECTORY = "./web"

# Extension metadata
__version__ = "1.0.0"
__author__ = "AC ComfyUI Queue Manager"
__description__ = "A comprehensive queue management system for ComfyUI workflows"


def setup_web_routes():
    """Set up web routes for serving Queue Manager files."""
    if not server or not aiohttp_web:
        print("[Queue Manager] ComfyUI server modules not available")
        return False

    try:
        prompt_server = server.PromptServer.instance
        if not prompt_server:
            print("[Queue Manager] PromptServer instance not available")
            return False
            
        if not hasattr(prompt_server, "app"):
            print("[Queue Manager] PromptServer app not available")
            return False

        async def serve_extension_file(request):
            """Serve extension files."""
            filename = request.match_info.get("filename", "")
            file_path = current_dir / "web" / filename
            
            print(f"[Queue Manager] Serving file request: {filename}")
            print(f"[Queue Manager] File path: {file_path}")
            print(f"[Queue Manager] File exists: {file_path.exists()}")
            
            if file_path.exists():
                print(f"[Queue Manager] File size: {file_path.stat().st_size} bytes")

            if not file_path.exists():
                print(f"[Queue Manager] File not found: {file_path}")
                return aiohttp_web.Response(status=404, text="File not found")

            # Determine content type
            content_type, _ = mimetypes.guess_type(str(file_path))
            if not content_type:
                if filename.endswith(".js"):
                    content_type = "application/javascript"
                elif filename.endswith(".html"):
                    content_type = "text/html"
                elif filename.endswith(".css"):
                    content_type = "text/css"
                else:
                    content_type = "text/plain"

            try:
                # Check file size to prevent memory issues
                file_size = file_path.stat().st_size
                if file_size > 10 * 1024 * 1024:  # 10MB limit
                    return aiohttp_web.Response(
                        status=413, text="File too large"
                    )
                
                with file_path.open(encoding="utf-8") as f:
                    content = f.read()
                return aiohttp_web.Response(text=content, content_type=content_type)
            except UnicodeDecodeError as e:
                print(f"[Queue Manager] Unicode decode error for {filename}: {e}")
                return aiohttp_web.Response(
                    status=500, text=f"File encoding error: {e}"
                )
            except OSError as e:
                print(f"[Queue Manager] OS error reading {filename}: {e}")
                return aiohttp_web.Response(
                    status=500, text=f"Error reading file: {e}"
                )
            except Exception as e:
                print(f"[Queue Manager] Unexpected error reading {filename}: {e}")
                return aiohttp_web.Response(
                    status=500, text=f"Unexpected error: {e}"
                )

        # Register routes for serving web files
        prompt_server.app.router.add_get(
            "/extensions/comfyui-queue-manager/{filename}", serve_extension_file
        )

        print("[Queue Manager] Web routes registered")
        return True

    except Exception as e:
        print(f"[Queue Manager] Failed to register web routes: {e}")
        return False


def initialize_queue_manager():
    """Initialize the queue manager system."""
    try:
        # Initialize logging and monitoring first
        from logging_config import setup_logging
        from performance_monitor import setup_performance_monitoring
        from health_check import setup_health_checks
        
        # Set up logging
        log_dir = current_dir / "logs"
        logging_config = setup_logging(
            log_dir=log_dir,
            console_level=20,  # INFO level
            file_level=10,     # DEBUG level
            structured=True
        )
        
        logger = logging_config.get_logger("init")
        logger.info(f"Queue Manager logging initialized (v{__version__})")
        
        # Set up performance monitoring
        perf_monitor = setup_performance_monitoring(max_history_size=1000)
        logger.info("Performance monitoring initialized")
        
        # Import and initialize core services
        from api_routes import QueueManagerAPI
        from database import SQLiteDatabase
        from queue_service import QueueService

        # Initialize database
        db_path = current_dir / "queue_manager.db"
        database = SQLiteDatabase(str(db_path))
        database.initialize()
        logger.info("Database initialized")

        # Initialize queue service
        queue_service = QueueService(database)
        logger.info("Queue service initialized")

        # Set up health checks with actual services
        health_manager = setup_health_checks(database=database, queue_service=queue_service)
        health_manager.start_monitoring(interval=300.0)  # 5 minutes
        logger.info("Health monitoring started")

        # Set up API routes (will be used by the web interface)
        api = QueueManagerAPI(queue_service)
        logger.info("API routes initialized")

        logger.info(f"Queue Manager initialized successfully (v{__version__})")
        print(f"[Queue Manager] Initialized successfully (v{__version__})")
        return True

    except Exception as e:
        # Fall back to basic logging if initialization fails
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger("queue_manager.init")
        logger.error(f"Failed to initialize queue manager: {e}")
        print(f"[Queue Manager] Failed to initialize: {e}")
        return False


# Initialize on import, unless explicitly disabled to prevent reconnect/auto-resume loops
if os.getenv("COMFYUI_QUEUE_MANAGER_DISABLE") or os.getenv("DISABLE_AUTO_RESUME"):
    print("[Queue Manager] Disabled via environment variable (COMFYUI_QUEUE_MANAGER_DISABLE or DISABLE_AUTO_RESUME)")
    _initialized = False
    _web_routes_setup = False
else:
    _initialized = initialize_queue_manager()
    try:
        _web_routes_setup = setup_web_routes()
    except Exception as e:
        print(f"[Queue Manager] Could not set up web routes immediately: {e}")
        _web_routes_setup = False

__all__ = [
    "NODE_CLASS_MAPPINGS", 
    "NODE_DISPLAY_NAME_MAPPINGS", 
    "WEB_DIRECTORY"
]
