from rules.bare_except import detect_bare_except
from rules.inefficient_code import detect_inefficient_code
from rules.mutable_defaults import detect_mutable_defaults
from rules.sql_injection import detect_sql_injection
from rules.syntax_error import detect_syntax_error


def test_syntax_error_detected():
    code = 'def broken(:\n    return 1\n'
    findings = detect_syntax_error(code)
    assert len(findings) == 1
    assert findings[0].type == "Syntax Error"
    assert findings[0].severity == "High"
    assert findings[0].line == 1
    assert "parse" in findings[0].explanation


def test_syntax_error_line_and_snippet():
    code = 'x = [1, 2\nprint(x)\n'
    findings = detect_syntax_error(code)
    assert findings and findings[0].line == 1
    assert findings[0].code_snippet == "x = [1, 2"


def test_valid_code_no_syntax_error():
    assert detect_syntax_error('print("ok")\n') == []


def test_pipeline_reports_syntax_error_instead_of_skipping():
    from pipeline import analyze_code

    findings = analyze_code('def broken(:\n    return 1\n', "broken.py")
    assert any(f.type == "Syntax Error" for f in findings)
    assert findings[0].severity == "High"


def test_sql_injection_fstring():
    code = '''import sqlite3
conn = sqlite3.connect("db.sqlite")
cur = conn.cursor()
user_id = input("id: ")
cur.execute(f"SELECT * FROM users WHERE id = {user_id}")
'''
    findings = detect_sql_injection(code)
    assert len(findings) == 1
    assert findings[0].type == "SQL Injection"
    assert findings[0].severity == "Critical"
    assert findings[0].line == 5


def test_sql_injection_concatenation_via_variable():
    code = '''query = "SELECT * FROM users WHERE name = '" + name + "'"
cursor.execute(query)
'''
    findings = detect_sql_injection(code)
    assert len(findings) == 1
    assert findings[0].type == "SQL Injection"


def test_sql_injection_format_method():
    code = '''cursor.execute("SELECT * FROM users WHERE id = {}".format(user_id))
'''
    findings = detect_sql_injection(code)
    assert len(findings) == 1


def test_sql_injection_percent_format():
    code = '''cursor.execute("SELECT * FROM users WHERE id = %s" % user_id)
'''
    findings = detect_sql_injection(code)
    assert len(findings) == 1


def test_sql_injection_safe_parametrized():
    code = '''cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
'''
    findings = detect_sql_injection(code)
    assert findings == []


def test_sql_injection_safe_static():
    code = '''cursor.execute("SELECT * FROM users WHERE active = 1")
'''
    findings = detect_sql_injection(code)
    assert findings == []


def test_sql_injection_django_extra_keyword():
    code = '''qs = Model.objects.extra(where=[f"id = {user_id}"])
'''
    findings = detect_sql_injection(code)
    assert len(findings) == 1


def test_bare_except():
    code = "try:\n    x = 1 / 0\nexcept:\n    pass\n"
    findings = detect_bare_except(code)
    assert len(findings) == 1
    assert findings[0].type == "Bare Except"
    assert findings[0].severity == "Medium"


def test_except_exception_pass_swallowed():
    code = "try:\n    f()\nexcept Exception:\n    pass\n"
    findings = detect_bare_except(code)
    assert findings
    assert findings[0].type == "Unhandled Exception"


def test_specific_except_not_flagged():
    code = "try:\n    f()\nexcept ValueError:\n    print('bad')\n"
    assert detect_bare_except(code) == []


def test_mutable_default_list():
    code = "def process(items=[]):\n    items.append(1)\n    return items\n"
    findings = detect_mutable_defaults(code)
    assert len(findings) == 1
    assert "None" in findings[0].suggested_fix


def test_mutable_default_dict():
    code = "def cache_store(cache={}):\n    return cache\n"
    findings = detect_mutable_defaults(code)
    assert len(findings) == 1
    assert findings[0].type == "Mutable Default Argument"


def test_no_mutable_default_with_none():
    code = "def process(items=None):\n    return items\n"
    assert detect_mutable_defaults(code) == []


def test_loop_string_concat_augassign():
    code = '''s = ""
for i in range(10):
    s += str(i)
'''
    findings = detect_inefficient_code(code)
    types = [f.type for f in findings]
    assert "Inefficient Code" in types


def test_loop_string_concat_assign():
    code = '''result = ""
for item in items:
    result = result + str(item)
'''
    findings = detect_inefficient_code(code)
    assert any(f.type == "Inefficient Code" for f in findings)


def test_n_plus_one_query_in_loop():
    code = '''for user in users:
    profile = db.execute("SELECT * FROM profile WHERE user_id = ?", user.id)
'''
    findings = detect_inefficient_code(code)
    assert any(f.type == "N+1 Query Pattern" for f in findings)


def test_list_materialization_in_for():
    code = '''for x in list(range(100)):
    print(x)
'''
    findings = detect_inefficient_code(code)
    assert any(f.type == "Inefficient Code" for f in findings)


def test_dict_get_in_loop_not_n_plus_one():
    code = '''for frame in frames:
    name = frame.f_globals.get("__name__")
    mapping = base.__dict__.get("__abstract__", False)
'''
    findings = detect_inefficient_code(code)
    assert all(f.type != "N+1 Query Pattern" for f in findings)