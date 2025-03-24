# Start with the base Airflow image
FROM apache/airflow:2.6.3-python3.8

# Set the environment variables for Airflow
ENV AIRFLOW_HOME=/opt/airflow

# Install additional Python dependencies
RUN pip install --no-cache-dir pympi-ling tqdm moviepy mediapipe python-dotenv huggingface_hub datasets GitPython

USER root

# First perform a full system upgrade
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get upgrade -y --no-install-recommends && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates \
        libglib2.0-0 \
        libgl1-mesa-glx \
        shared-mime-info \
        mime-support && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    # Workaround for segfault issue
    rm -f /var/lib/dpkg/info/shared-mime-info.postinst && \
    dpkg --configure -a

# Set the default command to run Airflow
CMD ["bash"]
