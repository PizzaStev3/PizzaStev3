import os
import hashlib
import datetime
from dateutil import relativedelta
import requests

BIRTHDAY = datetime.datetime(2004, 7, 6)

HEADERS = {"authorization": "token " + os.environ.get("ACCESS_TOKEN", "")}
USER_NAME = os.environ.get("USER_NAME", "")
QUERY_COUNT = {
    "user_getter": 0,
    "follower_getter": 0,
    "graph_repos_stars": 0,
    "graph_commits": 0,
    "loc_query": 0,
    "recursive_loc": 0,
}

GENERATED_DIRS = (
    "node_modules/", "/dist/", "/build/", "/out/", "/.next/", "/vendor/",
    "/venv/", "/.venv/", "/__pycache__/", "/bower_components/", "/target/",
    "/coverage/", "/.cache/", "/migrations/",
)
GENERATED_FILES = (
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "composer.lock",
    "gemfile.lock", "poetry.lock", "cargo.lock", "go.sum", "pipfile.lock",
)
GENERATED_EXT = (
    ".min.js", ".min.css", ".map", ".lock",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".bmp",
    ".pdf", ".zip", ".gz", ".tar", ".mp4", ".mov", ".webm", ".mp3",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".snap", ".pb.go",
)


def daily_readme(birthday):
    diff = relativedelta.relativedelta(datetime.datetime.today(), birthday)

    def plural(unit):
        return "s" if unit != 1 else ""

    return "{} year{}, {} month{}, {} day{}".format(
        diff.years, plural(diff.years),
        diff.months, plural(diff.months),
        diff.days, plural(diff.days),
    )


def simple_request(func_name, query, variables):
    response = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": variables},
        headers=HEADERS,
    )
    if response.status_code == 200:
        return response
    raise Exception(
        func_name, " has failed with a", response.status_code,
        response.text, query, variables,
    )


def user_getter(username):
    QUERY_COUNT["user_getter"] += 1
    query = """
    query($login: String!){
        user(login: $login) {
            id
            createdAt
        }
    }"""
    response = simple_request(user_getter.__name__, query, {"login": username})
    data = response.json()["data"]["user"]
    return {"id": data["id"]}, data["createdAt"]


def follower_getter(username):
    QUERY_COUNT["follower_getter"] += 1
    query = """
    query($login: String!){
        user(login: $login) { followers { totalCount } }
    }"""
    response = simple_request(follower_getter.__name__, query, {"login": username})
    return int(response.json()["data"]["user"]["followers"]["totalCount"])


def graph_commits(start_date, end_date):
    QUERY_COUNT["graph_commits"] += 1
    query = """
    query($start_date: DateTime!, $end_date: DateTime!, $login: String!) {
        user(login: $login) {
            contributionsCollection(from: $start_date, to: $end_date) {
                totalCommitContributions
                restrictedContributionsCount
            }
        }
    }"""
    variables = {"start_date": start_date, "end_date": end_date, "login": USER_NAME}
    response = simple_request(graph_commits.__name__, query, variables)
    collection = response.json()["data"]["user"]["contributionsCollection"]
    return int(collection["totalCommitContributions"]) + int(
        collection["restrictedContributionsCount"]
    )


def graph_repos_stars(count_type, owner_affiliation, cursor=None):
    QUERY_COUNT["graph_repos_stars"] += 1
    query = """
    query($owner_affiliation: [RepositoryAffiliation], $login: String!, $cursor: String) {
        user(login: $login) {
            repositories(first: 100, after: $cursor, ownerAffiliations: $owner_affiliation) {
                totalCount
                edges {
                    node {
                        stargazers { totalCount }
                    }
                }
                pageInfo { endCursor hasNextPage }
            }
        }
    }"""
    variables = {
        "owner_affiliation": owner_affiliation,
        "login": USER_NAME,
        "cursor": cursor,
    }
    response = simple_request(graph_repos_stars.__name__, query, variables)
    repos = response.json()["data"]["user"]["repositories"]
    if count_type == "repos":
        return repos["totalCount"]
    if count_type == "stars":
        return stars_counter(repos["edges"])
    return 0


def stars_counter(data):
    total = 0
    for node in data:
        total += node["node"]["stargazers"]["totalCount"]
    return total


def is_source_file(path):
    p = path.lower()
    if p.startswith("node_modules/") or any(d in "/" + p for d in GENERATED_DIRS):
        return False
    if p.rsplit("/", 1)[-1] in GENERATED_FILES:
        return False
    if p.endswith(GENERATED_EXT):
        return False
    return True


def commit_source_loc(owner, repo_name, sha):
    QUERY_COUNT["recursive_loc"] += 1
    response = requests.get(
        "https://api.github.com/repos/{}/{}/commits/{}".format(owner, repo_name, sha),
        headers=HEADERS,
    )
    if response.status_code != 200:
        return 0, 0
    add = dele = 0
    for f in response.json().get("files", []):
        if is_source_file(f.get("filename", "")):
            add += f.get("additions", 0)
            dele += f.get("deletions", 0)
    return add, dele


def recursive_loc(owner, repo_name, data, cache_comment, addition_total=0,
                  deletion_total=0, my_commits=0, cursor=None):
    QUERY_COUNT["recursive_loc"] += 1
    query = """
    query ($repo_name: String!, $owner: String!, $cursor: String) {
        repository(name: $repo_name, owner: $owner) {
            defaultBranchRef {
                target {
                    ... on Commit {
                        history(first: 100, after: $cursor) {
                            totalCount
                            edges {
                                node {
                                    ... on Commit {
                                        oid
                                        committedDate
                                        author { user { id } }
                                        deletions
                                        additions
                                    }
                                }
                            }
                            pageInfo { endCursor hasNextPage }
                        }
                    }
                }
            }
        }
    }"""
    variables = {"repo_name": repo_name, "owner": owner, "cursor": cursor}
    response = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": variables},
        headers=HEADERS,
    )
    if response.status_code != 200:
        return 0, 0, 0

    ref = response.json()["data"]["repository"]["defaultBranchRef"]
    if ref is None:
        return 0, 0, 0

    history = ref["target"]["history"]
    for edge in history["edges"]:
        node = edge["node"]
        if node["author"]["user"] == OWNER_ID:
            my_commits += 1
            add, dele = commit_source_loc(owner, repo_name, node["oid"])
            addition_total += add
            deletion_total += dele

    if history["edges"] == [] or not history["pageInfo"]["hasNextPage"]:
        return addition_total, deletion_total, my_commits
    return recursive_loc(
        owner, repo_name, data, cache_comment,
        addition_total, deletion_total, my_commits,
        history["pageInfo"]["endCursor"],
    )


def loc_query(owner_affiliation, comment_size=0, force_cache=False, cursor=None,
              edges=None):
    if edges is None:
        edges = []
    QUERY_COUNT["loc_query"] += 1
    query = """
    query ($owner_affiliation: [RepositoryAffiliation], $login: String!, $cursor: String) {
        user(login: $login) {
            repositories(first: 60, after: $cursor, ownerAffiliations: $owner_affiliation) {
                edges {
                    node {
                        nameWithOwner
                        defaultBranchRef {
                            target {
                                ... on Commit { history { totalCount } }
                            }
                        }
                    }
                }
                pageInfo { endCursor hasNextPage }
            }
        }
    }"""
    variables = {
        "owner_affiliation": owner_affiliation,
        "login": USER_NAME,
        "cursor": cursor,
    }
    response = simple_request(loc_query.__name__, query, variables)
    repos = response.json()["data"]["user"]["repositories"]
    edges += repos["edges"]
    if repos["pageInfo"]["hasNextPage"]:
        return loc_query(
            owner_affiliation, comment_size, force_cache,
            repos["pageInfo"]["endCursor"], edges,
        )
    return cache_builder(edges, comment_size, force_cache)


def cache_builder(edges, comment_size, force_cache, loc_add=0, loc_del=0):
    cached = True
    filename = "cache/" + hashlib.sha256(USER_NAME.encode("utf-8")).hexdigest() + ".txt"

    try:
        with open(filename, "r") as f:
            data = f.readlines()
    except FileNotFoundError:
        data = []
        if not os.path.exists("cache"):
            os.makedirs("cache")
        with open(filename, "w") as f:
            f.writelines(data)

    if len(data) - comment_size != len(edges) or force_cache:
        cached = False
        flush_cache(edges, filename, comment_size)
        with open(filename, "r") as f:
            data = f.readlines()

    cache_comment = data[:comment_size]
    data = data[comment_size:]

    for index in range(len(edges)):
        repo_hash, *__ = data[index].split()
        node = edges[index]["node"]
        current_hash = hashlib.sha256(
            node["nameWithOwner"].encode("utf-8")
        ).hexdigest()
        if repo_hash == current_hash:
            try:
                total_commits = node["defaultBranchRef"]["target"]["history"]["totalCount"]
            except TypeError:
                total_commits = 0
            if int(data[index].split()[2]) != total_commits:
                owner, repo_name = node["nameWithOwner"].split("/")
                loc = recursive_loc(owner, repo_name, data, cache_comment)
                data[index] = "{} {} {} {} {}\n".format(
                    current_hash, total_commits, loc[2], loc[0], loc[1]
                )

    with open(filename, "w") as f:
        f.writelines(cache_comment)
        f.writelines(data)

    for line in data:
        loc = line.split()
        loc_add += int(loc[3])
        loc_del += int(loc[4])
    return [loc_add, loc_del, loc_add - loc_del, cached]


def flush_cache(edges, filename, comment_size):
    with open(filename, "r") as f:
        data = []
        if comment_size > 0:
            data = f.readlines()[:comment_size]
    with open(filename, "w") as f:
        f.writelines(data)
        for node in edges:
            repo_hash = hashlib.sha256(
                node["node"]["nameWithOwner"].encode("utf-8")
            ).hexdigest()
            f.write(repo_hash + " 0 0 0 0\n")


def commit_counter(comment_size):
    total = 0
    filename = "cache/" + hashlib.sha256(USER_NAME.encode("utf-8")).hexdigest() + ".txt"
    with open(filename, "r") as f:
        data = f.readlines()
    for line in data[comment_size:]:
        total += int(line.split()[2])
    return total


if __name__ == "__main__":
    user_data, acc_date = user_getter(USER_NAME)
    OWNER_ID = user_data

    age_data = daily_readme(BIRTHDAY)

    total_commits = 0
    start = datetime.datetime.fromisoformat(acc_date.replace("Z", "+00:00"))
    now = datetime.datetime.now(datetime.timezone.utc)
    window_start = start
    while window_start < now:
        window_end = min(
            window_start + relativedelta.relativedelta(years=1), now
        )
        total_commits += graph_commits(
            window_start.isoformat(), window_end.isoformat()
        )
        window_start = window_end

    star_data = graph_repos_stars("stars", ["OWNER"])
    repo_data = graph_repos_stars("repos", ["OWNER"])
    contrib_data = graph_repos_stars(
        "repos", ["OWNER", "COLLABORATOR", "ORGANIZATION_MEMBER"]
    )
    follower_data = follower_getter(USER_NAME)

    total_loc = loc_query(
        ["OWNER", "COLLABORATOR", "ORGANIZATION_MEMBER"], comment_size=0
    )
    loc_add, loc_del, loc_net = total_loc[0], total_loc[1], total_loc[2]

    import build_svgs
    build_svgs.render_all({
        "age": age_data,
        "repos": repo_data,
        "contrib": contrib_data,
        "stars": star_data,
        "commits": total_commits,
        "followers": follower_data,
        "loc_net": loc_net,
        "loc_add": loc_add,
        "loc_del": loc_del,
    })

    print("Total GitHub API calls:", sum(QUERY_COUNT.values()))
    print("Done. dark_mode.svg and light_mode.svg updated.")
