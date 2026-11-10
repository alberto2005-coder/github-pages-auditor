import requests

def construir_url_pages(usuario: str, nombre_repo: str, dominio_base: str) -> str:
    user_lower = usuario.lower()
    repo_lower = nombre_repo.lower()

    if repo_lower in [f"{user_lower}.github.io", user_lower]:
        return dominio_base
    return f"{dominio_base}/{nombre_repo}/"

def comprobar_pages(session: requests.Session, url: str) -> bool:
    try:
        response = session.get(url, timeout=5, allow_redirects=True)
        if response.status_code == 200:
            return True
        return False
    except requests.RequestException:
        return False