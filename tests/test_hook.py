from idavenv.hook_template import (
    HOOK_END_MARKER,
    HOOK_START_MARKER,
    generate_hook_code,
    has_hook,
    inject_hook,
    remove_hook,
)


def test_generate_hook_code(tmp_path):
    venv_dir = tmp_path / "venv"
    code = generate_hook_code(venv_path=venv_dir)

    assert HOOK_START_MARKER in code
    assert HOOK_END_MARKER in code
    assert "_idapython_venv_initialized" in code
    assert "site.addsitedir" in code
    assert venv_dir.resolve().as_posix() in code


def test_inject_hook_new_file(tmp_path):
    target_file = tmp_path / "idapythonrc.py"
    venv_dir = tmp_path / "venv"

    assert not target_file.exists()
    changed = inject_hook(target_file, venv_dir)
    assert changed is True
    assert target_file.exists()

    content = target_file.read_text(encoding="utf-8")
    assert HOOK_START_MARKER in content
    assert HOOK_END_MARKER in content
    assert has_hook(target_file) is True


def test_inject_hook_preserves_existing_user_code(tmp_path):
    target_file = tmp_path / "idapythonrc.py"
    venv_dir = tmp_path / "venv"

    existing_code = "# User custom script\nprint('Hello from user idapythonrc!')\n"
    target_file.write_text(existing_code, encoding="utf-8")

    changed = inject_hook(target_file, venv_dir)
    assert changed is True

    content = target_file.read_text(encoding="utf-8")
    assert "Hello from user idapythonrc!" in content
    assert HOOK_START_MARKER in content
    assert HOOK_END_MARKER in content


def test_inject_hook_idempotent_update(tmp_path):
    target_file = tmp_path / "idapythonrc.py"
    venv1 = tmp_path / "venv1"
    venv2 = tmp_path / "venv2"

    inject_hook(target_file, venv1)
    content1 = target_file.read_text(encoding="utf-8")
    assert venv1.resolve().as_posix() in content1

    # Inject with new venv
    inject_hook(target_file, venv2)
    content2 = target_file.read_text(encoding="utf-8")
    assert venv2.resolve().as_posix() in content2
    assert venv1.resolve().as_posix() not in content2

    # Verify marker appears only once
    assert content2.count(HOOK_START_MARKER) == 1
    assert content2.count(HOOK_END_MARKER) == 1


def test_remove_hook(tmp_path):
    target_file = tmp_path / "idapythonrc.py"
    venv_dir = tmp_path / "venv"
    user_header = "# Header\nval = 42\n"
    target_file.write_text(user_header, encoding="utf-8")

    inject_hook(target_file, venv_dir)
    assert has_hook(target_file) is True

    removed = remove_hook(target_file)
    assert removed is True
    assert has_hook(target_file) is False

    remaining = target_file.read_text(encoding="utf-8")
    assert "val = 42" in remaining
    assert HOOK_START_MARKER not in remaining

    # Removing again returns False
    assert remove_hook(target_file) is False

    # Removing from non-existent file returns False
    non_existent = tmp_path / "does_not_exist.py"
    assert remove_hook(non_existent) is False


def test_hook_code_compiles_under_ast():
    import ast
    from pathlib import Path

    test_paths = [
        Path("/standard/posix/path/to/venv"),
        Path("C:/Program Files/IDA Pro/venv"),
        Path("C:\\Users\\runneradmin\\.idapro\\venv"),
        Path("/path with spaces and 中文/venv"),
    ]

    for p in test_paths:
        code = generate_hook_code(p)
        # Verify it compiles cleanly without any SyntaxError or bad escape
        parsed = ast.parse(code)
        assert parsed is not None
        compiled = compile(code, "<hook_test>", "exec")
        assert compiled is not None


def test_inject_hook_cleans_legacy_idavirtualenv_block(tmp_path):
    target_file = tmp_path / "idapythonrc.py"
    legacy_content = (
        "# >>> IDAPython Virtualenv Hook (managed by idavirtualenv) >>>\n"
        "# legacy hook code\n"
        "# <<< IDAPython Virtualenv Hook (managed by idavirtualenv) <<<\n"
        "print('user preserved')\n"
    )
    target_file.write_text(legacy_content, encoding="utf-8")

    assert has_hook(target_file) is True
    inject_hook(target_file, tmp_path / "new_venv")

    updated = target_file.read_text(encoding="utf-8")
    assert "managed by idavirtualenv" not in updated
    assert "managed by idavenv" in updated
    assert "print('user preserved')" in updated
