---
name: verificacion-fauna
description: Protocolo de verificación de datos sobre animales para Curiosa Fauna. Usar siempre antes de que una afirmación entre en un guion (short o vídeo largo), al revisar guiones existentes o cuando un comentario cuestione un dato publicado. Adapta fact-check-workflow (instalada) a la divulgación de fauna.
---

# Verificación de datos de fauna

Proceso general en `fact-check-workflow`. Aquí van las reglas propias del canal.

## Regla mínima
Cada afirmación factual necesita **2 fuentes independientes de nivel A o B**.
Si solo hay una, o hay contradicción, se reformula con prudencia («se cree que»,
«algunos estudios apuntan») o **se descarta**. Ante la duda, fuera.

## Jerarquía de fuentes
| Nivel | Fuentes |
|---|---|
| A | Artículos revisados por pares (PNAS, Nature, Science, Journal of Experimental Biology…), Lista Roja de la UICN, organismos científicos (NOAA, USFWS, CSIC, museos de historia natural) |
| B | Smithsonian, Animal Diversity Web (Univ. de Michigan), Encyclopaedia Britannica, National Geographic (artículos firmados), webs de zoos y acuarios acreditados |
| C | Wikipedia y divulgación general: **solo para encontrar fuentes A/B**, nunca como fuente final |
| ✗ | Blogs, listas virales, redes sociales, webs de «datos curiosos», contenido generado por IA |

## Trampas típicas en fauna
- **Cifras infladas** («hasta 100 km/h»): busca el valor medio medido, no el récord anecdótico.
- **Generalizar una especie a todo el grupo** («los pulpos…» cuando el estudio es de una especie). Nombra la especie o matiza.
- **Mitos clásicos** (memoria de 3 s del pez, avestruz que esconde la cabeza): material ideal para el formato `mito`, pero verifica también la refutación.
- **Antropomorfismo**: «está triste», «se venga». Describe conductas, no emociones atribuidas.
- **Datos que cambian**: población y estado de conservación → UICN, con año.

## Cómo registrarlo
En el brief, cada afirmación va en `datos` con sus URLs y `"verificado": true`.
Si reformulas por prudencia, anota el motivo en `"nota"`. Las URLs deben abrir
y decir lo que se afirma: no cites de memoria.
