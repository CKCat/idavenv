import pytest

from idavenv.cli import main


def test_cli_help(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "IDAPython virtualenv" in captured.out


def test_cli_init_and_info(tmp_path, capsys, monkeypatch):
    ida_dir = tmp_path / "cli_ida"
    ida_dir.mkdir()
    monkeypatch.setenv("IDAUSR", str(ida_dir))

    # Run init
    exit_code = main(["init", "--backend", "builtin", "--ida-dir", str(ida_dir)])
    assert exit_code == 0

    # Run info
    exit_code = main(["info", "--ida-dir", str(ida_dir)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "IDA User Directory" in captured.out
    assert "Hook Installed" in captured.out
    assert "Yes" in captured.out


def test_cli_uninstall(tmp_path, capsys):
    ida_dir = tmp_path / "cli_ida"
    ida_dir.mkdir()

    main(["init", "--backend", "builtin", "--ida-dir", str(ida_dir)])
    exit_code = main(["uninstall", "--ida-dir", str(ida_dir)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "Hook successfully removed" in captured.out


def test_cli_no_command(capsys):
    exit_code = main([])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out


def test_cli_list_and_run(tmp_path, capsys):
    ida_dir = tmp_path / "cli_ida_run"
    ida_dir.mkdir()

    main(["init", "--backend", "uv", "--ida-dir", str(ida_dir)])
    capsys.readouterr()

    # Test list
    exit_code = main(["list", "--ida-dir", str(ida_dir)])
    assert exit_code == 0

    # Test run
    exit_code = main(
        ["run", "--ida-dir", str(ida_dir), "python", "-c", "print('CLI_RUN_SUCCESS')"]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "CLI_RUN_SUCCESS" in captured.out


def test_cli_run_no_cmd(tmp_path, capsys):
    ida_dir = tmp_path / "cli_ida_empty_run"
    ida_dir.mkdir()

    main(["init", "--backend", "uv", "--ida-dir", str(ida_dir)])
    exit_code = main(["run", "--ida-dir", str(ida_dir)])
    assert exit_code == 1


def test_cli_install_requirement_file(tmp_path, capsys):
    ida_dir = tmp_path / "cli_ida_req"
    ida_dir.mkdir()
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("# empty requirements\n", encoding="utf-8")

    main(["init", "--backend", "uv", "--ida-dir", str(ida_dir)])
    capsys.readouterr()

    exit_code = main(["install", "--ida-dir", str(ida_dir), "-r", str(req_file)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "installed successfully" in captured.out


def test_cli_info_and_init_shows_ida9_details(tmp_path, capsys):
    ida_dir = tmp_path / "cli_ida9"
    ida_dir.mkdir()

    exit_code = main(["init", "--backend", "builtin", "--ida-dir", str(ida_dir)])
    assert exit_code == 0
    init_out = capsys.readouterr().out
    assert "IDAPYTHON_VENV_EXECUTABLE" in init_out

    exit_code = main(["info", "--ida-dir", str(ida_dir)])
    assert exit_code == 0
    info_out = capsys.readouterr().out
    assert "IDA 9.0+ Native" in info_out


def test_cli_uninstall_no_hook_with_clean_venv(tmp_path, capsys):
    ida_dir = tmp_path / "cli_un_no_hook"
    ida_dir.mkdir()
    # Create only venv directory without idapythonrc.py
    venv_dir = ida_dir / "venv"
    venv_dir.mkdir()

    exit_code = main(["uninstall", "--ida-dir", str(ida_dir), "--clean-venv"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "No active hook found" in out
    assert "Hook successfully removed" not in out
    assert "Virtualenv directory cleaned" in out
    assert not venv_dir.exists()

