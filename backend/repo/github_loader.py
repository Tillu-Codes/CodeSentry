import urllib.parse
from dataclasses import dataclass

import httpx

MAX_FILES = 500
MAX_FILE_BYTES = 2_000_000


class GitHubURLError(ValueError):
    pass


@dataclass
class GithubRepo:
    owner: str
    repo: str
    branch: str
    paths: list[str]


def _strip_git_suffix(name: str) -> str:
    return name[:-4] if name.endswith(".git") else name


def parse_github_url(url: str) -> tuple[str, str, str | None]:
    """Extract (owner, repo, branch) from the common GitHub URL shapes."""
    url = url.strip()
    if not url:
        raise GitHubURLError("Empty URL")
    if url.startswith("git@"):
        url = url.split(":", 1)[-1]
        parts = [p for p in url.split("/") if p]
    else:
        if "://" not in url:
            url = f"https://{url}"
        parsed = urllib.parse.urlparse(url)
        if (parsed.hostname or "").replace("www.", "") != "github.com":
            raise GitHubURLError(f"Not a GitHub URL: {url}")
        parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        raise GitHubURLError(f"Not a valid GitHub repository URL: {url}")
    owner, repo = parts[0], _strip_git_suffix(parts[1])
    branch = None
    if len(parts) >= 4 and parts[2] == "tree":
        branch = "/".join(parts[3:])
        if branch.endswith("/"):
            branch = branch[:-1]
    return owner, repo, branch


def load_github_repo(github_url: str, branch: str | None = None) -> GithubRepo:
    """Resolve a public GitHub repo to its default (or requested) branch and .py paths."""
    owner, repo_name, url_branch = parse_github_url(github_url)
    from github import Github

    gh = Github()
    slug = f"{owner}/{repo_name}"
    try:
        repo = gh.get_repo(slug)
    except Exception as exc:
        raise GitHubURLError(
            f"Repository '{slug}' was not found or is not public. "
            f"Double-check the owner/repo part of the URL{_detail(exc)}"
        ) from exc
    ref = branch or url_branch or repo.default_branch
    try:
        commit = repo.get_commit(ref)
    except Exception as exc:
        raise GitHubURLError(
            f"Branch '{ref}' was not found in '{slug}'{_detail(exc)}"
        ) from exc
    try:
        tree = repo.get_git_tree(commit.commit.tree.sha, recursive=True)
    except Exception as exc:
        raise GitHubURLError(
            f"Could not read the file tree of '{slug}'{_detail(exc)}"
        ) from exc
    paths = [
        entry.path
        for entry in tree.tree
        if entry.type == "blob" and entry.path.endswith(".py")
    ][:MAX_FILES]
    return GithubRepo(owner=owner, repo=repo_name, branch=ref, paths=paths)


def _detail(exc: Exception) -> str:
    msg = str(exc).strip()
    return f" ({msg})" if msg else ""


def build_raw_url(gh: GithubRepo, path: str) -> str:
    quoted = "/".join(urllib.parse.quote(seg) for seg in f"{gh.branch}/{path}".split("/"))
    return f"https://raw.githubusercontent.com/{gh.owner}/{gh.repo}/{quoted}"


def fetch_raw_github_file(gh: GithubRepo, path: str) -> str | None:
    try:
        resp = httpx.get(build_raw_url(gh, path), timeout=30, follow_redirects=True)
        if resp.status_code != 200 or len(resp.content) > MAX_FILE_BYTES:
            return None
        return resp.text
    except Exception:
        return None