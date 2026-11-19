"""La política exportada a numpy (servidor de Vercel) actúa igual que la de Stable-Baselines3."""
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parents[1]
MODELO = RAIZ / "models" / "exp-108" / "semilla-1" / "experto.zip"


@pytest.mark.skipif(not MODELO.exists(), reason="requiere `dvc pull` del modelo del Exp 8")
def test_media_y_episodio_iguales(tmp_path):
    import shutil
    import sys
    sys.path.insert(0, str(RAIZ / "scripts"))
    from exportar_politicas import exportar
    from expedicion import experimentos as X
    from expedicion.evaluar import Politica, PoliticaNumpy, correr_episodio

    copia = tmp_path / "experto.zip"
    shutil.copy(MODELO, copia)
    sb3, npy = Politica(copia), PoliticaNumpy(exportar(copia))
    rng = np.random.default_rng(0)
    for _ in range(50):
        obs = rng.normal(0, 1, 58).astype(np.float32)
        a = sb3.para_episodio(1)
        media = a.politica.get_distribution(a.politica.obs_to_tensor(obs)[0]).distribution.mean.detach().numpy()[0]
        assert np.allclose(media, npy.media(obs), atol=1e-5)
    exp = X.cargar("exp-108")
    for semilla in (3000, 3001):
        r1, _ = correr_episodio(exp, sb3, {"planeta": "marte", "perturbacion": "ninguna", "semilla": semilla})
        r2, _ = correr_episodio(exp, npy, {"planeta": "marte", "perturbacion": "ninguna", "semilla": semilla})
        assert r1["exito"] == r2["exito"]
