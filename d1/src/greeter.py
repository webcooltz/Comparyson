import sys


def greet(name):
    print("Hello, " + name)


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "world"
    greet(name)
    return 0


if __name__ == "__main__":
    main()
