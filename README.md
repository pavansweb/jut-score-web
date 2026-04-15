# Jut-Score Storage Web App

A Flask-based web application that allows you to upload files directly to a GitHub repository (`pavansweb/jut-score`) using the PyGithub library.

## Setup

1.  **Clone the repository.**
2.  **Create a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure environment variables:**
    Create a `.env` file in the root directory with the following content:
    ```env
    GITHUB_TOKEN=your_personal_access_token
    GITHUB_REPO=pavansweb/jut-score
    FLASK_SECRET_KEY=some_random_secret_key
    ```
5.  **Run the application:**
    ```bash
    python3 app.py
    ```
6.  Open `http://127.0.0.1:5000` in your browser.

## Features
- File upload interface.
- Automatic creation or update of files in the GitHub repository.
- Flash messages for success or error feedback.
