#!/usr/bin/python3

import argparse
import logging
import os
import re
import subprocess
import shutil
from typing import Optional

import chardet

re_spaces = re.compile(r"\s")


def detect_encoding_and_read(filename: str, encoding_guess_length: int) -> str:
    with open(filename, "rb") as fi_b:
        result = chardet.detect(fi_b.read(encoding_guess_length))
    read_str = ""
    if result["encoding"] is not None:
        with open(filename, "r", encoding=result["encoding"]) as fi_t:
            read_str = fi_t.read()
    return read_str


def print_search_result(pattern, string, hint):
    for i, match in enumerate(re.finditer(pattern, string)):
        line_number = string.count("\n", 0, match.start()) + 1
        column_number = match.start() - string.rfind("\n", 0, match.start())
        first_space_after_substring_m = re_spaces.search(string, match.end())
        first_space_after_substring = (
            first_space_after_substring_m.end()
            if first_space_after_substring_m is not None
            else -1
        )
        first_enter_after_substring = string.find("\n", match.end())
        word = string[
            match.end():(
                first_space_after_substring
                if first_space_after_substring < first_enter_after_substring
                else first_enter_after_substring
            )
        ]
        if i == 0:
            print("\033[1m%s\033[0m" % hint)
        print(
            "\033[1;32m%d\033[0m:\033[1;32m%d\033[0m\t\033[31m%s\033[0m%s"
            % (line_number, column_number, pattern, word)
        )


def advanced_search(
    directory: str,
    substring: str,
    encoding_guess_length: int,
    auto_delete_tmp: bool = True,
    tika_path: Optional[str] = None,
    deep_search: bool = False,
):
    logging.disable(logging.ERROR)
    if deep_search:
        import patoolib
    for root, dirs, files in os.walk(directory):
        for filename in files:
            real_filename = os.path.join(root, filename)
            read_str = ""
            if deep_search and patoolib.is_archive(real_filename):
                # archive
                extracted_dir = os.path.join(root, ".tmp", filename)
                try:
                    patoolib.extract_archive(
                        os.path.join(root, real_filename), outdir=extracted_dir
                    )
                except Exception as e:
                    print(str(e))
                advanced_search(
                    tika_path, extracted_dir, substring, encoding_guess_length
                )
                if auto_delete_tmp:
                    shutil.rmtree(extracted_dir)
            elif tika_path is not None:
                cp = subprocess.run(
                    ["java", "-jar", tika_path, "-t", real_filename],
                    capture_output=True,
                    text=True,
                )
                read_str = cp.stdout
                if cp.stderr is not None:
                    read_str += detect_encoding_and_read()
            else:
                read_str = detect_encoding_and_read()

            print_search_result(substring, read_str, filename)

    if auto_delete_tmp and os.path.exists(os.path.join(directory, ".tmp")):
        os.rmdir(os.path.join(directory, ".tmp"))
    logging.disable(logging.NOTSET)


arg_parser = argparse.ArgumentParser(description="ack extended")
arg_parser.add_argument("directory")
arg_parser.add_argument("substring")
arg_parser.add_argument("-e", "--encoding-guess-length", type=int, default=256)
arg_parser.add_argument("-c", "--auto-clean", action="store_true")
arg_parser.add_argument(
    "-t", "--tika-path", help="use Tika to support more file types"
)
arg_parser.add_argument(
    "-d",
    "--deep-search",
    help="use Patool to support archives",
    action="store_true",
)
args = arg_parser.parse_args()
advanced_search(
    args.directory,
    args.substring,
    args.encoding_guess_length,
    args.auto_clean,
    args.tika_path,
    args.deep_search,
)
