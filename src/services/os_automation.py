import os

def open_application(app_name: str) -> str:
    """
    Abre una aplicación de escritorio común en Windows (ej. 'notepad', 'calc', 'chrome').
    
    Args:
        app_name: El nombre o identificador de la aplicación a abrir.
        
    Returns:
        Un mensaje de estado en texto indicando el resultado de la operación.
    """
    app_lower = app_name.lower().strip()

    # Mapping common app names to executable commands in Windows
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

    try:
        # Resolve executable
        cmd = windows_apps.get(app_lower)
        if not cmd:
            cmd = f"{app_lower}.exe" if not app_lower.endswith(".exe") else app_lower

        # Use os.startfile for Windows (robust path resolution for system apps and URLs)
        os.startfile(cmd)
        return f"Aplicación '{app_name}' iniciada correctamente en Windows."
            
    except FileNotFoundError:
        return f"Error: No se pudo encontrar el archivo ejecutable para '{app_name}'."
    except Exception as e:
        return f"Error al abrir '{app_name}': {str(e)}"
