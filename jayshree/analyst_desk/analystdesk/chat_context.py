"""Conversation context helpers for the baseline research chat."""

from collections.abc import Mapping, Sequence


def build_chat_question(
    question: str,
    question_mode: str,
    conversation_context: Sequence[Mapping[str, str]] | None,
) -> str:
    if question_mode == "new":
        return question
    if question_mode != "follow_up":
        raise ValueError("Choose either a new question or a follow-up question.")
    if not conversation_context:
        raise ValueError("Ask a new question before asking a follow-up.")

    context_lines = [
        f"Analyst: {turn['question']}\nAssistant: {turn['answer'][:1200]}"
        for turn in conversation_context[-3:]
    ]
    return (
        "Earlier conversation (use only to resolve references; verify the answer "
        "using the retrieved passages and EDGAR numbers):\n"
        + "\n".join(context_lines)
        + f"\nCurrent follow-up question: {question}"
    )
