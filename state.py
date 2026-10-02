from typing import TypedDict, List


class PipelineState(TypedDict):
    topic: str            # what to write about
    format: str           # "blog" or "thread"
    research: str         # notes from the Researcher
    draft: str            # latest text from the Writer
    final: str            # polished markdown from the Editor
    feedback: str         # Editor's advice to the Writer
    approved: bool        # did the Editor say yes?
    revision_count: int   # how many drafts so far
    errors: List[str]     # a diary of things that went wrong