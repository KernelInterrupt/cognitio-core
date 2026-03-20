LOCKED_START = "% === LOCKED START ==="
LOCKED_END = "% === LOCKED END ==="
EDITABLE_START = "% === EDITABLE START ==="
EDITABLE_END = "% === EDITABLE END ==="

DEFAULT_TEX_TEMPLATE = f"""{LOCKED_START}
\\documentclass{{{{article}}}}
\\usepackage{{{{amsmath}}}}
\\newcommand{{{{\\annotationtype}}}}[1]{{{{}}}}
\\newcommand{{{{\\target}}}}[1]{{{{}}}}
\\newcommand{{{{\\language}}}}[1]{{{{}}}}
\\begin{{{{document}}}}
\\annotationtype{{{{intuition}}}}
\\target{{{{target_node_id}}}}
\\language{{{{zh}}}}
{LOCKED_END}
{EDITABLE_START}
这里写批注内容。
{EDITABLE_END}
{LOCKED_START}
\\end{{{{document}}}}
{LOCKED_END}
"""
