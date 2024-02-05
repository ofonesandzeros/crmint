#!/bin/bash
#
# Copyright 2023 Google Inc
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#!/bin/bash
set -e

function parse_command_line_arguments() {
  TARGET_BRANCH=$1
  RUN_COMMAND=$2
  COMMAND_OPTIONS=$3
  USE_VPC_FLAG=""
  CURRENT_DIR=$(pwd)

  if [[ "$4" == "--use_vpc" ]]; then
    USE_VPC_FLAG="--use_vpc"
  fi

  case "${RUN_COMMAND}" in
    --bundle)
      COMMAND="crmint bundle install ${USE_VPC_FLAG}"
      ;;
    *)
      echo "Unknown command: ${RUN_COMMAND}" >&2
      exit 2
      ;;
  esac
  if [[ ! -z "$COMMAND" ]]; then
    echo "Will run the following command after installing the CRMint command line"
    echo " ${COMMAND} ${COMMAND_OPTIONS}"
  fi
}

function clone_and_checkout_repository() {
  TARGET_REPO_URL="https://github.com/instant-bqml/crmint.git"
  TARGET_REPO_NAME="crmint"
  CLONE_DIR="$HOME/$TARGET_REPO_NAME"

  if [ -d "$CLONE_DIR" ]; then
    echo "Found existing directory for $TARGET_REPO_NAME"
    cd "$CLONE_DIR"

    CURRENT_REPO_URL=$(git config --get remote.origin.url)
    if [ "$CURRENT_REPO_URL" != "$TARGET_REPO_URL" ]; then
      echo "Switching remote URL from $CURRENT_REPO_URL to $TARGET_REPO_URL"
      git remote set-url origin "$TARGET_REPO_URL"
      git fetch --all --quiet
      git reset --hard origin/$TARGET_BRANCH
      git checkout $TARGET_BRANCH
      git pull --quiet --rebase
    else
      echo "Remote URL is already set to $TARGET_REPO_URL"
      git fetch --all --quiet
      git checkout $TARGET_BRANCH
      git reset --hard origin/$TARGET_BRANCH
      git pull --quiet --rebase
    fi
  else
    git clone "$TARGET_REPO_URL" "$CLONE_DIR"
    echo "Cloned $TARGET_REPO_NAME repository to your home directory: $HOME."
    cd "$CLONE_DIR"
    git checkout $TARGET_BRANCH
  fi
}

function install_command_line() {
  if [ ! -d .venv ]; then
    sudo apt-get install -y python3-venv
    python3 -m venv .venv
  fi

  . .venv/bin/activate
  pip install --quiet --upgrade "pip<23.0"
  pip install --quiet -e cli/
}

function add_wrapper_function_to_bashrc() {
  echo -e "\\nAdding a bash function to your $HOME/.bashrc file."

  cat <<EOF >>$HOME/.bashrc

# CRMint wrapper function.
# Automatically activates the virtualenv and makes the command
# accessible from all directories
function crmint {
  CURRENT_DIR=\$(pwd)
  cd \$HOME/crmint
  . .venv/bin/activate
  command crmint \$@ || return
  deactivate
  cd "\$CURRENT_DIR"
}
EOF
}

function run_command_line() {
  if [[ ! -z "$COMMAND" ]]; then
    hash -r
    eval "${COMMAND} ${COMMAND_OPTIONS}"
  else
    echo -e "\nSuccessfully installed the CRMint command-line."
    echo "You can use it now by typing: crmint --help"
    exec bash
  fi
}

# Main script execution
parse_command_line_arguments "$@"
clone_and_checkout_repository
install_command_line
add_wrapper_function_to_bashrc
cd "$CURRENT_DIR"
run_command_line
