import os
import base64
from flask import Flask, render_template, request, redirect, url_for, flash
from github import Github, GithubException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback_secret_key")

# GitHub configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")

# Initialize GitHub client
g = Github(GITHUB_TOKEN)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        flash("No file part")
        return redirect(url_for("index"))
    
    file = request.files["file"]
    
    if file.filename == "":
        flash("No selected file")
        return redirect(url_for("index"))
    
    if file:
        filename = file.filename
        content = file.read()
        
        try:
            repo = g.get_repo(GITHUB_REPO)
            
            # Use the default branch from the repo
            branch = repo.default_branch
            
            # Check if file already exists in the repo
            try:
                contents = repo.get_contents(filename, ref=branch)
                # Update existing file
                repo.update_file(
                    contents.path,
                    f"Update {filename} via jut-score-web",
                    content,
                    contents.sha,
                    branch=branch
                )
                flash(f"Successfully updated {filename} on GitHub!")
            except GithubException as e:
                if e.status == 404:
                    # Create new file
                    repo.create_file(
                        filename,
                        f"Upload {filename} via jut-score-web",
                        content,
                        branch=branch
                    )
                    flash(f"Successfully uploaded {filename} to GitHub!")
                else:
                    raise e
                    
        except Exception as e:
            flash(f"Error: {str(e)}")
            
        return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
