import argparse
import json


def main(argv=None):
    p = argparse.ArgumentParser(prog="notes")
    p.add_argument("text")
    args = p.parse_args(argv)
    with open("notes.json", "a", encoding="utf-8") as f:
        f.write(json.dumps({"text": args.text}) + "\n")


if __name__ == "__main__":
    main()
