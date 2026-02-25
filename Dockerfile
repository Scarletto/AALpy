FROM python:3.12-slim

# Install only the bare-minimum system packages:
#   - git            (for cloning / version tracking)
#   - graphviz       (runtime dependency of pydot)
RUN apt-get update \
    && apt-get install -y --no-install-recommends git graphviz \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY setup.py README.md ./
RUN pip install --no-cache-dir pydot

# Copy the project source
COPY aalpy/ aalpy/
COPY Benchmarking/ Benchmarking/
COPY DotModels/ DotModels/
COPY tests/ tests/
COPY RUN.py RUN.py
RUN mkdir CRG_results/

# Install the package in editable mode so `import aalpy` works everywhere
RUN pip install --no-cache-dir -e .

CMD ["bash"]
