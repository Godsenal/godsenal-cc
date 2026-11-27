import sys

from src.members.importer import import_members

if __name__ == "__main__":
    for m in import_members(sys.argv[2], sys.argv[1]):
        print(f"{m['id']}\t{m['name']}")
