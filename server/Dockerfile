# Use the official UV image with Python 3.12 and Debian Bookworm Slim
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set the working directory
WORKDIR /app

# Copy the project files into the container
COPY . .

# Install project dependencies
RUN uv sync --frozen

# Make the startup script executable
RUN chmod +x /app/start.sh

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application (migrations + server)
CMD ["/app/start.sh"]

