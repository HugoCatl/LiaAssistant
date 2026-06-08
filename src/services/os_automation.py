import os
import subprocess

def open_application(app_name: str) -> str:
    """
    Abre una aplicación de escritorio común en Windows (ej. 'notepad', 'calc', 'chrome', 'discord', 'teams').
    
    Args:
        app_name: El nombre o identificador de la aplicación a abrir.
        
    Returns:
        Un mensaje de estado en texto indicando el resultado de la operación.
    """
    app_lower = app_name.lower().strip()
    local_app_data = os.environ.get("LOCALAPPDATA", "")

    # Mapeo de atajos específicos para aplicaciones complejas / personalizadas
    if app_lower in ("paint", "paint 3d", "paint3d", "abrir paint 3d", "abrir paint"):
        try:
            # Paint 3D utiliza el protocolo UWP 'ms-paint:'
            os.startfile("ms-paint:")
            return "Aplicación 'Paint 3D' iniciada usando el protocolo ms-paint:."
        except Exception:
            # Fallback al mspaint clásico si falla ms-paint:
            try:
                os.startfile("mspaint.exe")
                return "Paint 3D no disponible. Se inició Paint clásico como alternativa."
            except Exception as e:
                return f"Error al abrir Paint: {str(e)}"

    elif app_lower in ("discord", "abrir discord"):
        discord_updater = os.path.join(local_app_data, "Discord", "Update.exe")
        if os.path.exists(discord_updater):
            try:
                subprocess.Popen([discord_updater, "--processStart", "Discord.exe"])
                return "Discord iniciado desde el directorio local."
            except Exception as e:
                return f"Error al iniciar Discord: {str(e)}"
        else:
            try:
                os.startfile("discord")
                return "Discord invocado vía atajo de Windows."
            except Exception as e:
                return f"No se encontró Discord en el equipo: {str(e)}"

    elif app_lower in ("teams", "microsoft teams", "abrir teams"):
        try:
            # El Teams moderno utiliza el protocolo UWP 'ms-teams:'
            os.startfile("ms-teams:")
            return "Microsoft Teams (UWP) iniciado."
        except Exception:
            # Fallback a Teams clásico en LocalAppData
            teams_path = os.path.join(local_app_data, "Microsoft", "Teams", "current", "Teams.exe")
            if os.path.exists(teams_path):
                try:
                    subprocess.Popen([teams_path])
                    return "Microsoft Teams clásico iniciado desde el directorio local."
                except Exception as e:
                    return f"Error al abrir Teams clásico: {str(e)}"
            else:
                return "No se pudo iniciar Microsoft Teams en Windows."

    # Mapeo de aplicaciones de sistema estándar
    windows_apps = {
        "notepad": "notepad.exe",
        "bloc de notas": "notepad.exe",
        "calculadora": "calc.exe",
        "calculator": "calc.exe",
        "chrome": "chrome",
        "google chrome": "chrome",
        "cmd": "cmd.exe",
        "explorador": "explorer.exe",
        "explorer": "explorer.exe"
    }

    try:
        # Resolver ejecutable estándar
        cmd = windows_apps.get(app_lower)
        if not cmd:
            cmd = f"{app_lower}.exe" if not app_lower.endswith(".exe") else app_lower

        # Lanzamiento
        os.startfile(cmd)
        return f"Aplicación '{app_name}' iniciada correctamente en Windows."
            
    except FileNotFoundError:
        return f"Error: No se pudo encontrar el archivo ejecutable para '{app_name}'."
    except Exception as e:
        return f"Error al abrir '{app_name}': {str(e)}"
