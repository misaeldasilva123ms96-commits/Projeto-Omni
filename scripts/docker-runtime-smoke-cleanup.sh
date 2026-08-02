#!/usr/bin/env bash

omni_finalize_cleanup() {
  local original_status="$1"
  local teardown_command="$2"
  local verify_command="$3"
  local image_command="$4"
  local cleanup_failed=0

  if ! "$teardown_command"; then cleanup_failed=1; fi
  if ! "$verify_command"; then cleanup_failed=1; fi
  if ! "$image_command"; then cleanup_failed=1; fi

  if (( original_status != 0 )); then
    return "$original_status"
  fi
  if (( cleanup_failed != 0 )); then
    return 1
  fi
  return 0
}

omni_finalize_failed_smoke() {
  local original_status="$1"
  local diagnostics_command="$2"
  local teardown_command="$3"
  local verify_command="$4"
  local image_command="$5"

  if ! "$diagnostics_command"; then
    : # Publication failure is withheld; the original smoke status remains authoritative.
  fi
  omni_finalize_cleanup "$original_status" "$teardown_command" "$verify_command" "$image_command"
}
