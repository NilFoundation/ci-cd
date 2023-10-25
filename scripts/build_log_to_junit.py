import re
import sys
import argparse
from junit_xml import TestSuite, TestCase


def generate_junit_report(input_lines, output_file):
    # Patterns to match build successes and failures
    success_pattern = re.compile(r"Built target (.+)")
    failure_pattern = re.compile(
        r"make\[\d+\]: Target [`'](.+)[`'] not remade because of errors."
    )

    # Lists to store successful and failed builds
    successful_builds = []
    failed_builds = []

    # Process each line in the input
    for line in input_lines:
        success_match = success_pattern.search(line)
        failure_match = failure_pattern.search(line)

        if success_match:
            successful_builds.append(success_match.group(1))
        elif failure_match:
            failed_builds.append(failure_match.group(1))

    # Create test cases for JUnit
    test_cases = []

    for success in successful_builds:
        if success.startswith("_cm_internal_tests-"):
            # fake internal target from CMTest module added here:
            # https://github.com/boost-cmake/bcm/blob/5b8e981c4990aae7204cfc1c00a2fc18fe2e96a3/share/bcm/cmake/BCMTest.cmake#L54-L60
            continue
        tc = TestCase("Build Success", success)
        test_cases.append(tc)

    for failure in failed_builds:
        # e.g. libs/marshalling/multiprecision/test/CMakeFiles/marshalling_integral_test.dir/build
        if not failure.endswith("build"):
            # e.g. libs/marshalling/multiprecision/all
            continue

        target_name = failure.split("/")[-2].split(".")[0]
        tc = TestCase("Build Failure", target_name)
        tc.add_failure_info("Build failed for target: " + target_name)
        test_cases.append(tc)

    # Create a test suite and add test cases
    ts = TestSuite("Build Results", test_cases)

    # Generate JUnit XML report
    with open(output_file, "w") as f:
        TestSuite.to_file(f, [ts], prettyprint=True)

    print(f"JUnit report generated: {output_file}")


def main():
    # Initialize argument parser
    parser = argparse.ArgumentParser(
        description="Generate JUnit report from build output."
    )
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        help="Path to the file containing the build output. If not provided, the script will read from stdin.",
    )
    parser.add_argument(
        "-o", "--output", type=str, help="Output file name for the JUnit report."
    )

    # Parse the arguments
    args = parser.parse_args()

    # Read input from file or stdin
    input_lines = []
    if args.file:
        with open(args.file, "r") as file:
            input_lines = file.readlines()
    else:
        input_lines = sys.stdin.readlines()

    # Generate JUnit report
    generate_junit_report(input_lines, args.output)


if __name__ == "__main__":
    main()
