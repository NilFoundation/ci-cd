import json

from utils import RelatedPR, RelatedPRsCommentBody, TagParser


SYNCWITH_TAG = "SyncWith"


def get_syncwith_issue(g, pr_title, org_name=None):
    tags = TagParser.get_tags(pr_title)
    syncwith_value = tags.get(SYNCWITH_TAG)
    if syncwith_value is None:
        raise ValueError(f"No {SYNCWITH_TAG} tag found in PR title.")

    if "/" in syncwith_value:
        issue_org_name, repo_and_pr = syncwith_value.split("/")
    else:
        if org_name is None:
            raise ValueError(
                "No organisation name found in tag. You must provide org_name in this case."
            )
        issue_org_name = org_name
        repo_and_pr = syncwith_value
    issue_repo_name, issue_number = repo_and_pr.split("#")

    issue_repo = g.get_repo(f"{issue_org_name}/{issue_repo_name}")
    issue = issue_repo.get_issue(number=int(issue_number))
    return issue


def extract_related_prs(g, issue):
    related_prs_comment_body = RelatedPRsCommentBody()
    related_dataclass_prs = []
    existing_comment = None
    for comment in issue.get_comments():
        if related_prs_comment_body.parse_from(comment.body):
            existing_comment = comment
            data = json.loads(related_prs_comment_body.hidden_text)
            related_dataclass_prs = [RelatedPR.from_dict(d) for d in data]
            break

    related_prs = []
    for dataclass_pr in related_dataclass_prs:
        pr_repo = g.get_repo(dataclass_pr.repo)
        related_prs.append(pr_repo.get_pull(number=dataclass_pr.number))

    return related_prs, existing_comment
