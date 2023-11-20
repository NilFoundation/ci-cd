import os
import re
from dataclasses import dataclass, asdict, is_dataclass


class CommentBodyManager:
    tag = None
    need_caution = False

    def __init__(self, hidden_text="", visible_text=""):
        self.hidden_text = hidden_text
        self.visible_text = visible_text

    def parse_from(self, comment_content):
        if not self.tag or self.tag not in comment_content:
            return False

        pattern = r"<!-- (.*?)\n(.*?)\n-->\n(.*)"
        match = re.search(
            pattern, comment_content.replace("\r\n", "\n"), re.DOTALL
        )  # replace() is needed after manual comment edit
        if match is None:
            return False
        tag, hidden_text, visible_text = match.groups()
        if tag != self.tag:
            return False

        self.hidden_text = hidden_text
        self.visible_text = visible_text

        return True

    def dump(self):
        caution_message = (
            "\n\n**Note:** Please do not edit this comment; it's generated automatically."
            if self.need_caution
            else ""
        )
        return f"<!-- {self.tag}\n{self.hidden_text}\n-->\n{self.visible_text}{caution_message}"


class RelatedPRsCommentBody(CommentBodyManager):
    tag = "LINKED-PR-COMMENT"
    need_caution = True


def dict_serializable(cls):
    if not is_dataclass(cls):
        raise TypeError("dict_serializable should be used with dataclasses only")

    def to_dict_method(self):
        return asdict(self)

    @classmethod
    def from_dict_method(cls, data):
        return cls(**data)

    setattr(cls, "to_dict", to_dict_method)
    setattr(cls, "from_dict", from_dict_method)

    return cls


@dict_serializable
@dataclass
class RelatedPR:
    repo: str
    number: int
    sha: str
    url: str

    @classmethod
    def from_github_object(cls, pr):
        return cls(
            repo=pr.base.repo.full_name,
            number=pr.number,
            sha=pr.head.sha,
            url=pr.html_url,
        )


class TagParser:
    TAG_PATTERN = r"\[(\w+):\s*([^]]+)\]"

    @staticmethod
    def get_tags(string):
        matches = re.findall(TagParser.TAG_PATTERN, string)
        return {tag: value for tag, value in matches}


def assign_output(var_name, value):
    # https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#multiline-strings
    env_file = os.getenv("GITHUB_OUTPUT")
    with open(env_file, "a") as file:
        file.write(f"{var_name}<<EOF\n{value}\nEOF\n")
