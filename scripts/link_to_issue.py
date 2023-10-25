import argparse
import json
import os

from github import Github

from common import extract_related_prs, get_syncwith_issue, SYNCWITH_TAG
from utils import RelatedPR, RelatedPRsCommentBody


class LinkerToIssue:
    def __init__(self, g, repo_name, pr_number):
        self.g = g
        self.current_repo = g.get_repo(repo_name)
        self.pr = self.current_repo.get_pull(pr_number)
        self.issue = get_syncwith_issue(
            self.g, self.pr.title, self.current_repo.organization.login
        )

    def _comment_issue_with_related_prs(self, prs, comment):
        dataclass_prs = [RelatedPR.from_github_object(pr) for pr in prs]

        dataclass_prs = sorted(dataclass_prs, key=lambda pr: pr.repo)
        dicts_for_dump = [pr.to_dict() for pr in dataclass_prs]

        comment_body = RelatedPRsCommentBody()
        if comment is not None:
            if comment_body.parse_from(
                comment.body
            ):  # and comment.user.id == self.g.get_app().id:
                if json.loads(comment_body.hidden_text) == dicts_for_dump:
                    print("The same issue comment already exists, exiting...")
                    return

        comment_visible_part = "PRs, synced with the current issue:\n"
        for pr in dataclass_prs:
            comment_visible_part += (
                f"- [{pr.repo}#{pr.number}]({pr.url}) (SHA: {pr.sha[:7]})\n"
            )

        comment_body.visible_text = comment_visible_part
        comment_body.hidden_text = json.dumps(dicts_for_dump)
        if comment is not None:
            print("Editing existing issue comment")
            comment.edit(comment_body.dump())
        else:
            print("Creating new issue comment")
            raise
            self.issue.create_comment(comment_body.dump())

    def _comment_pr(self):
        comment_content = (
            "Tests will be run in sync with other PRs containing "
            f"`[{SYNCWITH_TAG} {self.issue.repository.full_name}#{self.issue.number}]` in title. "
            f"You can find related PRs as linked with mentioned [issue]({self.issue.html_url})."
        )

        for comment in self.pr.get_issue_comments():
            if comment_content in comment.body:
                print("The same PR comment already exists, exiting...")
                return  # Comment already exists, not adding another one

        self.pr.create_issue_comment(comment_content)

    def link_pr_to_issue(self):
        prs_to_include_to_comment, comment = extract_related_prs(self.g, self.issue)
        if not any(  # if current repo is not presented, add it
            filter(
                lambda extracted_pr: extracted_pr.base.repo.full_name
                == self.pr.base.repo.full_name,
                prs_to_include_to_comment,
            )
        ):
            prs_to_include_to_comment.append(self.pr)

        self._comment_issue_with_related_prs(prs_to_include_to_comment, comment)
        self._comment_pr()


def main():
    parser = argparse.ArgumentParser(
        description="Extract related PRs based on PR title"
    )
    parser.add_argument(
        "repo_name", help="Full name of the current repository, e.g., 'org/repo'"
    )
    parser.add_argument("pr_number", type=int, help="Pull request number")
    args = parser.parse_args()

    token = os.environ.get("CI_TOKEN")
    if not token:
        raise ValueError(
            "GitHub token not provided in the environment variable 'CI_TOKEN'."
        )

    g = Github(token)

    linker = LinkerToIssue(g, args.repo_name, args.pr_number)
    linker.link_pr_to_issue()


if __name__ == "__main__":
    main()
