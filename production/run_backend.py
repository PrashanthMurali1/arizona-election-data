"""Production web process with quiet access logging and structured diagnostics."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.observability import configure_logging

configure_logging('backend')

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('backend.app.main:app', host='0.0.0.0', port=8000, workers=1,
                timeout_graceful_shutdown=30, proxy_headers=True,
                forwarded_allow_ips='*', access_log=False, log_config=None)
