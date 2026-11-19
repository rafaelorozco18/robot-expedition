"""Exporta el actor de modelos de Stable-Baselines3 (.zip) a .npz para evaluar sin PyTorch.

Uso: python scripts/exportar_politicas.py modelo.zip [...]   (escribe modelo.npz al lado)
"""
import io
import sys
import zipfile
from pathlib import Path

import numpy as np
import torch


def exportar(ruta):
    ruta = Path(ruta)
    with zipfile.ZipFile(ruta) as z:
        sd = torch.load(io.BytesIO(z.read("policy.pth")), map_location="cpu")
    f = lambda k: sd[k].detach().numpy().astype(np.float32)  # noqa: E731
    destino = ruta.with_suffix(".npz")
    np.savez(destino, w0=f("mlp_extractor.policy_net.0.weight"), b0=f("mlp_extractor.policy_net.0.bias"),
             w1=f("mlp_extractor.policy_net.2.weight"), b1=f("mlp_extractor.policy_net.2.bias"),
             w2=f("action_net.weight"), b2=f("action_net.bias"), log_std=f("log_std"))
    return destino


if __name__ == "__main__":
    for r in sys.argv[1:]:
        print(exportar(r))
