import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def crear_sesion_http(token: str = None, timeout: int = 10) -> requests.Session:
    session = requests.Session()
    
    retries = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"]
    )
    
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ver-github-pages/0.2.0"
    }
    
    if token:
        headers["Authorization"] = f"token {token}"
        headers["Accept"] = "application/vnd.github.v3+json"

    session.headers.update(headers)
    session.request_timeout = timeout
    return session