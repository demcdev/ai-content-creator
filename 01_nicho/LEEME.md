# 01_nicho · decisión de nicho

- `Analisis de nicho - octubre 2026.md`: cómo y por qué se eligió el nicho (incluye el cambio de decisión del 12-oct-2026).
- `datos/`: exportaciones JSON de la app (botón **Exportar datos**). Son el respaldo real, porque la app guarda sus datos solo en el navegador.

## La app vive en otro proyecto
`selector-nichos` (React + TypeScript, 50 pruebas) está en `C:\Users\USUARIO\Desktop\DemcDev\Proyectos-dev\selector-nichos\` y tiene su propio repositorio git. La versión anterior (v28) quedó dentro como `legacy/Sistema de nichos/`.

```powershell
cd ..\..\selector-nichos
npm install
npm run dev     # http://localhost:5173
npm test
```
