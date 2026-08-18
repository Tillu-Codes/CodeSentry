from rules.bare_except import detect_bare_except
from rules.inefficient_code import detect_inefficient_code
from rules.mutable_defaults import detect_mutable_defaults
from rules.sql_injection import detect_sql_injection

ALL_RULES = [
    detect_sql_injection,
    detect_bare_except,
    detect_mutable_defaults,
    detect_inefficient_code,
]