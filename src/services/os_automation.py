import sys
import subprocess

def open_application(app_name: str) -> str:
    """
    Abre una aplicación de escritorio común en el sistema operativo (ej. 'notepad', 'calc', 'chrome').
    
    Args:
        app_name: El nombre o identificador de la aplicación a abrir.
        
    Returns:
        Un mensaje de estado en texto indicando el resultado de la operación.
    """
    app_lower = app_name.lower().strip()
    platform = sys.platform

    # Mapping common app names to executable commands
    windows_apps = {
        "notepad": "notepad.exe",
        "bloc de notas": "notepad.exe",
        "calculadora": "calc.exe",
        "calculator": "calc.exe",
        "chrome": "chrome",
        "google chrome": "chrome",
        "paint": "mspaint.exe",
        "cmd": "cmd.exe",
        "explorador": "explorer.exe",
        "explorer": "explorer.exe"
    }

    linux_apps = {
        "notepad": "gedit",
        "bloc de notas": "gedit",
        "calculadora": "gnome-calculator",
        "calculator": "gnome-calculator",
        "chrome": "google-chrome",
        "google chrome": "google-chrome",
        "firefox": "firefox",
        "terminal": "x-terminal-emulator"
    }

    try:
        if platform == "win32":
            import os
            # Resolve executable
            cmd = windows_apps.get(app_lower)
            if not cmd:
                cmd = f"{app_lower}.exe" if not app_lower.endswith(".exe") else app_lower

            # Use os.startfile for Windows (robust path resolution for system apps and URLs)
            os.startfile(cmd)
            return f"Aplicación '{app_name}' iniciada correctamente en Windows."
            
        elif platform.startswith("linux"):
            cmd = linux_apps.get(app_lower, app_lower)
            # Use subprocess.Popen for Linux
            subprocess.Popen([cmd], shell=False)
            return f"Aplicación '{app_name}' iniciada correctamente en Linux."
            
        else:
            return f"Plataforma '{platform}' no soportada para automatización local."
            
    except FileNotFoundError:
        return f"Error: No se pudo encontrar el archivo ejecutable para '{app_name}'."
    except Exception as e:
        return f"Error al abrir '{app_name}': {str(e)}"
