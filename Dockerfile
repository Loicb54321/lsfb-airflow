# Start with the base Airflow image
FROM apache/airflow:2.6.3-python3.8

# Set the environment variables for Airflow
ENV AIRFLOW_HOME=/opt/airflow

# Install additional Python dependencies
RUN pip install --no-cache-dir pympi-ling tqdm moviepy mediapipe python-dotenv huggingface_hub datasets GitPython

USER root
RUN apt-get update && apt-get install -y libglib2.0-0 libgl1-mesa-glx

# Set the default command to run Airflow
CMD ["bash"]
