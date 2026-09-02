import argparse
import asyncio

from pipeline import answer_question
from settings import load_settings


def main() -> None:
    """Run a domain-limited search question from the command line."""
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    args = parser.parse_args()
    response = asyncio.run(answer_question(args.question, load_settings()))
    print(response.answer)
    if response.sources:
        print("\nSources:")
        for source in response.sources:
            print(f"- {source}")
    if response.follow_ups:
        print("\nNext questions:")
        for follow_up in response.follow_ups:
            print(f"- {follow_up}")
