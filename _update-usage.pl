#!/usr/bin/env perl

open README_md, "README.md" and undef $/,
scalar <README_md> =~ m/^## Usage\n(.*?)\n^##/ms, $Usage = $1,
open Script, "+<", "git-branchless" and
$New_Text = scalar <Script> =~ s/^(USAGE[^\n]*)\n.*?^("""\n)/$1$Usage$2/msgr,
truncate Script, 0 and seek Script, 0, 0 and print Script $New_Text

and system "black *.py"
