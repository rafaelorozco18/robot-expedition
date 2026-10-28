"""Ambiente Gymnasium de Robot Expedition v0.1.

Misión: visitar la baliza 1, luego la baliza 2 (agarrando una muestra en cada
una) y volver a la base antes de agotar la batería.

Estado del mundo (lo sabe el simulador)   vs.   Observación (lo sabe el agente)
    posición absoluta, mapa completo,             8 rayos de distancia con ruido,
    batería, etapa, clima, gravedad,              vector y distancia al objetivo,
    incidente, generador aleatorio                velocidad, batería, etapa,
                                                  terreno bajo las ruedas,
                                                  clima y gravedad.
"""

import heapq

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from . import config as C

ETAPAS = ["baliza 1", "baliza 2", "base"]
INF = 10_000.0


class ExpedicionEnv(gym.Env):
    metadata = {"render_modes": ["ansi", "human"], "render_fps": 4}

    def __init__(self, render_mode=None, mapa=None, clima=None, gravedad=None,
                 incidente="ninguno", **parametros):
        self.render_mode = render_mode
        self.mapa_base = [list(fila) for fila in (mapa or C.MAPA_V01)]
        self.alto = len(self.mapa_base)
        self.ancho = len(self.mapa_base[0])
        # Si clima/gravedad son None, se sortean en cada reset (entrenamiento robusto).
        self.clima_fijo = clima
        self.gravedad_fija = gravedad
        self.incidente_fijo = incidente
        self.p = {**C.PARAMETROS_AMBIENTE, **parametros}

        lado = max(self.ancho, self.alto) - 1
        alcance = self.p["alcance_sensor"]
        self.observation_space = spaces.Dict({
            "rayos": spaces.Box(0.0, alcance, shape=(8,), dtype=np.float32),
            "objetivo": spaces.Box(-lado, lado, shape=(2,), dtype=np.int64),
            "distancia_objetivo": spaces.Box(0.0, 2.0 * lado, shape=(1,), dtype=np.float32),
            "velocidad": spaces.Box(0.0, 3.0, shape=(1,), dtype=np.float32),
            "bateria": spaces.Box(0.0, self.p["bateria_inicial"], shape=(1,), dtype=np.float32),
            "etapa": spaces.Discrete(3),
            "terreno": spaces.Discrete(len(C.CODIGOS_TERRENO)),
            "clima": spaces.Discrete(len(C.NOMBRES_CLIMA)),
            "gravedad": spaces.Box(0.0, 15.0, shape=(1,), dtype=np.float32),
        })
        self.action_space = spaces.Discrete(len(C.ACCIONES))

    # ------------------------------------------------------------------ mapa
    def _preparar_mapa(self, incidente):
        self.mapa = [fila[:] for fila in self.mapa_base]
        for (x, y), codigo in C.INCIDENTES[incidente].items():
            self.mapa[y][x] = codigo
        self.puntos = {}
        for y, fila in enumerate(self.mapa):
            for x, c in enumerate(fila):
                if c in "B12":
                    self.puntos[c] = (x, y)
        self.objetivos = [self.puntos["1"], self.puntos["2"], self.puntos["B"]]
        # Distancias geodésicas a cada objetivo (para el moldeado de recompensa)
        self.dist = [self._dijkstra(o) for o in self.objetivos]
        self.tramo = [self.dist[1][self.objetivos[0][1]][self.objetivos[0][0]],
                      self.dist[2][self.objetivos[1][1]][self.objetivos[1][0]]]

    def celda(self, x, y):
        if 0 <= x < self.ancho and 0 <= y < self.alto:
            return self.mapa[y][x]
        return "#"  # fuera del mapa = límite infranqueable

    def _dijkstra(self, destino):
        """Ruta segura más corta (caminando o saltando, sin pisar grietas), en metros."""
        dist = [[INF] * self.ancho for _ in range(self.alto)]
        dx0, dy0 = destino
        dist[dy0][dx0] = 0.0
        cola = [(0.0, destino)]
        seguro = lambda c: C.TERRENOS[c]["pisable"] and c != "G"
        while cola:
            d, (x, y) = heapq.heappop(cola)
            if d > dist[y][x]:
                continue
            for mx, my in C.DIRECCIONES.values():
                vecinos = [((x + mx, y + my), 1.0)]
                medio = self.celda(x + mx, y + my)
                if C.TERRENOS[medio]["saltable"]:
                    vecinos.append(((x + 2 * mx, y + 2 * my), 2.0))
                for (nx, ny), costo in vecinos:
                    if seguro(self.celda(nx, ny)) and d + costo < dist[ny][nx]:
                        dist[ny][nx] = d + costo
                        heapq.heappush(cola, (d + costo, (nx, ny)))
        return dist

    def ruta_restante(self, pos=None, etapa=None):
        """Metros que faltan para terminar la misión por la ruta segura más corta."""
        x, y = pos or self.pos
        etapa = self.etapa if etapa is None else etapa
        if etapa >= 3:
            return 0.0
        return self.dist[etapa][y][x] + sum(self.tramo[etapa:])

    # ----------------------------------------------------------- condiciones
    def condiciones(self):
        clima = C.CLIMAS[self.clima]
        terreno = self.celda(*self.pos)
        p_desl = min(0.9, clima["deslizar"] * C.factor_traccion(self.g))
        return {
            "clima": self.clima,
            "gravedad": self.nombre_gravedad,
            "g": self.g,
            "incidente": self.incidente,
            "terreno": C.TERRENOS[terreno]["nombre"],
            "prob_deslizar": p_desl,
            "prob_atasco": clima["atasco"] if terreno == "b" else 0.0,
            "consumo_clima": clima["consumo"],
            "ruido_sensor": self.p["ruido_sensor"] * clima["ruido"],
            "costo_salto": C.costo_salto(self.g),
            "prob_sobrevuelo": C.prob_sobrevuelo(self.g),
        }

    # --------------------------------------------------------- gymnasium API
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        options = options or {}
        self.clima = options.get("clima", self.clima_fijo) or \
            C.NOMBRES_CLIMA[self.np_random.integers(len(C.NOMBRES_CLIMA))]
        self.nombre_gravedad = options.get("gravedad", self.gravedad_fija) or \
            C.NOMBRES_GRAVEDAD[self.np_random.integers(len(C.NOMBRES_GRAVEDAD))]
        self.g = C.GRAVEDADES[self.nombre_gravedad]
        self.incidente = options.get("incidente", self.incidente_fijo) or "ninguno"
        self._preparar_mapa(self.incidente)

        self.pos = self.puntos["B"]
        self.etapa = 0
        self.bateria = float(self.p["bateria_inicial"])
        self.pasos = 0
        self.velocidad = 0.0
        self.eventos = []
        self.ultima_accion = None
        return self._observar(), self._info()

    def step(self, action):
        if not self.action_space.contains(action):
            raise ValueError(f"Acción inválida: {action!r} (0..{self.action_space.n - 1}).")
        action = int(action)
        clima = C.CLIMAS[self.clima]
        tipo, d = C.ACCIONES[action]
        self.eventos = []
        self.ultima_accion = action
        r = C.RECOMPENSAS
        recompensa = r["paso"]
        gasto = 0.0
        ruta_antes = self.ruta_restante()
        inicio = self.pos
        terminated = False
        motivo = None

        if tipo == "agarrar":
            gasto += C.COSTOS["agarrar"]
            if self.etapa < 2 and self.pos == self.objetivos[self.etapa]:
                recompensa += r["baliza"]
                self.eventos.append(f"agarró {ETAPAS[self.etapa]}")
                self.etapa += 1
            else:
                recompensa += r["agarrar_invalido"]
                self.eventos.append("agarre inválido")
        elif self.celda(*self.pos) == "b" and self.np_random.random() < clima["atasco"]:
            # El barro retiene las ruedas: se gasta energía pero no se avanza.
            gasto += C.TERRENOS["b"]["costo"]
            self.eventos.append("atascado en barro")
        else:
            mx, my = C.DIRECCIONES[d]
            if tipo == "mover":
                destino = (self.pos[0] + mx, self.pos[1] + my)
                if C.TERRENOS[self.celda(*destino)]["pisable"]:
                    self.pos = destino
                    gasto += C.TERRENOS[self.celda(*destino)]["costo"]
                else:
                    recompensa += r["choque"]
                    gasto += C.COSTOS["choque"]
                    self.eventos.append(f"choque con {C.TERRENOS[self.celda(*destino)]['nombre']}")
            else:  # saltar 2 celdas por encima de rocas o grietas
                gasto += C.costo_salto(self.g)
                medio = (self.pos[0] + mx, self.pos[1] + my)
                destino = (self.pos[0] + 2 * mx, self.pos[1] + 2 * my)
                if not C.TERRENOS[self.celda(*medio)]["saltable"] or \
                        not C.TERRENOS[self.celda(*destino)]["pisable"]:
                    recompensa += r["choque"]
                    gasto += C.COSTOS["choque"]
                    self.eventos.append("salto bloqueado")
                else:
                    self.eventos.append("salto")
                    largo = (destino[0] + mx, destino[1] + my)
                    if self.np_random.random() < C.prob_sobrevuelo(self.g) and \
                            C.TERRENOS[self.celda(*largo)]["pisable"]:
                        destino = largo
                        self.eventos.append("se pasó de largo (baja gravedad)")
                    self.pos = destino
            # El hielo hace patinar una celda más: recto o hacia un costado.
            if self.celda(*self.pos) == "h" and self.pos != inicio and \
                    self.np_random.random() < self.condiciones()["prob_deslizar"]:
                opciones = [(mx, my), (my, mx), (-my, -mx)]
                sx, sy = opciones[self.np_random.integers(3)]
                patinazo = (self.pos[0] + sx, self.pos[1] + sy)
                if C.TERRENOS[self.celda(*patinazo)]["pisable"]:
                    self.pos = patinazo
                    self.eventos.append("patinó en hielo")

        gasto *= clima["consumo"]
        self.bateria = max(0.0, self.bateria - gasto)
        recompensa += r["consumo"] * gasto
        self.velocidad = float(abs(self.pos[0] - inicio[0]) + abs(self.pos[1] - inicio[1]))
        self.pasos += 1

        if self.celda(*self.pos) == "G":
            recompensa += r["caida"]
            terminated, motivo = True, "cayó en una grieta"
        else:
            # Moldeado por potencial Φ = −k·ruta_restante: no se puede ganar dando vueltas.
            if self.etapa == 2 and self.pos == self.objetivos[2]:
                self.etapa = 3
            gamma = self.p["gamma_moldeado"]
            recompensa += r["progreso"] * (ruta_antes - gamma * self.ruta_restante())
            if self.etapa == 3:
                recompensa += r["mision"] + r["bateria_restante"] * self.bateria
                terminated, motivo = True, "misión completa"
            elif self.bateria <= 0.0:
                recompensa += r["sin_bateria"]
                terminated, motivo = True, "batería agotada"

        truncated = not terminated and self.pasos >= self.p["max_pasos"]
        if truncated:
            motivo = "tiempo agotado"
        self.motivo = motivo
        if self.render_mode == "human":
            print(self._texto())
        return self._observar(), float(recompensa), terminated, truncated, self._info()

    # ----------------------------------------------------------- percepción
    def _rayos(self):
        alcance = self.p["alcance_sensor"]
        ruido = self.p["ruido_sensor"] * C.CLIMAS[self.clima]["ruido"]
        lecturas = []
        for rx, ry in C.RAYOS:
            paso = np.hypot(rx, ry)
            d = alcance
            for k in range(1, int(alcance) + 1):
                c = self.celda(self.pos[0] + k * rx, self.pos[1] + k * ry)
                if c in "#RG":  # obstáculos y peligros
                    d = min(alcance, (k - 0.5) * paso)
                    break
            lecturas.append(d + self.np_random.normal(0.0, ruido))
        return np.clip(np.array(lecturas, dtype=np.float32), 0.0, alcance)

    def _observar(self):
        objetivo = self.objetivos[min(self.etapa, 2)]
        dx, dy = objetivo[0] - self.pos[0], objetivo[1] - self.pos[1]
        return {
            "rayos": self._rayos(),
            "objetivo": np.array([dx, dy], dtype=np.int64),
            "distancia_objetivo": np.array([np.hypot(dx, dy)], dtype=np.float32),
            "velocidad": np.array([self.velocidad], dtype=np.float32),
            "bateria": np.array([self.bateria], dtype=np.float32),
            "etapa": min(self.etapa, 2),
            "terreno": C.CODIGOS_TERRENO.index(self.celda(*self.pos)),
            "clima": C.NOMBRES_CLIMA.index(self.clima),
            "gravedad": np.array([self.g], dtype=np.float32),
        }

    def _info(self):
        return {
            "posicion": self.pos,
            "etapa": self.etapa,
            "bateria": self.bateria,
            "pasos": self.pasos,
            "eventos": list(self.eventos),
            "ruta_restante": self.ruta_restante(),
            "condiciones": self.condiciones(),
            "exito": self.etapa == 3,
        }

    # -------------------------------------------------------------- render
    def render(self):
        if self.render_mode == "human":
            print(self._texto())
            return None
        return self._texto()

    def _texto(self):
        colores = {".": "\033[38;5;180m", "a": "\033[38;5;222m", "b": "\033[38;5;94m",
                   "h": "\033[38;5;153m", "R": "\033[38;5;245m", "#": "\033[38;5;240m",
                   "G": "\033[38;5;52m", "B": "\033[38;5;40m", "1": "\033[38;5;51m",
                   "2": "\033[38;5;51m"}
        simbolos = {".": "·", "a": "░", "b": "▒", "h": "≈", "R": "▲", "#": "█",
                    "G": "▼", "B": "B", "1": "1", "2": "2"}
        filas = []
        for y in range(self.alto):
            fila = ""
            for x in range(self.ancho):
                c = self.mapa[y][x]
                if (x, y) == self.pos:
                    fila += "\033[1;38;5;208m◉ \033[0m"
                else:
                    fila += f"{colores[c]}{simbolos[c]} \033[0m"
            filas.append(fila)
        accion = C.NOMBRES_ACCION[self.ultima_accion] if self.ultima_accion is not None else "—"
        filas.append(f"paso {self.pasos:3d} · batería {self.bateria:5.1f}% · "
                     f"objetivo: {ETAPAS[min(self.etapa, 2)]} · acción: {accion}")
        filas.append(f"clima {self.clima} · gravedad {self.nombre_gravedad} ({self.g} m/s²)"
                     f" · terreno {C.TERRENOS[self.celda(*self.pos)]['nombre']}")
        if self.eventos:
            filas.append("eventos: " + ", ".join(self.eventos))
        return "\n".join(filas)
