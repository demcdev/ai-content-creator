# Informe auditor-guion · Video 01 Voyager 1 (17-oct-2026)

Veredicto: **PASA** (lint: 0 errores, 2 avisos; primera auditoría, sin sello). No hay bloqueantes. Hay 5 ajustes recomendados.

Archivo de los hallazgos: `Guion.md` (misma carpeta), salvo que se indique otro.

## Hallazgos
1. **Regla 9 / cifras · Guion.md línea 32 (Gancho)** · «una sola foto de móvil ocupa decenas de veces más» no tiene marca [✔] ni [cálculo propio]. Arreglo: marcarlo como [cálculo propio] (p. ej. 3 MB ÷ 69 KB ≈ 43) o quitarlo.
2. **Cifras · Guion.md línea 32 · [✔ 12]** · La cifra de 69 KB es solo 🟡 (fuente secundaria: MuckRock/FOIA 2016; sin página de NASA). Arreglo: en pantalla poner «Fuente: NASA, vía MuckRock (FOIA, 2016)» y decir «unos 69 kilobytes», como ya indica `Verificacion de cifras.md` fila 12.
3. **Cifras · Guion.md línea 75** · «Fue idea del astrónomo Carl Sagan» sin marca [✔ n] en esa frase (la [✔ 6] va en la frase anterior). Arreglo: añadir marca o la fuente de la fila correspondiente.
4. **Regla 9 / duración · Guion.md línea 3 y narración total** · El lint cuenta 1 929 palabras ≈ 12,9 min (objetivo 10–12) y el encabezado dice 1 800. Arreglo: recortar ~130 palabras (candidatos: Acto 1 sobre Titán, líneas 66-70) o actualizar el objetivo y el encabezado.
5. **Composición · Guion.md líneas 144 (Cierre)** · El cierre no invita a suscribirse, a dar like ni a la campanita (aviso del lint, no es política). Arreglo: añadir una frase breve y honesta, sin prometer nada.
6. **Matiz, regla 9 · Guion.md línea 36** · El gancho promete «una frase… Al final del video te digo cuál», pero se resuelve en «Lo que NO sabemos» (línea 127, 9:40), antes del cierre. Arreglo: cambiar a «Más adelante te digo cuál». Lo demás que promete el gancho y la lista de «cinco cosas» (línea 47) sí se entrega.

## Comprobado sin problemas
- Sección «Lo que no sabemos» presente, con comprobado/probable/sin fecha (líneas 124-135).
- Los 30 [✔] tienen fila en `Verificacion de cifras.md`; solo la 12 no es ✅. La 14 («Big Bang» en Voyager 1) está marcada «comprobar el día de publicar».
- Cálculos propios correctos: 17 km/s × 86 400 s ≈ 1,47 M km; 3 MB a 160 bit/s ≈ 42 h; 2 × 23 h.
- Sin imágenes de IA como reales (reglas 4 y 19): las imágenes son NASA/JPL y los esquemas son propios; la voz IA está declarada en el encabezado. Sin bienes regulados, menores ni temas sensibles (8, 12, 13, 14). Sin petición de clics en anuncios ni promesas de dinero (22).
- Plagio (regla 5): estructura y guion propios. Esto no se puede verificar contra otros canales desde el archivo; no verificable.
- Títulos y miniatura prometen lo que el video entrega.

## No verificable en esta etapa
- Licencias de cada imagen (todas en ☐ en la lista de material, líneas 151-159 del guion): se comprueban en modo final.
- Cifras dependientes de fecha (distancia, hito del 18-nov, estado de instrumentos): comprobar el día de grabar.
