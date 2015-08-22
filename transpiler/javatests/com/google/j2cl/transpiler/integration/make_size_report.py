#!/usr/bin/python2.7
#
# Copyright 2015 Google Inc. All Rights Reserved.

"""Reports optimized size changes caused by the current CL."""


import getpass
import os
import time


import repo_util


# pylint: disable=global-variable-not-assigned
MANAGED_GOOGLE3_PATH = repo_util.MANAGED_GOOGLE3_PATH


def find_last_stats(stat_lines, synced_to_cl):
  """Returns the opt size in the highest CL before the current sync cl."""
  last_optimized_size = 0

  for stat_line in stat_lines:
    cl, optimized_size = stat_line.split("\t")
    cl = int(cl)
    optimized_size = int(optimized_size)

    if cl > synced_to_cl:
      break
    else:
      last_optimized_size = optimized_size

  return last_optimized_size


def make_size_report():
  """Compare current test sizes and generate a report."""
  size_report_file = open(
      os.path.join(
          os.path.dirname(__file__), "size_report.txt"),
      "w+")

  synced_to_cl = repo_util.compute_synced_to_cl()

  size_report_file.write("Integration tests optimized size report:\n")
  size_report_file.write("**************************************\n")
  size_report_file.write("Generated by %s at %s.\n" %
                         (getpass.getuser(), time.strftime("%c")))

  size_report_file.write("Synced @%s.\n" % synced_to_cl)

  print "  Collecting original optimized sizes."
  repo_util.build_optimized_tests(cwd=MANAGED_GOOGLE3_PATH)
  original_js_files_by_test_name = (
      repo_util.get_js_files_by_test_name(cwd=MANAGED_GOOGLE3_PATH))
  print "  Collecting modified optimized sizes."
  repo_util.build_optimized_tests()
  modified_js_files_by_test_name = repo_util.get_js_files_by_test_name()

  print "  Comparing results."
  # Collect all test names
  all_test_names = set()
  all_test_names.update(original_js_files_by_test_name.keys())
  all_test_names.update(modified_js_files_by_test_name.keys())
  all_test_names = sorted(list(all_test_names))

  original_total_size = 0
  modified_total_size = 0
  optimized_size_change_count = 0
  all_reports = []
  new_reports = []
  shrinkage_reports = []
  expansion_reports = []

  for test_name in all_test_names:
    original_js_file = original_js_files_by_test_name.get(test_name)
    modified_js_file = modified_js_files_by_test_name.get(test_name)

    if original_js_file:
      original_js_file = MANAGED_GOOGLE3_PATH + "/" + original_js_file

    original_optimized_size = os.path.getsize(
        original_js_file) if original_js_file else -1
    modified_optimized_size = os.path.getsize(
        modified_js_file) if modified_js_file else -1

    # If this is a pre-existing test
    if original_optimized_size >= 0:
      # Log it's prexisting size
      original_total_size += original_optimized_size
      # And if an updated size exists then
      if modified_optimized_size >= 0:
        # Log that too
        modified_total_size += modified_optimized_size

    # If the original optimized JS file exists
    if original_optimized_size >= 0:
      # If the modified optimized JS file exists
      if modified_optimized_size >= 0:
        # Both files exist, so compare their sizes.
        if modified_optimized_size > original_optimized_size:
          optimized_size_change_count += 1
          increased_percent = (
              modified_optimized_size / float(original_optimized_size) - 1)
          increased_percent *= 100
          message = (
              "  '%s' %s->%s bytes (+%2.2f%%)\n" %
              (test_name, original_optimized_size, modified_optimized_size,
               increased_percent))
          all_reports.append(message)
          expansion_reports.append((increased_percent, message))
        elif modified_optimized_size < original_optimized_size:
          optimized_size_change_count += 1
          decreased_percent = (
              1 - modified_optimized_size / float(original_optimized_size))
          decreased_percent *= 100
          message = (
              "  '%s' %s->%s bytes (-%2.2f%%)\n" %
              (test_name, original_optimized_size, modified_optimized_size,
               decreased_percent))
          all_reports.append(message)
          shrinkage_reports.append((decreased_percent, message))
        else:
          message = ("  '%s' %s bytes (unchanged)\n" %
                     (test_name, modified_optimized_size))
          all_reports.append(message)
    else:
      if modified_optimized_size >= 0:
        # The original optimized JS file doesn't exist and the
        # modified one does, this is a new result.
        optimized_size_change_count += 1
        message = "  '%s' is %s bytes\n" % (test_name, modified_optimized_size)
        all_reports.append(message)
        new_reports.append(message)

  # Keep a maximum of 4 of the largest shrinkages.
  shrinkage_reports = (
      sorted(shrinkage_reports, key=lambda report: report[0], reverse=True)
      [0: 4])
  # Keep a maximum of 4 of the largest expansions.
  expansion_reports = (
      sorted(expansion_reports, key=lambda report: report[0], reverse=True)
      [0: 4])

  size_report_file.write(
      "There are %s size changes.\n" % optimized_size_change_count)

  if modified_total_size != original_total_size:
    total_percent = (
        modified_total_size / float(original_total_size)) * 100
    size_report_file.write(
        "Total size (of already existing tests) "
        "changed from %s to %s bytes (100%%->%2.2f%%).\n" %
        (original_total_size, modified_total_size, total_percent))
  else:
    size_report_file.write(
        "Total size (of already existing tests) did not change.\n")

  size_report_file.write("\n")
  size_report_file.write("\n")
  size_report_file.write("New reports:\n")
  size_report_file.write("**************************************\n")
  if new_reports:
    for new_report in new_reports:
      size_report_file.write(new_report)
  else:
    size_report_file.write("  none\n")

  size_report_file.write("\n")
  size_report_file.write("\n")
  size_report_file.write("Shrinkage report highlights:\n")
  size_report_file.write("**************************************\n")
  if shrinkage_reports:
    for shrinkage_report in shrinkage_reports:
      size_report_file.write(shrinkage_report[1])
  else:
    size_report_file.write("  none\n")

  size_report_file.write("\n")
  size_report_file.write("\n")
  size_report_file.write("Expansion report highlights:\n")
  size_report_file.write("**************************************\n")
  if expansion_reports:
    for expansion_report in expansion_reports:
      size_report_file.write(expansion_report[1])
  else:
    size_report_file.write("  none\n")

  size_report_file.write("\n")
  size_report_file.write("\n")
  size_report_file.write("All reports:\n")
  size_report_file.write("**************************************\n")
  if all_reports:
    for all_report in all_reports:
      size_report_file.write(all_report)
  else:
    size_report_file.write("  none\n")
  size_report_file.close()
  print "  Closing report (%s)" % size_report_file.name


def main():
  print "Generating the size change report:"

  repo_util.managed_repo_validate_environment()
  make_size_report()


main()
