FROM python:3.12-slim

# Install required system packages
RUN apt-get update && apt-get install -y \
    openjdk-17-jre-headless \
    wget \
    bash \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy jena install script
COPY scripts/install-jena.sh scripts/install-jena.sh

# Make install script executable
RUN chmod +x scripts/install-jena.sh

# Install Jena/Fuseki
RUN scripts/install-jena.sh

# Install Python tools in src (pyproject)
COPY pyproject.toml pyproject.toml
COPY src/ src/
RUN pip install .

# Copy scripts and data
COPY scripts/ scripts/

# Make a data directory and download dataset
RUN mkdir -p data && \
    wget -O data/Queen_Eliz_II.ged http://kingscoronation.com/wp-includes/images/Queen_Eliz_II.ged

# Make scripts executable
RUN chmod +x scripts/run-server.sh

# Convert GEDCOM to TTL
RUN python3 scripts/ged_to_ttl.py

# Expose Fuseki default port
EXPOSE 3031

# Start the server
CMD ["bash", "scripts/run-server.sh"]