"""
Source context rendering for Session 11 verifiable line citations.

The generation prompt must expose exact chunk ids and document ids so the model
can cite only sources that were actually retrieved.
"""

from html import escape

from pydantic import BaseModel, Field


class RetrievedSourceChunk(BaseModel):
    """A retrieved chunk prepared for line-level citation in generation."""

    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    content: str = Field(min_length=1)


def render_source_context(chunks: list[RetrievedSourceChunk]) -> str:
    """
    Render retrieved chunks as explicit source blocks.

    The output is prompt text, not an XML document parser contract. Escaping
    prevents source content from breaking the source block boundaries.
    """

    if not chunks:
        return "<retrieved_context>\nNO_RETRIEVED_CONTEXT\n</retrieved_context>"

    source_blocks = []
    for chunk in chunks:
        source_blocks.append(
            "\n".join(
                [
                    (
                        f'<source id="{escape(chunk.chunk_id, quote=True)}" '
                        f'document_id="{escape(chunk.document_id, quote=True)}">'
                    ),
                    escape(chunk.content, quote=False),
                    "</source>",
                ]
            )
        )

    return "\n".join(
        [
            "<retrieved_context>",
            *source_blocks,
            "</retrieved_context>",
        ]
    )


def build_line_citation_prompt_rules() -> str:
    """
    Return strict generation rules for Session 11 line-level citations.
    """

    return "\n".join(
        [
            "Line-level citation rules:",
            "- Every source block has an exact source id and document_id.",
            "- Every grounded line must cite one or more exact source id values.",
            "- chunk_id must be copied exactly from the source id attribute.",
            "- document_id must be copied exactly from the source document_id attribute.",
            "- evidence must be a verbatim span or figure from the cited source.",
            "- Do not cite chunk ids that are not present in retrieved_context.",
            "- Use grounded=false when no retrieved source supports a line.",
            "- Do not invent hours when support is missing.",
            "- For grounded=false lines, set hours to null and sources to an empty list.",
        ]
    )
