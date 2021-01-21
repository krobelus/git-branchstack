# Changelog

## [Unreleased]
- Allow passing a custom range with -r to override @{upstream}..

## [0.0.2] - 2021-01-21
- Fix error when previously generated branch was deleted
- Fix cache of previously generated branches being cleared too eagerly
- Fix git-branchless-pick inserting new cherry-picks at the beginning of the
  todo list, instead of at the end.
- Fix cases when a Git ref with the same name as a branch exists
- Show more explicit errors on invalid usage

## [0.0.1] - 2021-01-17
- Initial release
