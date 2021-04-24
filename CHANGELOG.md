# Changelog

## Unreleased
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
