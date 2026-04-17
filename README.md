# Geoportal Riesgo Agroclimático — Imbabura, Ecuador

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19288559.svg)](https://doi.org/10.5281/zenodo.19288559)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3-38bdf8)](https://tailwindcss.com/)
[![MapLibre](https://img.shields.io/badge/MapLibre-GL%20JS-blue)](https://maplibre.org/)
[![CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey)](https://creativecommons.org/licenses/by/4.0/)

Portal institucional que publica el resultado de la investigación de Maestría (USGP 2026) sobre el riesgo agroclimático
de cultivos andinos en las 42 parroquias de Imbabura, Ecuador, bajo escenarios climáticos CMIP6.

**Autor:** Víctor Hugo Pinto Páez · USGP · [ORCID 0009-0001-5573-8294](https://orcid.org/0009-0001-5573-8294)
**Manuscrito:** sometido a *Natural Hazards* (Springer Nature)

## Stack técnico

| Capa | Tecnología |
|------|-----------|
| Framework | Next.js 14 (App Router) + TypeScript |
| Estilos | Tailwind CSS 3 |
| Visor cartográfico | MapLibre GL JS (consume Feature Services REST) |
| Gráficos | Plotly.js + react-plotly.js |
| Iconografía | Lucide React |
| Datos geoespaciales | ArcGIS Online USGP-EC (3 Feature Services REST públicos) |
| Base de conocimiento IA | Retrieval-Augmented Generation sobre manuscrito (KB pre-indexada) |
| Deploy | GitHub Pages (static export) |

## Páginas

1. **`/`** — Home con hero, estadísticas clave, servicios y hallazgo principal
2. **`/servicios`** — Catálogo completo de 8 servicios del geoportal
3. **`/visor`** — Visor cartográfico interactivo (MapLibre GL JS) con 3 capas y popup + descarga de fichas
4. **`/galeria`** — 60 figuras científicas organizadas por 6 grupos temáticos, con lightbox
5. **`/fichas`** — 42 fichas parroquiales PDF con búsqueda por parroquia/cantón
6. **`/metodologia`** — Pipeline 5 fases, Red Bayesiana DAG, métricas RF, limitaciones
7. **`/resultados`** — Ranking Top 10, gráficos interactivos del IR por cultivo/SSP/horizonte, exposición
8. **`/datos`** — 3 Feature Services REST públicos, GitHub, Zenodo, metadatos ISO 19115, licencia
9. **`/asistente`** — Chatbot RAG sobre manuscrito con base de conocimiento pre-indexada
10. **`/acerca`** — Autor, manuscrito de referencia, cita sugerida, agradecimientos

## Desarrollo

```bash
npm install
npm run dev    # http://localhost:3000
npm run build  # compila a /out
```

## Deploy

Push a `main` → GitHub Actions compila y publica en GitHub Pages.
URL pública: `https://VICTORSIG1985.github.io/geoportal-riesgo-agroclimatico-imbabura/`

## Datos abiertos

3 Feature Services REST públicos en ArcGIS Online USGP-EC:

- **FL_Parroquias_Base_Imbabura_42** — 42 parroquias con `ficha_url`
- **FL_Riesgo_Parroquial_Long_1512** — 1.512 inferencias cultivo × SSP × horizonte
- **FL_Priorizacion_Final_Imbabura_42** — ranking ejecutivo con mensaje de priorización

Código fuente del pipeline científico (22 scripts Python) en [GitHub](https://github.com/VICTORSIG1985/agroclimatic-risk-imbabura) y Zenodo [DOI 10.5281/zenodo.19288559](https://doi.org/10.5281/zenodo.19288559).

## Licencia

Creative Commons Atribución 4.0 Internacional (CC BY 4.0). Cita:

> Pinto Páez, V.H. (2026). *Geoportal Riesgo Agroclimático — Imbabura, Ecuador*.
> Universidad San Gregorio de Portoviejo. DOI: 10.5281/zenodo.19288559
