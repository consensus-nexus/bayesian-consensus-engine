"""CLI entrypoint."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="bayesian-engine")
    parser.add_argument("--input", help="Path to JSON input file")
    parser.add_argument("--dry-run", action="store_true", help="Compute output without DB writes")
    parser.parse_args()
    print("Bayesian Engine scaffold is ready.")


if __name__ == "__main__":
    main()
