import argparse
import json
import shutil
import sys
from pathlib import Path


SOURCE_DIR: Path = Path(__file__).resolve().parent.parent
PACKAGES: tuple[str, ...] = ("scheduler", "awsutil")
LAMBDA_HANDLER_FILE: Path = Path(__file__).parent.joinpath("lambdahandler.py")
IGNORED = shutil.ignore_patterns("__pycache__", "*.pyc")


def loadGroups(inputDir: Path) -> dict:
    groups = json.loads(inputDir.joinpath("groups.json").read_text(encoding="utf-8"))
    if not groups.get("groups"):
        raise ValueError("groups.json: 'groups' must be a non-empty list")
    for group in groups["groups"]:
        if not group.get("functions"):
            raise ValueError(f"groups.json: group {group.get('name')!r} has no functions")
        for function in group["functions"]:
            for key in ("name", "input", "priority"):
                if key not in function:
                    raise ValueError(f"groups.json: missing {key!r} in {function} of group {group.get('name')!r}")
            if not inputDir.joinpath(function["name"]).is_dir():
                raise ValueError(f"groups.json: no source directory for {function['name']!r}")
    return groups


def generateComposite(group: dict, inputDir: Path, compositeDir: Path) -> None:
    for function in group["functions"]:
        shutil.copytree(inputDir.joinpath(function["name"]), compositeDir.joinpath(function["name"]), ignore=IGNORED)
    for package in PACKAGES:
        shutil.copytree(SOURCE_DIR.joinpath(package), compositeDir.joinpath(package), ignore=IGNORED)

    config = {"functions": group["functions"]}
    compositeDir.joinpath("config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    shutil.copyfile(LAMBDA_HANDLER_FILE, compositeDir.joinpath("lambda_function.py"))


def generate(inputDir: Path, outputDir: Path) -> None:
    groups = loadGroups(inputDir)

    shutil.rmtree(outputDir, ignore_errors=True)
    outputDir.joinpath("source").mkdir(parents=True)
    outputDir.joinpath("package").mkdir()  # opentofu zips

    for index, group in enumerate(groups["groups"]):
        compositeDir = outputDir.joinpath("source", f"composite-function-{index + 1}")
        compositeDir.mkdir()
        generateComposite(group, inputDir, compositeDir)
        print(f"Generated '{compositeDir.name}' with {len(group['functions'])} atomic function(s)")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="generator",
        description="The Generator assembles the composite functions from the provided source codes and the groups.json file"
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        required=True,
        help="Path of the application directory that contains the source code of the functions and the JSON file"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Root of the output directory (composite sources under <output>/source/, zip packages under <output>/package/)"
    )
    args = parser.parse_args()

    try:
        generate(args.input, args.output)
    except (OSError, ValueError, KeyError) as error:
        print(f"\n{error}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
