#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os


def resolve_path_from_script(script_file: str, filename: str) -> str:
    """Resolve a file path relative to the current script file."""
    script_dir = os.path.dirname(os.path.abspath(script_file))
    return os.path.join(script_dir, filename)