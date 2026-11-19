# Comparación de experimentos y corridas

Generado por `scripts/comparacion.py` desde `metrics/<exp>/evaluacion.json` y `models/<exp>/semilla-N/corrida.json`.
Una **corrida** es una semilla de un experimento (un run de MLflow). Examen oficial: 12 episodios fijos en la
condición que decide la aprobación (sin perturbación), 12 más con un empujón (informativo) y 12 por cada examen
anterior (`aprobar.sin_olvidar`). Se conservan todos los intentos,
también los que no mejoraron. Resultados por episodio de cada campeón: `data/<exp>/trayectorias.jsonl`;
tabla por semilla en CSV: `docs/evaluaciones/<exp>-semillas.csv`.

## Resumen

| Exp | Título | Corridas | Campeón | Estado |
|---|---|---|---|---|
| 1 | De pie | 1 | semilla 0 | aprobado |
| 2 | Caminar | 2 | semilla 1 | aprobado |
| 3 | Caminar bien | 2 | semilla 1 | aprobado |
| 4 | Caminar en terreno difícil | 1 | semilla 0 | aprobado |
| 5 | Girar en la esquina | 21 | semilla 25 | aprobado |
| 6 | Caminar en curva | 5 | semilla 5 | aprobado |
| 7 | Recorrido | 3 | semilla 3 | aprobado |
| 8 | Llegar a las balizas | 4 | semilla 1 | aprobado |
| 7 (terreno, descartado) | Dominio en terreno duro | 10 | semilla 6 | no aprobado |

## Todas las corridas

| Exp | Semilla | Origen | Pasos | Tiempo | Examen propio | Con empujón (informativo) | Exámenes anteriores | Decisión | Run MLflow |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 0 | desde cero | 1,503,232 | 12 min | 83 % | 83 % | — | **campeón · aprobado** | `523bb570` |
| 2 | 0 | campeón de exp-101 | 1,555,648 | 21 min | 58 % | 58 % | — | rechazado: no llega al mínimo | `0441976e` |
| 2 | 1 | campeón de exp-101 | 1,555,600 | 12 min | 100 % | 83 % | — | **campeón · aprobado** | `91f42b85` |
| 3 | 0 | campeón de exp-102 | 6,000,640 | 54 min | 75 % | 42 % | — | rechazado: no llega al mínimo | `c848ab0e` |
| 3 | 1 | campeón de exp-102 | 9,003,008 | 74 min | 100 % | 50 % | — | **campeón · aprobado** | `5288517f` |
| 4 | 0 | campeón de exp-103 | 5,001,216 | 48 min | 75 % | 67 % | — | **campeón · aprobado** | `b16c1655` |
| 5 | 6 | campeón de exp-104 | 6,000,640 | 44 min | 50 % | 42 % | 101 50 % · 103 83 % · 104 58 % | rechazado: no llega al mínimo; olvida exp-101, exp-104 | `43d3901a` |
| 5 | 7 | campeón de exp-104 | 9,000,960 | 62 min | 100 % | 58 % | 101 0 % · 103 100 % · 104 0 % | rechazado: olvida exp-101, exp-104 | `526cb652` |
| 5 | 8 | continúa semilla 7 | 2,041,680 | 16 min | 42 % | 42 % | 101 75 % · 103 83 % · 104 58 % | rechazado: no llega al mínimo; olvida exp-101, exp-104 | `ba977abd` |
| 5 | 9 | continúa semilla 7 | 6,000,640 | 38 min | 92 % | 42 % | 101 50 % · 103 100 % · 104 75 % | rechazado: olvida exp-101 | `833c1b13` |
| 5 | 10 | continúa semilla 9 | 4,003,840 | 25 min | 92 % | 67 % | 101 58 % · 103 100 % · 104 92 % | rechazado: olvida exp-101 | `271d756a` |
| 5 | 11 | continúa semilla 10 | 4,003,840 | 25 min | 92 % | 58 % | 101 67 % · 103 100 % · 104 42 % | rechazado: olvida exp-101, exp-104 | `5b6c6b32` |
| 5 | 12 | continúa semilla 10 | 6,000,640 | 38 min | 58 % | 42 % | 101 58 % · 103 75 % · 104 42 % | rechazado: no llega al mínimo; olvida exp-101, exp-103, exp-104 | `fbd343d4` |
| 5 | 13 | continúa semilla 10 | 4,003,840 | 25 min | 0 % | 8 % | 101 75 % · 103 100 % · 104 42 % | rechazado: no llega al mínimo; olvida exp-101, exp-104 | `486cbf0b` |
| 5 | 14 | continúa semilla 10 | 4,003,840 | 25 min | 25 % | 50 % | 101 50 % · 103 100 % · 104 25 % | rechazado: no llega al mínimo; olvida exp-101, exp-104 | `d6bb53a9` |
| 5 | 15 | continúa semilla 9 | 3,002,368 | 34 min | 100 % | 50 % | 101 83 % · 103 100 % · 104 42 % | rechazado: olvida exp-104 | `50cbaf76` |
| 5 | 16 | continúa semilla 9 | 3,002,368 | 34 min | 17 % | 33 % | 101 92 % · 103 17 % · 104 0 % | rechazado: no llega al mínimo; olvida exp-103, exp-104 | `53ba1396` |
| 5 | 17 | continúa semilla 9 | 3,502,080 | 38 min | 0 % | 42 % | 101 50 % · 103 100 % · 104 42 % | rechazado: no llega al mínimo; olvida exp-101, exp-104 | `d379807f` |
| 5 | 18 | continúa semilla 15 | 401,408 | 20 min | 83 % | 42 % | 101 58 % · 103 100 % · 104 83 % | rechazado: olvida exp-101 | `7de17423` |
| 5 | 19 | continúa semilla 15 | 401,408 | 17 min | 25 % | 17 % | 101 67 % · 103 100 % · 104 17 % | rechazado: no llega al mínimo; olvida exp-101, exp-104 | `cfa273a4` |
| 5 | 20 | continúa semilla 15 | 401,408 | 20 min | 100 % | 50 % | 101 58 % · 103 100 % · 104 58 % | rechazado: olvida exp-101, exp-104 | `6512c8cf` |
| 5 | 21 | continúa semilla 15 | 401,408 | 20 min | 92 % | 42 % | 101 92 % · 103 100 % · 104 67 % | rechazado: olvida exp-104 | `aaca73bf` |
| 5 | 22 | continúa semilla 15 | 401,408 | 20 min | 100 % | 42 % | 101 92 % · 103 100 % · 104 50 % | rechazado: olvida exp-104 | `e70ea5a5` |
| 5 | 23 | continúa semilla 15 | 401,408 | 22 min | 100 % | 33 % | 101 92 % · 103 100 % · 104 58 % | rechazado: olvida exp-104 | `98fc41c9` |
| 5 | 24 | continúa semilla 15 | 401,408 | 32 min | 100 % | 42 % | 101 92 % · 103 100 % · 104 58 % | rechazado: olvida exp-104 | `a27102a0` |
| 5 | 25 | continúa semilla 15 | 401,408 | 32 min | 100 % | 50 % | 101 92 % · 103 100 % · 104 75 % | **campeón · aprobado** | `88c1d9da` |
| 5 | 26 | continúa semilla 15 | 401,408 | 32 min | 92 % | 33 % | 101 92 % · 103 100 % · 104 83 % | aprueba (no elegido) | `dad15f78` |
| 6 | 1 | campeón de exp-105 | 5,001,216 | 51 min | 83 % | 8 % | 101 92 % · 103 100 % · 104 42 % · 105 100 % | rechazado: olvida exp-104 | `0fd785be` |
| 6 | 2 | campeón de exp-105 | 5,001,216 | 47 min | 42 % | 0 % | 101 58 % · 103 0 % · 104 42 % · 105 50 % | rechazado: no llega al mínimo; olvida exp-101, exp-103, exp-104, exp-105 | `e81ef782` |
| 6 | 3 | continúa semilla 1 | 401,408 | 44 min | 83 % | 8 % | 101 67 % · 103 100 % · 104 67 % · 105 100 % | rechazado: olvida exp-101, exp-104 | `3c459d4d` |
| 6 | 4 | campeón de exp-105 | 401,408 | 39 min | 92 % | 17 % | 101 75 % · 103 100 % · 104 92 % · 105 100 % | rechazado: olvida exp-101 | `beade7e6` |
| 6 | 5 | continúa semilla 4 | 401,408 | 42 min | 75 % | 8 % | 101 83 % · 103 100 % · 104 83 % · 105 100 % | **campeón · aprobado** | `b8780d38` |
| 7 | 1 | campeón de exp-106 | 3,002,368 | 23 min | 50 % | 33 % | 101 75 % · 103 0 % · 104 0 % · 105 58 % · 106 0 % | rechazado: no llega al mínimo; olvida exp-101, exp-103, exp-104, exp-105, exp-106 | `4af5039a` |
| 7 | 2 | campeón de exp-106 | 401,408 | 58 min | 100 % | 42 % | 101 83 % · 103 100 % · 104 58 % · 105 100 % · 106 100 % | rechazado: olvida exp-104 | `b17082c6` |
| 7 | 3 | campeón de exp-106 | 401,408 | 57 min | 100 % | 50 % | 101 92 % · 103 100 % · 104 75 % · 105 100 % · 106 100 % | **campeón · aprobado** | `d88c5a3d` |
| 8 | 1 | campeón de exp-107a | 303,104 | 4 min | 83 % | 58 % | 101 92 % · 103 100 % · 104 75 % · 105 100 % · 106 100 % · 107a 100 % | **campeón · aprobado** | `a6328691` |
| 8 | 2 | continúa semilla 1 | 1,003,520 | 9 min | 50 % | 33 % | 101 75 % · 103 100 % · 104 8 % · 105 92 % · 106 100 % · 107a 75 % | rechazado: no llega al mínimo; olvida exp-101, exp-104 | `87a38abf` |
| 8 | 3 | continúa semilla 1 | 1,003,520 | 11 min | 75 % | 50 % | 101 75 % · 103 100 % · 104 33 % · 105 92 % · 106 75 % · 107a 75 % | rechazado: olvida exp-101, exp-104 | `175793b0` |
| 8 | 4 | continúa semilla 1 | 1,003,520 | 8 min | 58 % | 42 % | 101 83 % · 103 100 % · 104 0 % · 105 100 % · 106 100 % · 107a 92 % | rechazado: no llega al mínimo; olvida exp-104 | `98a73a9a` |
| 7 (terreno, descartado) | 1 | campeón de exp-106 | 6,000,640 | 47 min | 0 % | 17 % | 101 75 % · 103 17 % · 104 0 % · 105 17 % · 106 8 % | rechazado: no llega al mínimo; olvida exp-101, exp-103, exp-104, exp-105, exp-106 | `807e24cc` |
| 7 (terreno, descartado) | 2 | campeón de exp-106 | 3,002,368 | 21 min | 17 % | 8 % | 101 83 % · 103 100 % · 104 17 % · 105 83 % · 106 83 % | rechazado: no llega al mínimo; olvida exp-104 | `51a01ac5` |
| 7 (terreno, descartado) | 3 | continúa semilla 2 | 6,000,640 | 42 min | 17 % | 8 % | 101 92 % · 103 8 % · 104 0 % · 105 25 % · 106 33 % | rechazado: no llega al mínimo; olvida exp-103, exp-104, exp-105, exp-106 | `18726350` |
| 7 (terreno, descartado) | 4 | campeón de exp-106 | 6,000,640 | 50 min | 17 % | 17 % | 101 83 % · 103 100 % · 104 50 % · 105 92 % · 106 8 % | rechazado: no llega al mínimo; olvida exp-104, exp-106 | `030a101a` |
| 7 (terreno, descartado) | 5 | continúa semilla 4 | 6,000,640 | 42 min | 33 % | 33 % | 101 58 % · 103 100 % · 104 75 % · 105 75 % · 106 0 % | rechazado: no llega al mínimo; olvida exp-101, exp-105, exp-106 | `92bb7e0e` |
| 7 (terreno, descartado) | 6 | continúa semilla 5 | 6,000,640 | 42 min | 75 % | 67 % | 101 83 % · 103 100 % · 104 67 % · 105 100 % · 106 25 % | campeón (no aprueba): olvida exp-104, exp-106 | `5b4ad57c` |
| 7 (terreno, descartado) | 7 | continúa semilla 6 | 6,000,640 | 44 min | 67 % | 58 % | 101 83 % · 103 100 % · 104 50 % · 105 100 % · 106 42 % | rechazado: no llega al mínimo; olvida exp-104, exp-106 | `e1086303` |
| 7 (terreno, descartado) | 8 | campeón de exp-106 | 401,408 | 47 min | 42 % | 42 % | 101 92 % · 103 100 % · 104 83 % · 105 92 % · 106 100 % | rechazado: no llega al mínimo | `b9cbe585` |
| 7 (terreno, descartado) | 9 | continúa semilla 8 | 2,002,944 | 15 min | 50 % | 33 % | 101 75 % · 103 100 % · 104 83 % · 105 92 % · 106 33 % | rechazado: no llega al mínimo; olvida exp-101, exp-106 | `31524ad3` |
| 7 (terreno, descartado) | 10 | campeón de exp-106 | 401,408 | 80 min | 50 % | 50 % | 101 75 % · 103 100 % · 104 75 % · 105 92 % · 106 92 % | rechazado: no llega al mínimo; olvida exp-101 | `a867d31d` |
