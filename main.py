import logging
import argparse
import pathlib
import re
from dataclasses import dataclass
from svdsuite import Process

from svdconv.parser import parse_svdconv_output
from compare import Compare

LAST_SUCCESSFUL = {"vendor": "GigaDevice", "name": "GD32L23x_DFP", "version": "1.0.3", "svd_name": "GD32L23x"}

ACCEPTED_DIFFERENCES = [
    # multiple interrupts in one interrupt element
    {"vendor": "ELAN", "name": "eKTF7020_DFP", "version": "1.0.1", "svd_name": "eKTF7020"},
    #
    # multiple interrupts in one interrupt element
    {"vendor": "ELAN", "name": "eWD720_DFP", "version": "1.0.1", "svd_name": "eWD720"},
    #
    # svd content: <peripheral derivedFrom="DMA1"><name>DMA2</name><description/><groupName/>
    # SVDConv wrongly accepts <groupName/> as a valid group name and doesn't inherhit the real group name from DMA1
    {"vendor": "Geehy", "name": "APM32E1xx_DFP", "version": "1.0.0", "svd_name": "APM32E103xx"},
]


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


def is_accepted_difference(svd_meta: SVDMeta) -> bool:
    for accepted_diff in ACCEPTED_DIFFERENCES:
        if (
            accepted_diff["vendor"] == svd_meta.vendor
            and accepted_diff["name"] == svd_meta.name
            and accepted_diff["version"] == svd_meta.version
            and accepted_diff["svd_name"] == svd_meta.svd
        ):
            return True

    return False


def skip_to_untested(svd_meta_list: list[SVDMeta]) -> list[SVDMeta]:
    if "LAST_SUCCESSFUL" in globals():
        for index, svd_meta in enumerate(svd_meta_list):
            if (
                LAST_SUCCESSFUL["vendor"] == svd_meta.vendor
                and LAST_SUCCESSFUL["name"] == svd_meta.name
                and LAST_SUCCESSFUL["version"] == svd_meta.version
                and LAST_SUCCESSFUL["svd_name"] == svd_meta.svd
            ):
                return svd_meta_list[index + 1 :]

    return svd_meta_list


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        dest="svd_meta_list",
        help="path to single svd file or directory containing svd files",
        type=valid_svd_dir_or_file,
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    # skip all svd files until the last successful one if LAST_SUCCESSFUL is defined
    svd_meta_list = skip_to_untested(args.svd_meta_list)

    for svd_meta in svd_meta_list:
        logging.info("Processing %s", svd_meta.path)

        svdconv_peripherals = parse_svdconv_output(svd_meta.path)

        if svdconv_peripherals is None:
            logging.info(
                "Processing of %s was canceled because the file could not be parsed with svdconv\n\n", svd_meta.path
            )
            continue

        svdsuite_peripherals = Process.from_svd_file(svd_meta.path).get_processed_device().peripherals
        compare = Compare(svdconv_peripherals, svdsuite_peripherals)

        if not compare.compare():
            logging.error("Found differences between svdconv and svdsuite for %s", svd_meta.path)

            if not is_accepted_difference(svd_meta):
                raise SystemExit(1)

        logging.info("Finished processing %s\n\n", svd_meta.path)


if __name__ == "__main__":
    main()
