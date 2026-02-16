FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    xz-utils \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Blender
RUN wget -q https://download.blender.org/release/Blender4.0/blender-4.0.2-linux-x64.tar.xz \
    && tar -xf blender-4.0.2-linux-x64.tar.xz \
    && mv blender-4.0.2-linux-x64 /opt/blender \
    && rm blender-4.0.2-linux-x64.tar.xz \
    && ln -s /opt/blender/blender /usr/local/bin/blender

# Set working directory
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py .

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "main.py"]
