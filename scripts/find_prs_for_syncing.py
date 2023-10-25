import argparse
import json
import os

from github import Github

from common import extract_related_prs, get_syncwith_issue


def get_workflow_run_for_pr(pr, workflow_ref):
    workflow_path = '/'.join(workflow_ref.split('@')[0].split('/')[2:])

    workflow = next((wf for wf in pr.head.repo.get_workflows() if wf.path == workflow_path), None)
    if workflow is None:
        return None

    workflow_runs = workflow.get_runs(head_sha=pr.head.sha)
    for run in workflow_runs:
        if any(pr.number == run_pr.number for run_pr in run.pull_requests):
            return run

    return None


def main():
    parser = argparse.ArgumentParser(description="Process SyncWith PRs")
    parser.add_argument("repo_name", help='Repository in format "Org/Repo"')
    parser.add_argument("pr_number", type=int, help="Pull request number")
    parser.add_argument("workflow_ref", help="GITHUB_WORKFLOW_REF value to look for its last run in PRs")
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
        output_data[head.repo.full_name] = {
            "pr_number": linked_pr.number,
            "branch": head.ref,
            "sha": head.sha,
            "last_run_id": get_workflow_run_for_pr(linked_pr, args.workflow_ref).id,
        }

    print(json.dumps(output_data))


if __name__ == "__main__":
    main()
