# API de simulación e inferencia de Robot Expedition (Hugging Face Space, SDK docker).
# Corre el mismo ambiente MuJoCo y los mismos modelos que el entrenamiento: Python es la autoridad.
FROM python:3.14-slim
ENV PIP_NO_CACHE_DIR=1 PYTHONUNBUFFERED=1 HOST=0.0.0.0 PORT=7860 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
RUN pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu \
 && pip install mujoco==3.17.0 gymnasium==1.4.0 stable_baselines3==2.9.2 numpy==2.5.4 PyYAML==6.0.3
RUN useradd -m -u 1000 user
WORKDIR /home/user/app
COPY --chown=user . .
USER user
EXPOSE 7860
CMD ["python", "-m", "expedicion", "servir"]
