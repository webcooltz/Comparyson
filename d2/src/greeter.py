import logging
import sys


def greet(name, punctuation="!"):
    print(f"Hello, {name}{punctuation}")


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "world"
    logging.info("greeting %s", name)
    greet(name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
