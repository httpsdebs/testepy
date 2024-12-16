import builtins
import contextlib
import io
import tarfile
from pathlib import Path
from typing import cast

import pytest

import run_release
from release import ReleaseShelf, Tag


@pytest.mark.parametrize(
    ["url", "expected"],
    [
        ("github.com/hugovk/cpython.git", "hugovk"),
        ("git@github.com:hugovk/cpython.git", "hugovk"),
        ("https://github.com/hugovk/cpython.git", "hugovk"),
    ],
)
def test_extract_github_owner(url: str, expected: str) -> None:
    assert run_release.extract_github_owner(url) == expected


def test_invalid_extract_github_owner() -> None:
    with pytest.raises(
        run_release.ReleaseException,
        match="Could not parse GitHub owner from 'origin' remote URL: "
        "https://example.com",
    ):
        run_release.extract_github_owner("https://example.com")


def test_check_magic_number() -> None:
    db = {
        "release": Tag("3.13.0rc1"),
        "git_repo": str(Path(__file__).parent / "magicdata"),
    }
    with pytest.raises(
        run_release.ReleaseException, match="Magic numbers in .* don't match"
    ):
        run_release.check_magic_number(cast(ReleaseShelf, db))


def prepare_fake_docs(tmp_path: Path, content: str) -> None:
    docs_path = tmp_path / "3.13.0rc1/docs"
    docs_path.mkdir(parents=True)
    tarball = tarfile.open(docs_path / "python-3.13.0rc1-docs-html.tar.bz2", "w:bz2")
    with tarball:
        tarinfo = tarfile.TarInfo("index.html")
        tarinfo.size = len(content)
        tarball.addfile(tarinfo, io.BytesIO(content.encode()))


@contextlib.contextmanager
def fake_answers(monkeypatch: pytest.MonkeyPatch, answers: list[str]) -> None:
    """Monkey-patch input() to give the given answers. All must be consumed."""

    answers_left = list(answers)

    def fake_input(question):
        print(question, "--", answers_left[0])
        return answers_left.pop(0)

    with monkeypatch.context() as ctx:
        ctx.setattr(builtins, "input", fake_input)
        yield
    assert answers_left == []


def test_check_doc_unreleased_version_no_file(tmp_path: Path) -> None:
    db = {
        "release": Tag("3.13.0rc1"),
        "git_repo": str(tmp_path),
    }
    with pytest.raises(AssertionError):
        # There should be a docs artefact available
        run_release.check_doc_unreleased_version(cast(ReleaseShelf, db))


def test_check_doc_unreleased_version_no_file_alpha(tmp_path: Path) -> None:
    db = {
        "release": Tag("3.13.0a1"),
        "git_repo": str(tmp_path),
    }
    # No docs artefact needed for alphas
    run_release.check_doc_unreleased_version(cast(ReleaseShelf, db))


def test_check_doc_unreleased_version_ok(monkeypatch, tmp_path: Path) -> None:
    prepare_fake_docs(
        tmp_path,
        "<div>New in 3.13</div>",
    )
    db = {
        "release": Tag("3.13.0rc1"),
        "git_repo": str(tmp_path),
    }
    run_release.check_doc_unreleased_version(cast(ReleaseShelf, db))


def test_check_doc_unreleased_version_not_ok(monkeypatch, tmp_path: Path) -> None:
    prepare_fake_docs(
        tmp_path,
        "<div>New in 3.13.0rc1 (unreleased)</div>",
    )
    db = {
        "release": Tag("3.13.0rc1"),
        "git_repo": str(tmp_path),
    }
    with fake_answers(monkeypatch, ["no"]), pytest.raises(AssertionError):
        run_release.check_doc_unreleased_version(cast(ReleaseShelf, db))


def test_check_doc_unreleased_version_waived(monkeypatch, tmp_path: Path) -> None:
    prepare_fake_docs(
        tmp_path,
        "<div>New in 3.13.0rc1 (unreleased)</div>",
    )
    db = {
        "release": Tag("3.13.0rc1"),
        "git_repo": str(tmp_path),
    }
    with fake_answers(monkeypatch, ["yes"]):
        run_release.check_doc_unreleased_version(cast(ReleaseShelf, db))
