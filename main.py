import logging
import argparse
import pathlib
import warnings
import re
from dataclasses import dataclass
from svdsuite import Process, ParserWarning

from svdconv.parser import parse_svdconv_output
from compare import Compare


@dataclass
class SVDMeta:
    path: str
    vendor: str
    name: str
    version: str
    svd: str


def valid_svd_dir_or_file(arg: str) -> list[SVDMeta]:
    abs_path = pathlib.Path(arg).absolute()

    svd_paths: list[str] = []
    if abs_path.is_dir():
        svd_paths = [file.absolute().as_posix() for file in abs_path.rglob("*.svd")]

    if abs_path.is_file() and abs_path.suffix == ".svd":
        svd_paths = [abs_path.absolute().as_posix()]

    if not svd_paths:
        raise argparse.ArgumentTypeError("given path is not valid or does not contain any svd files")

    svd_meta: list[SVDMeta] = []
    for svd_path in svd_paths:
        pattern = r"^.*/(?P<vendor>[^/.]+)\.(?P<name>[^/.]+)\.(?P<version>[^/]+)/(?P<svd_name>[^/]+)\.svd$"

        match = re.match(pattern, svd_path)
        if match:
            vendor = match.group("vendor")
            name = match.group("name")
            version = match.group("version")
            svd_name = match.group("svd_name")

            svd_meta.append(SVDMeta(path=svd_path, vendor=vendor, name=name, version=version, svd=svd_name))
        else:
            raise argparse.ArgumentTypeError(f"can't extract vendor, name, version and svd name from {svd_path}")

    return svd_meta


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        dest="svd_meta_list",
        help="path to single svd file or directory containing svd files",
        type=valid_svd_dir_or_file,
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    for svd_meta in args.svd_meta_list:
        logging.info("Processing %s", svd_meta.path)

        svdconv_peripherals = parse_svdconv_output(svd_meta.path)

        if svdconv_peripherals is None:
            logging.info(
                "Processing of %s was canceled because the file could not be parsed with svdconv\n\n", svd_meta.path
            )
            continue

        # Suppress ParserWarning
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=ParserWarning, module="svdsuite.parse")
            svdsuite_peripherals = Process.from_svd_file(svd_meta.path).get_processed_device().peripherals

        compare = Compare(svdconv_peripherals, svdsuite_peripherals)

        if not compare.compare():
            logging.error("Found differences between svdconv and svdsuite for %s", svd_meta.path)
            raise SystemExit(1)

        logging.info("Finished processing %s\n\n", svd_meta.path)


if __name__ == "__main__":
    main()
