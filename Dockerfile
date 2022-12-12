# Add a new comment to trigger build..
FROM python:3.10-slim-bullseye

# Install git (required to install packages directly from git).
RUN apt-get -y update
RUN apt-get -y install git

# Create a working directory, set it, and go into it.
WORKDIR /eventdispatch

# Copy all content in the src directory to the working directory.
COPY eventdispatch/ .

# Add src path to pythonpath.
ENV PYTHONPATH "${PYTHONPATH}:../"

# Run event center when container starts.
CMD ["bash"]
