#!/usr/bin/env python3

import argparse
import os
import sys
from typing import Dict, Optional, List, Set, Tuple
from pathlib import Path
from subprocess import CalledProcessError

import gitrevise
from gitrevise import merge, utils
from gitrevise.utils import EditorError
from gitrevise.odb import Blob, Repository
from gitrevise.merge import rebase, MergeConflict

USAGE = """\
Create branches for commits in @{upstream}..HEAD if their commit message
subject starts with [<topic>] where <topic> is the desired branch name.
"""

SUBJECT_PREFIX_PREFIX = b"["
SUBJECT_PREFIX_SUFFIX = b"]"

CommitEntries = List[Tuple[str, str, str]]

TrimSubject = bool
Dependency = Tuple[str, TrimSubject]
Dependencies = Dict[str, Dependency]

def parse_log(
    repo, prefix_prefix, prefix_suffix, *args
) -> Tuple[CommitEntries, Dependencies]:
    commit_entries = []
    dependency_graph: Dependencies = {}
    if "--reverse" not in args:
        dependency_graph = None
    include_others = "--reverse" not in args
    patches = repo.git("log", "-z", "--format=%H %B", *args).decode().split("\x00")
    for entry in patches:
        tmp = entry.split(maxsplit=1)
        if len(tmp) != 2:
            continue
        commit, message = tmp
        raw_subject = message.split("\n\n", maxsplit=1)[0].strip()
        words = raw_subject.split(maxsplit=1)
        if len(words) < 2:
            if include_others:
                commit_entries += [(commit, None, raw_subject)]
            continue
        prefix, subject = words
        if not prefix.startswith(prefix_prefix) or not prefix.endswith(prefix_suffix):
            if include_others:
                commit_entries += [(commit, None, raw_subject)]
            continue

        prefix = prefix[len(prefix_prefix) : -len(prefix_suffix)]
        topic_with_parents = prefix.split(":")
        topic = topic_with_parents[0]
        parent_topics = [parse_parent_topic(t) for t in topic_with_parents[1:] if t]

        if not topic:
            if include_others:
                commit_entries += [(commit, "", subject)]
            continue

        commit_entries += [(commit, topic, subject)]

        if dependency_graph is not None:
            if topic not in dependency_graph:
                dependency_graph[topic] = {}
            if parent_topics:
                dependency_graph[topic].update(parent_topics)

    return commit_entries, dependency_graph

def parse_parent_topic(topic: str) -> Dependency:
    keep_tag = False
    if topic.startswith("+"):
        topic = topic[len("+") :]
        keep_tag = True
    return (topic, keep_tag)

def transitive_dependencies(depgraph: Dependencies, node: Dependency) -> Dependencies:
    visited: Dependencies = {}
    transitive_dependencies_rec(depgraph, node, visited)
    return visited

def transitive_dependencies_rec(
    depgraph: Dependencies, node: Dependency, visited: Dependencies
) -> None:
    name, keep_tag = node
    if name in visited:
        return
    visited[name] = keep_tag
    if name in depgraph:
        for x in depgraph[name].items():
            transitive_dependencies_rec(depgraph, x, visited)

class BranchWasModifiedError(Exception):
    pass

class InvalidRangeError(Exception):
    pass

class TopicNotFoundError(Exception):
    pass

def validate_cache(repo, topic_set, force):
    cache_path = repo.gitdir / "branchstack-cache"
    if not os.path.exists(cache_path):
        return
    cached_shas = [
        (w[0], w[1])
        for w in map(
            lambda line: line.split(), cache_path.read_bytes().decode().splitlines()
        )
    ]
    existing_branches = {}
    refs = repo.git(
        "for-each-ref",
        "--format",
        "%(refname:short) %(objectname)",
        *[f"refs/heads/{t[0]}" for t in cached_shas],
    )
    for line in refs.decode().splitlines():
        refname, sha = line.split(" ", maxsplit=1)
        existing_branches[refname] = sha
    for topic, cached_sha in cached_shas:
        if topic not in existing_branches:
            continue
        if topic not in topic_set:  # The user did not ask to create this branch.
            continue
        current_sha = existing_branches[topic]
        if current_sha == cached_sha:
            continue
        if force:
            print(f"Will overwrite modified branch {topic}")
        else:
            raise BranchWasModifiedError(topic)

def update_cache(repo, topics):
    cache_path = repo.gitdir / "branchstack-cache"
    mode = "r+" if cache_path.exists() else "w+"
    with open(cache_path, mode) as f:
        cached_shas = {
            w[0]: w[1] for w in map(lambda line: line.split(), f.read().splitlines())
        }
        new_topics = cached_shas
        for t in topics:
            if topics[t] is not None:
                new_topics[t] = topics[t]
        new_content = ""
        for topic in new_topics:
            sha = new_topics[topic]
            if sha is not None:
                new_content += f"{topic} {sha}{os.linesep}"
        f.seek(0)
        f.truncate()
        f.write(new_content)

def trimmed_message(subject: str, message: bytes) -> str:
    body = b"\n".join(message.split(b"\n\n", maxsplit=1)[1:])
    if body:
        return subject.encode() + b"\n\n" + body
    return subject.encode()

def create_branches(
    repo,
    current_branch,
    base_commit,
    tip="HEAD",
    branches=None,
    force=False,
    keep_tags=None,
) -> None:
    prefix_prefix = repo.config(
        "branchstack.subjectPrefixPrefix",
        default=SUBJECT_PREFIX_PREFIX,
    ).decode()
    prefix_suffix = repo.config(
        "branchstack.subjectPrefixSuffix",
        default=SUBJECT_PREFIX_SUFFIX,
    ).decode()
    commit_entries, dependency_graph = parse_log(
        repo, prefix_prefix, prefix_suffix, f"{base_commit}..{tip}", "--reverse"
    )
    def by_first_commit_on_topic(commit_entry):
        (commit, topic, subject) = commit_entry
        for i in range(len(commit_entries)):
            if commit_entries[i][1] == topic:
                return i
        return -1
    commit_entries.sort(key=by_first_commit_on_topic)
    topics = {commit_entry[1]: None for commit_entry in commit_entries}
    all_topics = set(topics)
    topic_set = all_topics

    if branches:
        for topic in branches:
            if topic not in all_topics:
                raise TopicNotFoundError(topic, base_commit, tip)
        topic_set = set()
        for topic in branches:
            topic_set.add(topic)
        topics = {t: None for t in topics if t in topic_set}

    for child in topics:
        for parent in dependency_graph[child]:
            if parent not in all_topics:
                print(f"Warning: topic '{child}' depends on missing topic '{parent}'.")

    assert current_branch is None or current_branch not in set(
        topics
    ), f"Refusing to overwrite current branch {current_branch}"

    base_commit_id = repo.git("rev-parse", base_commit).decode()

    validate_cache(repo, topic_set, force)
    try:
        for topic in topics:
            create_branch(
                repo,
                prefix_prefix,
                prefix_suffix,
                keep_tags,
                base_commit_id,
                commit_entries,
                topics,
                dependency_graph,
                topic,
            )
    finally:
        update_cache(repo, topics)

    for topic in topics:
        print(topic)
        for line in (
            repo.git("log", f"{base_commit}..refs/heads/{topic}", "--oneline")
            .decode()
            .splitlines()
        ):
            print("\t", line)

def create_branch(
    repo,
    prefix_prefix,
    prefix_suffix,
    keep_tags,
    base_commit_id,
    commit_entries,
    topics,
    dependency_graph,
    topic,
):
    head = repo.get_commit(base_commit_id)
    deps = transitive_dependencies(dependency_graph, (topic, False))
    for commit, t, subject in commit_entries:
        if t not in deps:
            continue
        keep_tag = deps[t]
        patch = repo.get_commit(commit)
        def on_conflict(path):
            """
            Some commit in "base_commit..commit~" must have touched the
            path as well, but is not among our dependencies.
            """
            print("Missing dependency on one of the commits below?")
            log, _ = parse_log(
                repo,
                prefix_prefix,
                prefix_suffix,
                f"{base_commit_id}..{commit}~",
                "--",
                path,
            )
            for id, topic, subject in log:
                if topic not in deps:
                    prefix = (
                        ""
                        if topic is None
                        else f"{prefix_prefix}{topic}{prefix_suffix} "
                    )
                    print(f"\t{id[:7]} {prefix}{subject}")
        global ON_CONFLICT
        ON_CONFLICT = on_conflict
        head = rebase(patch, head)
        message = head.message
        keep_tag = (
            keep_tag
            or (keep_tags == "dependencies" and t != topic)
            or keep_tags == "all"
        )
        if not keep_tag:
            message = trimmed_message(subject, patch.message)
        head = repo.new_commit(
            message=message,
            tree=head.tree(),
            parents=head.parents(),
            author=head.author,
            committer=patch.committer,  # preserve original committer and timestamp
        )
    topic_fqn = f"refs/heads/{topic}"
    if not repo.git("branch", "--list", topic):
        repo.git("branch", topic, base_commit_id)
    topic_ref = repo.get_commit_ref(topic_fqn)

    if head.oid != topic_ref.target.oid:
        topic_oid = topic_ref.target.oid
        print(f"Updating {topic_ref.name} ({topic_oid} => {head.oid})")
        topic_ref.update(head, "git-branchstack rewrite")

    topics[topic] = topic_ref.target.oid

ON_CONFLICT = None

def override_merge_blobs(
    path: Path,
    labels: Tuple[str, str, str],
    current: Blob,
    base: Optional[Blob],
    other: Blob,
) -> Blob:
    repo = current.repo

    tmpdir = repo.get_tempdir()

    annotated_labels = (
        f"{path} (new parent): {labels[0]}",
        f"{path} (old parent): {labels[1]}",
        f"{path} (current): {labels[2]}",
    )
    (is_clean_merge, merged) = merge.merge_files(
        repo,
        annotated_labels,
        current.body,
        base.body if base else b"",
        other.body,
        tmpdir,
    )

    if is_clean_merge:
        # No conflicts.
        return Blob(repo, merged)

    path = path.relative_to("/")

    # At this point, we know that there are merge conflicts to resolve.
    # Prompt to try and trigger manual resolution.
    print(f"Conflict applying '{labels[2]}'")
    print(f"  Path: '{path}'")

    preimage = merged
    (normalized_preimage, conflict_id, merged_blob) = merge.replay_recorded_resolution(
        repo, tmpdir, preimage
    )
    if merged_blob is not None:
        return merged_blob

    ON_CONFLICT(path)

    if input("  Edit conflicted file? (Y/n) ").lower() == "n":
        raise MergeConflict("user aborted")

    # Open the editor on the conflicted file. We ensure the relative path
    # matches the path of the original file for a better editor experience.
    conflicts = tmpdir / "conflict" / path
    conflicts.parent.mkdir(parents=True, exist_ok=True)
    conflicts.write_bytes(preimage)
    merged = utils.edit_file(repo, conflicts)

    # Print warnings if the merge looks like it may have failed.
    if merged == preimage:
        print("(note) conflicted file is unchanged")

    if b"<<<<<<<" in merged or b"=======" in merged or b">>>>>>>" in merged:
        print("(note) conflict markers found in the merged file")

    # Was the merge successful?
    if input("  Merge successful? (y/N) ").lower() != "y":
        raise MergeConflict("user aborted")

    merge.record_resolution(repo, conflict_id, normalized_preimage, merged)

    return Blob(current.repo, merged)

gitrevise.merge.merge_blobs = override_merge_blobs

def dwim(repo: Repository) -> Tuple[str, str]:
    rebase_dir = repo.gitdir / "rebase-merge"

    if os.path.exists(rebase_dir):
        branch = os.path.basename((rebase_dir / "head-name").read_text().strip())
        base_commit = os.path.basename((rebase_dir / "onto").read_text().strip())
    else:
        branch = repo.git("symbolic-ref", "--short", "HEAD").decode()
        base_commit = "@{upstream}"

    return branch, base_commit

def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="git branchstack",
        description=USAGE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    p.add_argument(
        "<topic>",
        nargs="*",
        help="only create the given branches",
    )

    p.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="overwrite branches even if they were modified since the last run",
    )

    p.add_argument(
        "--keep-tags",
        "-k",
        metavar="dependencies|all",
        nargs="?",
        const="dependencies",
        help="keep topic tag on created commits",
    )

    p.add_argument(
        "--range",
        "-r",
        metavar="<rev1>..<rev2>",
        help="use commits from the given range instead of @{upstream}..",
    )

    return p

def parse_range(repo: Repository, range: str) -> Tuple[str, str]:
    if ".." not in range:
        raise InvalidRangeError(range)
    upper, lower = repo.git("rev-parse", range).decode().splitlines()
    assert lower.startswith("^")
    return lower[len("^") :], upper

def main(argv: Optional[List[str]] = None):
    args = parser().parse_args(argv)
    try:
        with Repository() as repo:
            if args.range is None:
                branch, base_commit = dwim(repo)
                tip = "HEAD"
            else:
                branch = None
                base_commit, tip = parse_range(repo, args.range)
            if args.keep_tags is not None:
                if args.keep_tags not in ("dependencies", "all"):
                    print(
                        "argument to --keep-tags must be one of 'dependencies' (the default) or 'all'"
                    )
                    sys.exit(1)
            base_commit = repo.git("merge-base", "--", base_commit, "HEAD").decode()
            create_branches(
                repo,
                branch,
                base_commit,
                tip,
                getattr(args, "<topic>"),
                force=args.force,
                keep_tags=args.keep_tags,
            )
    except BranchWasModifiedError as err:
        print(
            f"error: generated branch {err} has been modified. Use --force to overwrite."
        )
        sys.exit(1)
    except CalledProcessError as err:
        print(f"subprocess exited with non-zero status: {err.returncode}")
        sys.exit(1)
    except EditorError as err:
        print(f"editor error: {err}")
        sys.exit(1)
    except InvalidRangeError as err:
        print(f'invalid commit range: {err} should be a valid "a..b" range')
        sys.exit(1)
    except MergeConflict as err:
        print(f"merge conflict: {err}")
        sys.exit(1)
    except TopicNotFoundError as err:
        topic, base_commit, tip = err.args
        print(f"error: topic '{topic}' not found {base_commit}..{tip}")
    except ValueError as err:
        print(f"invalid value: {err}")
        sys.exit(1)

if __name__ == "__main__":
    main()
