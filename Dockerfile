# Dockerfile

# Stage 1: Use an official Python image as the base.
# This is like choosing the foundation for our container. We're starting with Python 3.11.
FROM python:3.11-slim

# Stage 2: Set the working directory inside the container.
# This is where all our project files will live.
WORKDIR /app

# Stage 3: Copy over the requirements file first.
# This is a smart trick. By copying this small file first, Docker can cache
# our installed packages, making future builds much faster.
COPY requirements.txt .

# Stage 4: Install the Python packages.
# We run the same pip install command we used on our local machine.
RUN pip install --no-cache-dir -r requirements.txt

# Stage 5: Copy the rest of our application code into the container.
# This includes main.py and our entire 'core' directory.
COPY . .

# Stage 6: Expose the port the app runs on.
# We're telling Docker that our server inside the container will be listening on port 8000.
EXPOSE 8000

# Stage 7: The command to run when the container starts.
# This is the same command we used to start our server locally, but ready for production.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
