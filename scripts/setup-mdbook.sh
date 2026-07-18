#!/bin/sh
# Install the mdBook toolchain (Rust binaries) used to build the documentation.
# Versions are pinned for reproducibility.
set -ex

MDBOOK_VERSION=0.4.52
MDBOOK_ADMONISH_VERSION=1.20.0
MDBOOK_MERMAID_VERSION=0.16.0
MDBOOK_LINKCHECK_VERSION=0.7.7

if ! command -v cargo >/dev/null 2>&1; then
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
  . "$HOME/.cargo/env"
fi

export PATH="$HOME/.cargo/bin:$PATH"

cargo install mdbook --version "${MDBOOK_VERSION}" --locked
cargo install mdbook-admonish --version "${MDBOOK_ADMONISH_VERSION}"
cargo install mdbook-mermaid --version "${MDBOOK_MERMAID_VERSION}"
cargo install mdbook-linkcheck --version "${MDBOOK_LINKCHECK_VERSION}"

mdbook --version
mdbook-admonish --version
mdbook-mermaid --version
mdbook-linkcheck --version
