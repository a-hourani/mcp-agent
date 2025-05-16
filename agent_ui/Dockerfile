# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

# Expose the port that the app will run on
EXPOSE 8501

# Run server.py when the container launches
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]

