#!/bin/bash

# The first argument is a JSON string with the submodule paths and SHAs.
# Example of JSON argument: '{"org/repo1": "sha1", "org/repo2": "sha2"}'

set -e
set -o pipefail

submodules_json="$1"

# Validate the JSON input
if ! jq empty <<< "$submodules_json" ; then
    echo "Invalid JSON input."
    exit 1
fi

# Iterate over the submodule paths defined in the .gitmodules file
while read -r submodule_name; do
    echo "$submodule_name"
    submodule_path=$(git config --file .gitmodules --get "submodule.$submodule_name.path")
    submodule_repo=$(git config --file .gitmodules --get "submodule.$submodule_name.url" | awk -F'[/.]' '{print $(NF-2)"/"$(NF-1)}')

    # Find the SHA for the submodule from the JSON
    sha=$(echo "$submodules_json" | jq -r --arg repo "$submodule_repo" '.[$repo]')

    if [[ -z "$sha" || "$sha" == "null" ]]; then
        echo "No SHA specified for submodule $submodule_path ($submodule_repo), skipping."
    else
        echo "Checking out submodule $submodule_path ($submodule_repo) to SHA $sha."

        git -C "$submodule_path" fetch origin "$sha" && git -C "$submodule_path" checkout "$sha" || {
            echo "Failed to checkout submodule $submodule_path ($submodule_repo) to SHA $sha."
            exit 1
        }
    fi
done < <(git config --file .gitmodules --get-regexp 'submodule\..*\.path' | awk -F '.' '{ print $2 }')

echo "Submodule checkout complete."
