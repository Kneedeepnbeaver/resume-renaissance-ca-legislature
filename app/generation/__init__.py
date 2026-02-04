"""Generation module for resumes and cover letters."""
from .prompts import CA_LEG_WRITING_RULES, build_resume_prompt, build_cover_letter_prompt
from .outputs import save_output, get_output_filename, get_output_filename_with_ext, load_history

__all__ = [
    "CA_LEG_WRITING_RULES",
    "build_resume_prompt",
    "build_cover_letter_prompt",
    "save_output",
    "get_output_filename",
    "get_output_filename_with_ext",
    "load_history",
]
