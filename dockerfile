# Use the official Python image as the base image
FROM python:3.11

# Allow statements and log messages to immediately appear in the logs
ENV PYTHONUNBUFFERED True

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . ./

# Install production dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Set an environment variable for the port
ENV PORT 1234

# Expose the port that Gunicorn will run on
EXPOSE $PORT

# As an example here we're running the web service with one worker on uvicorn.
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1