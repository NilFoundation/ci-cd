import argparse
import os

from github import Github

from common import extract_related_prs, get_syncwith_issue
from utils import assign_output


def main():
    parser = argparse.ArgumentParser(description="Process SyncWith PRs")
    parser.add_argument("repo_name", help='Repository in format "Org/Repo"')
    parser.add_argument("pr_number", type=int, help="Pull request number")
    args = parser.parse_args()

    token = os.environ.get("CI_TOKEN")
    if not token:
        raise ValueError(
            "GitHub personal access token not provided in the environment variable 'CI_TOKEN'."
        )

    g = Github(token)

    repo = g.get_repo(args.repo_name)
    pr = repo.get_pull(args.pr_number)

    issue = get_syncwith_issue(g, pr.title, repo.organization.login)

    output_data = {}
    linked_prs, _ = extract_related_prs(g, issue)
    for linked_pr in linked_prs:
        head = linked_pr.head
        output_data[head.repo.full_name] = head.sha

    assign_output("prs-shas", "\n".join([f"{full_name}: {sha}" for full_name, sha in output_data.items()]))


if __name__ == "__main__":
    main()
