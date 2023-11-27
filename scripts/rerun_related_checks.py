import argparse
import os
import time

from github import Github

from common import extract_related_prs, get_syncwith_issue


def is_final_status(status):
    final_statuses = [
        "completed",
        "action_required",
        "cancelled",
        "failure",
        "neutral",
        "skipped",
        "stale",
        "success",
        "timed_out",
    ]
    return status in final_statuses


def wait_for_workflow_completion(workflow_run, timeout_seconds=300) -> bool:
    initial_run_attempt = workflow_run.run_attempt
    elapsed_time = 0
    while not is_final_status(workflow_run.status) and elapsed_time < timeout_seconds:
        time.sleep(10)
        workflow_run.update()
        if workflow_run.run_attempt > initial_run_attempt:
            return False
        elapsed_time += 10

    if elapsed_time >= timeout_seconds:
        print(f"Timeout waiting for workflow {workflow_run.id} to complete.")
        raise TimeoutError(
            f"Cancelation timeout after {elapsed_time} seconds of waiting"
        )

    return True


def rerun_workflow_actions(github_client, repo_full_name, head_sha):
    repo = github_client.get_repo(repo_full_name)
    runs = repo.get_workflow_runs(head_sha=head_sha, event="pull_request")

    for run in runs:
        was_rerun = False
        if not is_final_status(run.status):
            print(f"Cancelling run {run.id} for {repo_full_name}")
            run.cancel()
            was_rerun = not wait_for_workflow_completion(run)

        print(f"Rerunning run {run.id} for {repo_full_name}")
        if not was_rerun:
            run.rerun()


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

    linked_prs, _ = extract_related_prs(g, issue)
    for linked_pr in linked_prs:
        head = linked_pr.head
        if head.repo.full_name == os.environ.get("GITHUB_REPOSITORY"):
            # Do not commit suicide
            continue
        rerun_workflow_actions(g, head.repo.full_name, head.sha)


if __name__ == "__main__":
    main()
