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
        with open(filename, "r", encoding=result["encoding"], errors="ignore") as fi_t:
            read_str = fi_t.read()
    return read_str if read_str else ""


def print_search_result(pattern: str, string: str, hint: str) -> None:
    for i, match in enumerate(re.finditer(pattern, string)):
        if i == 0:
            print("\n\033[1m%s\033[0m" % hint)
        line_number = string.count("\n", 0, match.start()) + 1
        enter_before = string.rfind("\n", 0, match.start())
        enter_after = string.find("\n", match.end())
        column_number = match.start() - enter_before
        first_space_after_substring_m = re_spaces.search(string, match.end() + 15)
        first_space_after_substring = (
            first_space_after_substring_m.end()
            if first_space_after_substring_m is not None
            else -1
        )
        word_after = string[
            match.end():(
                first_space_after_substring
                if first_space_after_substring < enter_after
                else enter_after
            )
        ]
        if len(word_after) > 15:
            word_after = word_after[:16] + "..."
        first_space_before_substring_m = re_spaces.search(string, 0, match.start() - 15)
        first_space_before_substring = (
            first_space_before_substring_m.start()
            if first_space_before_substring_m is not None
            else 0
        )
        word_before = string[
            (
                first_space_before_substring
                if first_space_before_substring > enter_before
                else enter_before
            ):match.start()
        ]
        if len(word_before) > 15:
            word_before = "..." + word_before[-15:]
        joint_str = "\033[1;32m%d\033[0m:\033[1;32m%d\033[0m\t%s\033[31m%s\033[0m%s" \
            % (line_number, column_number, word_before, pattern, word_after)
        print(joint_str.replace("\n", ""))


def advanced_search(
    directory: str,
    substring: str,
    encoding_guess_length: int,
    auto_delete_tmp: bool = True,
    tika_path: Optional[str] = None,
    deep_search: bool = False,
) -> None:
    print('walking "%s" | grep "%s"' % (directory, substring))
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
                    encoding="utf-8",
                    text=True,
                )
                read_str = cp.stdout
            else:
                read_str = detect_encoding_and_read(real_filename, encoding_guess_length)

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
