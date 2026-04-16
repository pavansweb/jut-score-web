import os
from functools import wraps
from pathlib import PurePosixPath

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for
from github import Auth, Github, GithubException
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback_secret_key")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
APP_PASSWORD = os.getenv("APP_PASSWORD", "pavan")
STORAGE_ROOT = "storage"
ALLOWED_EXTENSIONS = {
    "pdf",
    "png",
    "jpg",
    "jpeg",
    "webp",
    "txt",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "csv",
    "zip",
}

_repo_cache = None


def get_repo():
    global _repo_cache
    if _repo_cache is None:
        if not GITHUB_TOKEN:
            raise ValueError("Missing GITHUB_TOKEN in environment variables")
        if not GITHUB_REPO:
            raise ValueError("Missing GITHUB_REPO in environment variables")
        auth = Auth.Token(GITHUB_TOKEN)
        github_client = Github(auth=auth)
        _repo_cache = github_client.get_repo(GITHUB_REPO)
    return _repo_cache


def ensure_storage_exists(repo):
    try:
        repo.get_contents(STORAGE_ROOT)
    except GithubException as exc:
        if exc.status == 404:
            repo.create_file(f"{STORAGE_ROOT}/.gitkeep", "Initialize storage directory", "")
            return
        raise


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("authenticated"):
            flash("Enter the access password to open the document dashboard.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped


def normalize_storage_path(raw_path=None):
    path = (raw_path or STORAGE_ROOT).strip().strip("/")
    candidate = PurePosixPath(path or STORAGE_ROOT)
    cleaned = [part for part in candidate.parts if part not in ("", ".", "..")]
    if not cleaned or cleaned[0] != STORAGE_ROOT:
        cleaned = [STORAGE_ROOT]
    return "/".join(cleaned)


def is_allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def format_size(size_bytes):
    units = ["B", "KB", "MB", "GB"]
    size = float(size_bytes or 0)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return "0 B"


def get_file_icon(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "pdf":
        return "bi-file-earmark-pdf-fill"
    if ext in {"png", "jpg", "jpeg", "webp"}:
        return "bi-file-earmark-image"
    if ext in {"xls", "xlsx", "csv"}:
        return "bi-file-earmark-spreadsheet"
    if ext in {"doc", "docx", "txt"}:
        return "bi-file-earmark-text"
    if ext == "zip":
        return "bi-file-earmark-zip"
    return "bi-file-earmark"


def build_sidebar_tree(repo):
    try:
        root_contents = repo.get_contents(STORAGE_ROOT, ref=repo.default_branch)
    except GithubException:
        return []

    if not isinstance(root_contents, list):
        root_contents = [root_contents]

    folders = []
    for content in root_contents:
        if content.type != "dir":
            continue
        folders.append(
            {
                "name": content.name,
                "path": content.path,
            }
        )
    folders.sort(key=lambda item: item["name"].lower())
    return folders


def get_folder_summary(files, folders):
    pdf_count = sum(1 for file in files if file["extension"] == "pdf")
    total_size = sum(file["size"] for file in files)
    return {
        "file_count": len(files),
        "folder_count": len(folders),
        "pdf_count": pdf_count,
        "total_size": format_size(total_size),
    }


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("authenticated"):
        return redirect(url_for("index"))

    if request.method == "POST":
        password = request.form.get("password", "")
        if password == APP_PASSWORD:
            session["authenticated"] = True
            flash("Access granted.", "success")
            return redirect(url_for("index"))
        flash("Wrong password.", "danger")

    return render_template("login.html")


@app.post("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("login"))


@app.route("/")
@app.route("/browse/<path:folder_path>")
@login_required
def index(folder_path=STORAGE_ROOT):
    folder_path = normalize_storage_path(folder_path)

    try:
        repo = get_repo()
        if folder_path == STORAGE_ROOT:
            ensure_storage_exists(repo)

        try:
            contents = repo.get_contents(folder_path, ref=repo.default_branch)
        except GithubException as exc:
            if exc.status == 404:
                flash(f"Folder '{folder_path}' not found.", "warning")
                return redirect(url_for("index"))
            raise

        if not isinstance(contents, list):
            contents = [contents]

        files = []
        folders = []
        parent_path = None
        if folder_path != STORAGE_ROOT:
            parent_path = normalize_storage_path(str(PurePosixPath(folder_path).parent))

        sidebar_folders = build_sidebar_tree(repo)

        for content in contents:
            if content.type == "dir":
                folders.append({"name": content.name, "path": content.path})
                continue

            if content.type == "file" and not content.name.startswith("."):
                extension = content.name.rsplit(".", 1)[-1].lower() if "." in content.name else ""
                files.append(
                    {
                        "name": content.name,
                        "path": content.path,
                        "download_url": content.download_url,
                        "size": content.size,
                        "size_label": format_size(content.size),
                        "sha": content.sha,
                        "extension": extension,
                        "is_pdf": extension == "pdf",
                        "icon": get_file_icon(content.name),
                    }
                )

        folders.sort(key=lambda item: item["name"].lower())
        files.sort(key=lambda item: item["name"].lower())

        return render_template(
            "index.html",
            files=files,
            folders=folders,
            current_path=folder_path,
            parent_path=parent_path,
            sidebar_folders=sidebar_folders,
            summary=get_folder_summary(files, folders),
        )
    except Exception as exc:
        flash(f"Error fetching contents: {exc}", "danger")
        return render_template(
            "index.html",
            files=[],
            folders=[],
            current_path=folder_path,
            parent_path=None,
            sidebar_folders=[],
            summary=get_folder_summary([], []),
        )


@app.post("/upload")
@login_required
def upload_file():
    folder_path = normalize_storage_path(request.form.get("folder_path", STORAGE_ROOT))
    if "file" not in request.files:
        flash("No file selected.", "danger")
        return redirect(url_for("index", folder_path=folder_path))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected.", "warning")
        return redirect(url_for("index", folder_path=folder_path))

    filename = secure_filename(file.filename)
    if not filename:
        flash("Invalid file name.", "warning")
        return redirect(url_for("index", folder_path=folder_path))

    if not is_allowed_file(filename):
        flash("Unsupported file type.", "danger")
        return redirect(url_for("index", folder_path=folder_path))

    content = file.read()
    full_path = f"{folder_path}/{filename}"

    try:
        repo = get_repo()
        branch = repo.default_branch
        try:
            existing = repo.get_contents(full_path, ref=branch)
            repo.update_file(
                existing.path,
                f"Update {filename} via jut-score-web",
                content,
                existing.sha,
                branch=branch,
            )
            flash(f"Updated {filename}.", "success")
        except GithubException as exc:
            if exc.status == 404:
                repo.create_file(
                    full_path,
                    f"Upload {filename} via jut-score-web",
                    content,
                    branch=branch,
                )
                flash(f"Uploaded {filename}.", "success")
            else:
                raise
    except Exception as exc:
        flash(f"Error uploading file: {exc}", "danger")

    return redirect(url_for("index", folder_path=folder_path))


@app.post("/create_folder")
@login_required
def create_folder():
    folder_name = secure_filename(request.form.get("folder_name", ""))
    current_path = normalize_storage_path(request.form.get("current_path", STORAGE_ROOT))

    if not folder_name:
        flash("Folder name is required.", "warning")
        return redirect(url_for("index", folder_path=current_path))

    folder_path = f"{current_path}/{folder_name}"
    try:
        repo = get_repo()
        repo.create_file(
            f"{folder_path}/.gitkeep",
            f"Create folder {folder_name} via jut-score-web",
            "",
            branch=repo.default_branch,
        )
        flash(f"Folder '{folder_name}' created.", "success")
        return redirect(url_for("index", folder_path=folder_path))
    except Exception as exc:
        flash(f"Error creating folder: {exc}", "danger")
        return redirect(url_for("index", folder_path=current_path))


@app.post("/delete/<path:path>")
@login_required
def delete_file(path):
    safe_path = normalize_storage_path(path)
    folder_path = normalize_storage_path(str(PurePosixPath(safe_path).parent))
    try:
        repo = get_repo()
        branch = repo.default_branch
        content = repo.get_contents(safe_path, ref=branch)

        if isinstance(content, list):
            flash("Cannot delete a folder from this action.", "danger")
            return redirect(url_for("index", folder_path=folder_path))

        repo.delete_file(
            content.path,
            f"Delete {safe_path} via jut-score-web",
            content.sha,
            branch=branch,
        )
        flash(f"Deleted {os.path.basename(safe_path)}.", "success")
    except Exception as exc:
        flash(f"Error deleting file: {exc}", "danger")
    return redirect(url_for("index", folder_path=folder_path))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
