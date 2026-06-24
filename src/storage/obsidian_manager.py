import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from config import settings

# Índice semántico global (lazy-loaded en search_notes_semantic)
_semantic_index = None
_semantic_available = True  # Flag para saber si fastembed está disponible

def sanitize_filename(title: str) -> str:
    """
    Limpia el título de la nota eliminando caracteres no válidos para nombres de archivo en Windows.
    """
    sanitized = re.sub(r'[\\/*?:"<>|]', "", title)
    return sanitized.strip()

def normalize_tags(tags) -> List[str]:
    """
    Normaliza etiquetas para que sean VÁLIDAS en Obsidian, soportando entidades.

    - Quita '#' y espacios sobrantes.
    - Sustituye los espacios internos por '-' (las tags de Obsidian no admiten
      espacios): 'persona/Juan Pérez' -> 'persona/Juan-Pérez'.
    - Permite jerarquía 'tipo/Valor' (ej. proyecto/Lia, persona/Ana).
    - Elimina caracteres no válidos y duplicados (sin distinguir mayúsculas).
    """
    out, seen = [], set()
    for t in tags or []:
        if not t or not str(t).strip():
            continue
        raw = str(t).strip().replace("#", "")
        segments = [re.sub(r"\s+", "-", s.strip()) for s in raw.split("/") if s.strip()]
        norm = "/".join(segments)
        norm = re.sub(r"[^\w\-/]", "", norm, flags=re.UNICODE)  # letras (con acentos), dígitos, _-/
        norm = norm.strip("-/")
        if norm and norm.lower() not in seen:
            seen.add(norm.lower())
            out.append(norm)
    return out

def get_vault_path() -> Path:
    """
    Retorna la ruta absoluta del vault de Obsidian configurado y se asegura de que exista.
    """
    vault_path = settings.obsidian_vault_path
    if not vault_path:
        raise ValueError("OBSIDIAN_VAULT_PATH no está configurado en el archivo .env")
    path = Path(vault_path).resolve()
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    return path

def create_note(title: str, content: str, tags: Optional[List[str]] = None) -> str:
    """
    Crea una nueva nota en formato Markdown (.md) dentro del Vault de Obsidian.
    Si la nota ya existe, se genera un archivo nuevo añadiendo un sufijo de marca de tiempo (timestamp)
    para evitar sobrescribir las notas existentes.

    Args:
        title: El título o nombre de la nota.
        content: El contenido textual de la nota.
        tags: Una lista opcional de etiquetas para clasificar la nota.

    Returns:
        Un mensaje de confirmación detallando si se creó con éxito y el nombre del archivo.
    """
    try:
        vault = get_vault_path()
        clean_title = sanitize_filename(title)
        if not clean_title:
            clean_title = "Nota_Sin_Titulo"

        filename = f"{clean_title}.md"
        note_path = vault / filename

        # Seguridad: evitar escape de directorio
        if not note_path.resolve().is_relative_to(vault.resolve()):
            return "Error: Intento de escape del directorio del Vault detectado."

        # Evitar duplicados realizando una búsqueda insensible a mayúsculas/minúsculas
        existing_file = None
        for p in vault.iterdir():
            if p.is_file() and p.suffix.lower() == '.md':
                if p.stem.lower() == clean_title.lower():
                    existing_file = p.stem
                    break

        if existing_file:
            return f"Error: La nota '{existing_file}' ya existe en Obsidian. Para modificarla o sobrescribirla usa la herramienta 'write_note', o para añadir información al final usa 'append_to_note'."

        # Crear frontmatter de tipo YAML compatible con Obsidian
        tag_lines = ""
        clean_tags = normalize_tags(tags)
        if clean_tags:
            tag_lines = "\ntags:\n" + "\n".join(f"  - {ct}" for ct in clean_tags)

        frontmatter = f"---\ndate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{tag_lines}\n---\n\n"
        full_content = frontmatter + content

        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(full_content)

        return f"Nota creada exitosamente en Obsidian: '{filename}'"
    except Exception as e:
        return f"Error al crear la nota en Obsidian: {str(e)}"

def read_note(title: str) -> str:
    """
    Lee y retorna el contenido de una nota existente en el Vault de Obsidian.

    Args:
        title: El nombre o título de la nota a leer (se busca con y sin extensión .md).

    Returns:
        El contenido completo de la nota o un mensaje de error si no se encuentra.
    """
    try:
        vault = get_vault_path()
        clean_title = sanitize_filename(title)
        
        note_path = vault / f"{clean_title}.md"
        
        # Búsqueda insensible a mayúsculas/minúsculas si no existe de forma directa
        if not note_path.exists():
            found = False
            for p in vault.iterdir():
                if p.is_file() and p.suffix.lower() == '.md':
                    if p.stem.lower() == clean_title.lower():
                        note_path = p
                        found = True
                        break
            if not found:
                return f"Error: No se encontró la nota '{title}' en el Vault."

        # Seguridad: evitar escape de directorio
        if not note_path.resolve().is_relative_to(vault.resolve()):
            return "Error: Acceso no autorizado fuera del Vault."

        with open(note_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error al leer la nota en Obsidian: {str(e)}"

def search_notes(query: str) -> List[str]:
    """
    Busca palabras clave dentro de todos los títulos y del contenido de las notas (.md) del Vault de Obsidian.

    Args:
        query: El término o frase de búsqueda.

    Returns:
        Una lista de resultados formateados con el título de la nota y un fragmento relevante de la coincidencia.
    """
    try:
        vault = get_vault_path()
        results = []
        query_lower = query.lower()

        # Recorrer recursivamente excluyendo directorios ocultos (como .obsidian)
        for root, dirs, files in os.walk(vault):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if not file.endswith('.md') or file.startswith('.'):
                    continue
                    
                file_path = Path(root) / file
                
                # Seguridad: evitar procesamiento fuera del vault
                if not file_path.resolve().is_relative_to(vault.resolve()):
                    continue
                    
                relative_title = file_path.relative_to(vault).as_posix()
                note_title = relative_title[:-3]  # Quitar extensión .md

                # Comprobar coincidencia en el título
                title_match = query_lower in note_title.lower()
                content_match = False
                snippet = ""

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if query_lower in content.lower():
                            content_match = True
                            # Extraer un fragmento
                            idx = content.lower().find(query_lower)
                            start = max(0, idx - 40)
                            end = min(len(content), idx + len(query) + 40)
                            snippet = content[start:end].replace('\n', ' ')
                            snippet = f"...{snippet}..."
                except Exception:
                    continue

                if title_match or content_match:
                    if title_match and not snippet:
                        snippet = "(Coincidencia en el título)"
                    results.append(f"Nota: '{note_title}' - {snippet}")

        if not results:
            return ["No se encontraron notas en Obsidian que coincidan con la búsqueda."]
        return results
    except Exception as e:
        return [f"Error al realizar la búsqueda en Obsidian: {str(e)}"]

def search_notes_semantic(query: str) -> List[str]:
    """
    Busca notas por SIGNIFICADO (no por palabra exacta) en la memoria del usuario.
    Úsala cuando el usuario pregunte por temas, conceptos o ideas de forma abierta
    (ej: "qué sé sobre productividad", "ideas relacionadas con mi proyecto"),
    ya que encuentra notas relevantes aunque no contengan las palabras exactas.

    Args:
        query: La consulta o tema a buscar conceptualmente.

    Returns:
        Una lista de notas relevantes ordenadas por cercanía semántica, con un
        fragmento de cada una.
    """
    global _semantic_index, _semantic_available

    # Si fastembed no está disponible, recurrimos a la búsqueda por palabra clave
    if not _semantic_available:
        return search_notes(query)

    try:
        if _semantic_index is None:
            from src.services.semantic_index import SemanticIndex, FastEmbedEmbedder
            vault = get_vault_path()
            _semantic_index = SemanticIndex(vault, FastEmbedEmbedder())

        results = _semantic_index.search(query, top_k=5)
        if not results:
            return ["No se encontraron notas relevantes en la memoria."]

        formatted = []
        for r in results:
            # Umbral calibrado para paraphrase-multilingual-MiniLM (coseno ~0.3+ ya es relevante)
            if r["score"] < 0.30:
                continue
            formatted.append(f"Nota: '{r['title']}' (relevancia {r['score']:.0%}) - {r['snippet']}")

        if not formatted:
            return ["No se encontraron notas suficientemente relevantes en la memoria."]
        return formatted

    except ImportError:
        # fastembed no instalado: desactivar para futuras llamadas y usar keyword
        _semantic_available = False
        return search_notes(query)
    except Exception as e:
        # Cualquier otro fallo: degradar a búsqueda por palabra clave
        return search_notes(query)


def write_note(title: str, content: str, tags: Optional[List[str]] = None) -> str:
    """
    Crea una nueva nota o sobrescribe por completo el contenido de una nota existente en Obsidian.
    Úsala para actualizar, editar o corregir la información de una nota ya existente.

    Args:
        title: El título o nombre de la nota a escribir/sobrescribir.
        content: El nuevo contenido completo que tendrá la nota.
        tags: Una lista opcional de etiquetas para clasificar la nota.

    Returns:
        Un mensaje indicando el resultado de la escritura.
    """
    try:
        vault = get_vault_path()
        clean_title = sanitize_filename(title)
        if not clean_title:
            clean_title = "Nota_Sin_Titulo"

        filename = f"{clean_title}.md"
        note_path = vault / filename

        # Búsqueda insensible a mayúsculas/minúsculas para encontrar archivo existente a sobrescribir
        if not note_path.exists():
            for p in vault.iterdir():
                if p.is_file() and p.suffix.lower() == '.md':
                    if p.stem.lower() == clean_title.lower():
                        note_path = p
                        filename = p.name
                        break

        # Seguridad: evitar escape de directorio
        if not note_path.resolve().is_relative_to(vault.resolve()):
            return "Error: Intento de escape del directorio del Vault detectado."

        # Crear frontmatter de tipo YAML compatible con Obsidian
        tag_lines = ""
        clean_tags = normalize_tags(tags)
        if clean_tags:
            tag_lines = "\ntags:\n" + "\n".join(f"  - {ct}" for ct in clean_tags)

        frontmatter = f"---\ndate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{tag_lines}\n---\n\n"
        full_content = frontmatter + content

        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(full_content)

        return f"Nota '{filename}' escrita/actualizada con éxito en Obsidian."
    except Exception as e:
        return f"Error al escribir la nota en Obsidian: {str(e)}"

def append_to_note(title: str, content: str) -> str:
    """
    Añade contenido adicional al final de una nota existente en Obsidian.
    Si la nota no existe, la crea automáticamente.

    Args:
        title: El título o nombre de la nota a la que se le añadirá contenido.
        content: El texto o contenido que se va a añadir al final.

    Returns:
        Un mensaje indicando el resultado de la operación.
    """
    try:
        vault = get_vault_path()
        clean_title = sanitize_filename(title)
        if not clean_title:
            return "Error: Título de nota no válido."

        note_path = vault / f"{clean_title}.md"

        # Búsqueda insensible a mayúsculas/minúsculas si no existe de forma directa
        if not note_path.exists():
            for p in vault.iterdir():
                if p.is_file() and p.suffix.lower() == '.md':
                    if p.stem.lower() == clean_title.lower():
                        note_path = p
                        break

        # Seguridad: evitar escape de directorio
        if not note_path.resolve().is_relative_to(vault.resolve()):
            return "Error: Intento de escape del directorio del Vault detectado."

        # Si no existe la nota, la creamos desde cero
        if not note_path.exists():
            return create_note(title, content)

        # Leer contenido actual para evitar duplicaciones
        with open(note_path, 'r', encoding='utf-8') as f:
            existing_content = f.read()

        # Normalizar espacios y saltos de línea para la comparación
        norm_existing = " ".join(existing_content.lower().split())
        norm_new = " ".join(content.lower().split())

        # Si el texto ya está presente en el archivo, no duplicarlo
        if norm_new in norm_existing:
            return f"Información ya presente en la nota '{note_path.name}'. No se añadieron duplicados."

        # Añadimos al final de la nota
        with open(note_path, 'a', encoding='utf-8') as f:
            f.write(f"\n\n{content}")

        return f"Contenido añadido con éxito al final de la nota '{note_path.name}'."
    except Exception as e:
        return f"Error al añadir contenido a la nota en Obsidian: {str(e)}"

