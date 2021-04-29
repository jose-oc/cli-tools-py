#!/usr/bin/env python3
"""
Move duplicated files.
    Sort files in a directory by size,
    group files by size and compare them by content.
    Then move the files duplicated keeping the one with longest filename.
"""
import argparse
import filecmp
import logging
import os
import shutil
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from pprint import pformat

log = logging.getLogger('clean_identical_files')


def configure_logger(silent, verbose):
    if silent:
        basic_level = logging.ERROR
    else:
        basic_level = logging.DEBUG if verbose else logging.INFO

    fmt = '[%(asctime)-15s] [%(levelname)s] %(name)s: %(message)s'
    logging.basicConfig(format=fmt, level=basic_level)


def add_photo_into_map_by_filesize(base_names, entry):
    if isinstance(entry, str):
        fsize = Path(entry).stat().st_size
        path = entry
    else:
        fsize = os.path.getsize(entry.path)
        path = entry.path

    if fsize not in base_names:
        base_names[fsize] = {path}
    else:
        base_names[fsize].add(path)


def define_files_map(directory):
    """
    :param directory: directory to be analyzed recursively
    :return: a map with the files sorted by file size
    """
    base_names = {}
    for root, dirs, files in os.walk(directory):
        for file in files:
            entry = os.fspath( os.path.join(root, file) )
            if entry.endswith('.arw') or entry.endswith('.nef') or entry.endswith('.jpg') or entry.endswith('.tif'):
                add_photo_into_map_by_filesize(base_names, entry)
    return base_names


def group_equal_files(photo_set_original):
    """
    Given a list of photos, analyze them and group the files that are identical to the first file in the list.
    returns a list of files that are identical to the first one, including this one
    """
    if len(photo_set_original) <= 0:
        return set()

    # photo_list = sorted(photo_set_original, reverse=True)
    photo_set = deepcopy(photo_set_original)
    photo_selected = photo_set.pop()
    identical_photo_set = {photo_selected}
    for photo_candidate in photo_set:
        if filecmp.cmp(photo_selected, photo_candidate, shallow=False):
            identical_photo_set.add(photo_candidate)
    return identical_photo_set


def group_all_identical_photos(photos_map_by_basename):
    identical_photos_map = {}
    for k, group_photos in photos_map_by_basename.items():
        identical_photos_map[k] = list()
        group_photos_copy = deepcopy(group_photos)
        while group_photos_copy:
            group_of_identical_photos = group_equal_files(group_photos_copy)
            identical_photos_map[k].append(group_of_identical_photos)
            group_photos_copy.difference_update(group_of_identical_photos)
    return identical_photos_map


def move_file_list(files_to_be_moved, destination, num_files_moved, dry_run):
    for f in files_to_be_moved:
        try:
            if os.path.exists(f):
                num_files_moved = num_files_moved + 1
                if dry_run:
                    log.debug(f'-> File {f} to be moved')
                else:
                    moved = shutil.move(f, destination)
                    log.debug(f'-> File moved to {moved}')
        except Exception as e:
            log.error(f'!! Failure moving file {f}', e)
    return num_files_moved


def move_identical_files(identical_photos_dict, target_directory, dry_run):
    n_moved = 0
    if not os.path.exists(target_directory):
        os.makedirs(target_directory)

    for k, v in identical_photos_dict.items():
        for identical_photos_set in v:
            if len(identical_photos_set) > 1:
                move_longest_filename = True
                identical_photos_sorted = sorted(identical_photos_set, reverse=move_longest_filename)
                exclude_one_image_to_not_delete_it(identical_photos_sorted)
                n_moved = move_file_list(identical_photos_sorted, target_directory, n_moved, dry_run)
    return n_moved


def exclude_one_image_to_not_delete_it(identical_photos_sorted):
    identical_photos_sorted.pop()


def clean_identical_files(directory, target_directory, dry_run):
    log.info(f'Analyzing files from directory {directory}')
    if target_directory:
        log.info(f'Duplicated files will be moved to {target_directory}')

    map_of_files_with_same_size = define_files_map(directory)
    identical_photos = group_all_identical_photos(map_of_files_with_same_size)
    log.debug(pformat(identical_photos))

    log.debug('\n\n\n...Moving identical files...\n')
    num_files_duplicated = move_identical_files(identical_photos, target_directory, dry_run)
    log.info(f'There were {num_files_duplicated} files duplicated.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='clean_identical_files',
                                     description='Deduplicate identical image files that live in the same directory. '
                                                 'It works recursively moving the duplicated files to another folder.',
                                     epilog='Example of usage: '
                                            'python clean_identical_files.py --directory /path/'
                                     )
    parser.version = '0.1'
    parser.add_argument('-d', '--directory',
                        required=False,
                        type=str,
                        default='.',
                        help='Path to the directories to the files to be removed. Defaults to currect directory.')
    parser.add_argument('-t', '--target-directory',
                        required=False,
                        type=str,
                        default=tempfile.mkdtemp(prefix='duplicated_files_', dir=tempfile.tempdir),
                        help='When this parameter is provided the duplicated files are not removed '
                             'but moved to this path.')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('-V', '--version',
                        action='version')
    logging_args = parser.add_mutually_exclusive_group(required=False)
    logging_args.add_argument('-v', '--verbose', action='store_true')
    logging_args.add_argument('-s', '--silent', action='store_true')

    args = parser.parse_args()

    configure_logger(args.silent, args.verbose)

    try:
        sys.exit(
            clean_identical_files(args.directory, args.target_directory, args.dry_run)
        )
    except Exception as e:
        log.exception(e)
        sys.exit(1)
