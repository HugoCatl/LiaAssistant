# Validación de la Fase 2 — recordatorios proactivos

El sistema proactivo usa cooldowns de minutos en uso normal. Para validarlo en
segundos hay un **modo debug** que reduce los tiempos y lanza una sugerencia de
ejemplo al arrancar.

## Activar el modo debug

PowerShell (solo para esta sesión):

```powershell
$env:LIA_PROACTIVE_DEBUG = "1"; venv\Scripts\python.exe main.py
```

O de forma permanente, en `.env`:

```
LIA_PROACTIVE_DEBUG=true
```

En modo debug: cooldown global 8 s, hueco de notas 30 s, foco 30 s, sondeo 1.5 s.

## Qué comprobar

1. **Flujo visual (demo automática):** ~4 s tras arrancar, el orbe se pone en modo
   "recordatorio" y aparece una burbuja junto a él. Pulsa **Sí** → se abre el panel
   con una nota precargada. Pulsa **Ahora no** (o espera 9 s) → se descarta.

2. **Portapapeles:** copia un texto largo (40+ caracteres) desde cualquier app.
   En ~1.5 s el orbe reacciona y la burbuja sugiere guardarlo. Al aceptar, Lia
   crea la nota con tu portapapeles automáticamente.

3. **Inactividad de notas:** mueve el ratón (sigues "presente") pero no captures
   nada durante ~30 s → te sugiere apuntar algo.

4. **Foco prolongado:** mantén la misma ventana en primer plano ~30 s → te sugiere
   anotar en qué avanzas.

5. **No molesta:** mientras el panel está abierto o Lia está respondiendo/grabando,
   no aparecen sugerencias.

## Qué afinar (dímelo y lo ajusto)

- Si es demasiado insistente o demasiado callado → cooldowns/umbrales en
  `ProactiveEngine` (o exponerlos en `.env`).
- Tamaño/posición de la burbuja respecto al orbe.
- Longitud mínima del portapapeles para sugerir (ahora 40).

## Producción

Quita `LIA_PROACTIVE_DEBUG` para volver a los tiempos reales. Para desactivar todo
el sistema proactivo: `PROACTIVE_ENABLED=false`.
