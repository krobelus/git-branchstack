# Changelog

## Unreleased

## [0.2.0] - 2022-01-09
- BREAKING: option `--trim-subject` has been dropped and is the default
  behavior.  New option `--keep-tags` restores the old behavior. Consequently,
  the meaning of `+` inside topic tags has been inverted.
- Preserve committer date in created commits. This means we create
  deterministic commit IDs, which makes it easier to reuse commits, and
  creates fewer loose objects.

## [0.1.0] - 2021-08-29
- BREAKING `git-branchless` was renamed to `git-branchstack` (#1).
- `git-branchstack-pick` replaces a "refs/" prefix with "gitref/", making it
  easier to cherry-pick remote non-branch refs without introducing ambiguous
  refs.

## [0.0.6] - 2021-06-03
- `git-branchless-pick` now prefers `$GIT_SEQUENCE_EDITOR` over `git var $EDITOR`
  for editing the rebase-todo list.
- `git-branchless-pick` now supports empty base commits, so `..some-branch`
  means: pick all commits on `some-branch` minus the commits already in `HEAD`.
- `git-branchless-pick ..some/branch` will no longer trim the `some/` prefix,
  unless `some` is a valid Git remote.

## [0.0.5] - 2021-04-24
- First release on PyPI.
- Specify dependencies with a `+` prefix, like `[child:+parent]`, to include
  commits from `parent` and trim their subject tags.
- `git-branchless-pick` no longer pulls in new commits from `@{upstream}`.
- Fix subject computation for conflict hint commits without topic prefix

## [0.0.4] - 2021-03-07
- BREAKING: `git-branchless-pick` takes a `..`-range instead of a single commit.
- Branches are no longer based on @{upstream} but on `git merge-base @{u} HEAD`
- Similarly, `git-branchless-pick` will only not add new commits from @{upstream}
- Support multline subjects

## [0.0.3] - 2021-02-03
- BREAKING: the latest version of git-revise is now required, see README
- On conflict, show commits that are likely missing as dependencies
- Allow passing a custom range with -r to override @{upstream}..HEAD
- Allow dropping topic tags from subject with -t/--trim-subject
- Fixed a case of mistakenly refusing to overwrite branches after
  cancelling a previous run (usually on conflict)
- git-branchless-pick inserts new commits in the rebase-todo list
  immediately after dropped commits, instead of before them

## [0.0.2] - 2021-01-21
- Fix error when previously generated branch was deleted
- Fix cache of previously generated branches being cleared too eagerly
- Fix git-branchless-pick inserting new cherry-picks at the beginning of the
  todo list, instead of at the end.
- Fix cases when a Git ref with the same name as a branch exists
- Show more explicit errors on invalid usage

## [0.0.1] - 2021-01-17
- Initial release
