"""Promedio de pesos (SWA) de varias fotos de una misma corrida: una sola red que suele generalizar mejor.

Uso: python scripts/promediar_pesos.py SALIDA.zip FOTO.zip FOTO.zip [...]
"""
import sys
import torch
from stable_baselines3 import PPO
salida, fotos = sys.argv[1], sys.argv[2:]
modelos = [PPO.load(f, device="cpu") for f in fotos]
estado = modelos[0].policy.state_dict()
for k in estado:
    if estado[k].is_floating_point():
        estado[k] = torch.stack([m.policy.state_dict()[k] for m in modelos]).mean(0)
modelos[0].policy.load_state_dict(estado)
modelos[0].save(salida)
print("guardado", salida)
