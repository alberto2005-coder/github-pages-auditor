import os
import re
import requests
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# Cargar las variables definidas en el archivo .env
load_dotenv()

# Obtener variables con valores por defecto de respaldo
USUARIO_GITHUB = os.getenv("USUARIO_GITHUB", "alberto2005-coder")
DOMINIO_WEB = os.getenv("DOMINIO_WEB", "https://albertoortiz.is-a.dev")
ARCHIVO_SALIDA = os.getenv("ARCHIVO_SALIDA", "paginas_github.txt")


def obtener_todos_los_repositorios_web(username):
    repos = []
    page = 1
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    while True:
        url = f"https://github.com/{username}?page={page}&tab=repositories"
        res = requests.get(url, headers=headers)
        
        if res.status_code != 200:
            break

        html = res.text
        bloques_repo = re.findall(r'href="/' + re.escape(username) + r'/([^"/]+)"\s+itemprop="name codeRepository"', html)

        if not bloques_repo:
            break

        for nombre in bloques_repo:
            repos.append(nombre)

        page += 1

    return list(dict.fromkeys(repos))


def analizar_detalles_repo(username, nombre_repo):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # 1. Releases (feed Atom)
    atom_url = f"https://github.com/{username}/{nombre_repo}/releases.atom"
    try:
        res_atom = requests.get(atom_url, headers=headers, timeout=5)
        has_releases = (res_atom.status_code == 200) and ("<entry>" in res_atom.text)
    except Exception:
        has_releases = False

    # 2. Análisis del repositorio público
    repo_url = f"https://github.com/{username}/{nombre_repo}"
    has_readme = False
    has_license = False
    has_gitignore = False
    has_description = False
    is_fork = False
    is_archived = False

    try:
        res_repo = requests.get(repo_url, headers=headers, timeout=5)
        if res_repo.status_code == 200:
            html = res_repo.text
            
            if 'id="readme"' in html or 'README.md' in html or 'readme-icon' in html:
                has_readme = True
                
            if 'License' in html or 'license-icon' in html or 'LICENSE' in html:
                has_license = True

            if '.gitignore' in html:
                has_gitignore = True

            if 'f6 link-gray-dark' in html or 'repository-content' in html:
                if 'No description, website, or topics provided.' not in html:
                    has_description = True

            if 'forked from' in html:
                is_fork = True
            if 'This repository has been archived' in html or 'Label--warning' in html:
                is_archived = True

    except Exception:
        pass

    return (nombre_repo, has_releases, has_readme, has_license, 
            has_gitignore, has_description, is_fork, is_archived)


def analizar_repositorios(username, dominio_personalizado, archivo_salida):
    print(f"⚙️ Configuración cargada desde .env (Usuario: {username})")
    print("🔍 Obteniendo repositorios desde la web pública...")
    
    repos = obtener_todos_los_repositorios_web(username)

    if not repos:
        print("❌ No se pudieron obtener repositorios o el usuario no existe.")
        return

    print(f"📦 Se encontraron {len(repos)} repositorios.")
    print("⚡ Auditoría en paralelo (Pages, Releases, README, Licencia, .gitignore, About, Forks, Archivados)...")

    con_pages = []
    con_releases = []
    sin_nada = []
    sin_readme = []
    sin_licencia = []
    sin_gitignore = []
    sin_descripcion = []
    es_fork_list = []
    archivados_list = []

    with ThreadPoolExecutor(max_workers=15) as executor:
        resultados = executor.map(lambda r: analizar_detalles_repo(username, r), repos)

    for (nombre_repo, has_releases, has_readme, has_license, 
         has_gitignore, has_description, is_fork, is_archived) in resultados:
        
        es_principal = nombre_repo.lower() in [f"{username.lower()}.github.io", username.lower()]
        url_pages = dominio_personalizado if es_principal else f"{dominio_personalizado}/{nombre_repo}/"
        
        has_pages = False
        if es_principal:
            has_pages = True
            con_pages.append(f"- {nombre_repo:<32} -> {url_pages}")
        else:
            try:
                r_pages = requests.head(url_pages, timeout=3)
                if r_pages.status_code in [200, 301, 302]:
                    has_pages = True
                    con_pages.append(f"- {nombre_repo:<32} -> {url_pages}")
            except Exception:
                pass

        if has_releases:
            con_releases.append(f"- {nombre_repo}")

        if not has_pages and not has_releases:
            sin_nada.append(f"- {nombre_repo}")

        if not has_readme:
            sin_readme.append(f"- {nombre_repo}")
        
        if not has_license:
            sin_licencia.append(f"- {nombre_repo}")

        if not has_gitignore:
            sin_gitignore.append(f"- {nombre_repo}")

        if not has_description:
            sin_descripcion.append(f"- {nombre_repo}")

        if is_fork:
            es_fork_list.append(f"- {nombre_repo}")

        if is_archived:
            archivados_list.append(f"- {nombre_repo}")

    lineas = [
        f"=== ENLACES DE GITHUB PAGES PARA: {username} ===",
        f"Dominio base: {dominio_personalizado}\n"
    ]
    lineas.extend(con_pages if con_pages else ["No se encontraron repositorios con GitHub Pages."])

    lineas.append("\n=== REPOSITORIOS CON RELEASES ===")
    lineas.extend(con_releases if con_releases else ["No hay repositorios con releases publicadas."])

    lineas.append("\n=== REPOSITORIOS SIN RELEASES NI GITHUB PAGES ===")
    lineas.extend(sin_nada if sin_nada else ["Todos los repositorios tienen al menos web o releases."])

    lineas.append("\n=== REPOSITORIOS SIN README ===")
    lineas.extend(sin_readme if sin_readme else ["Todos los repositorios tienen archivo README."])

    lineas.append("\n=== REPOSITORIOS SIN LICENCIA ===")
    lineas.extend(sin_licencia if sin_licencia else ["Todos los repositorios tienen una licencia adjunta."])

    lineas.append("\n=== REPOSITORIOS SIN .GITIGNORE ===")
    lineas.extend(sin_gitignore if sin_gitignore else ["Todos los repositorios incluyen archivo .gitignore."])

    lineas.append("\n=== REPOSITORIOS SIN DESCRIPCIÓN (ABOUT) ===")
    lineas.extend(sin_descripcion if sin_descripcion else ["Todos los repositorios tienen descripción."])

    lineas.append("\n=== REPOSITORIOS QUE SON FORKS ===")
    lineas.extend(es_fork_list if es_fork_list else ["Ningún repositorio es un fork."])

    lineas.append("\n=== REPOSITORIOS ARCHIVADOS ===")
    lineas.extend(archivados_list if archivados_list else ["No hay repositorios archivados."])

    resultado_texto = "\n".join(lineas)
    print("\n" + resultado_texto)

    with open(archivo_salida, "w", encoding="utf-8") as f:
        f.write(resultado_texto + "\n")

    print(f"\n✅ Guardado correctamente en '{archivo_salida}'")


if __name__ == "__main__":
    analizar_repositorios(USUARIO_GITHUB, DOMINIO_WEB, ARCHIVO_SALIDA)