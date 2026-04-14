"""Custom file toolkit for Mini Agent G4"""

from typing import Optional
from pathlib import Path

from agno.tools.file import FileTools as AgnoFileTools


class FileToolkit(AgnoFileTools):
    """Extended file toolkit with MiniAgent-specific features."""

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        enable_save_file: bool = True,
        enable_read_file: bool = True,
        enable_delete_file: bool = False,
        enable_list_files: bool = True,
        enable_search_files: bool = True,
        enable_read_file_chunk: bool = True,
        enable_replace_file_chunk: bool = True,
        enable_search_content: bool = True,
        all: bool = False,
        **kwargs,
    ):
        super().__init__(
            base_dir=base_dir,
            enable_save_file=enable_save_file,
            enable_read_file=enable_read_file,
            enable_delete_file=enable_delete_file,
            enable_list_files=enable_list_files,
            enable_search_files=enable_search_files,
            enable_read_file_chunk=enable_read_file_chunk,
            enable_replace_file_chunk=enable_replace_file_chunk,
            enable_search_content=enable_search_content,
            all=all,
            **kwargs,
        )