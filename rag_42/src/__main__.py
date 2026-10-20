"""Entry point: run python -m src <command> [options]"""
import fire
from src import cli

if __name__ == "__main__":
    fire.Fire({"index": cli.index})
