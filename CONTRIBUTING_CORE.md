# CORE TEAM CONTRIBUTION GUIDE

# 1. Transparency

1.1 Use work logs for reflection of work done, aswell as telling your peers about changes that may affect their own tasks

1.2 A work log SHOULD be submitted after a "unit of work" is complete.

1.2.1 A "unit of work" should not span more than one full day's worth of work.

1.2.2 A "unit of work" should be small enough that the log entries give useful insight.

1.3 Individual logs are reviewed in weekly meetings

<!--1.4 Bullet point list of topics and one or more sub-points describing each item in short sentences, eg;

```
- Core
	* fixed foo
	* fixed bar
- Frontend
	* connected bar to baz

```-->

1.4 Work log format is defined in []()

1.5 Link to issue/MR in bullet point where appropriate

1.6 


# 2. Code hygiene

2.1 Keep function names and variable names short

2.2 Keep code files, functions and test fixtures short

2.3 The less magic the better. Recombinable and replaceable is king

2.4 Group imports by `standard`, `external`, `local`, `test` - in that order

2.5 Only auto-import when necessary, and always with a minimum of side-effects

2.6 Use custom errors. Let them bubble up

2.7 No logs in tight loops

2.8 Keep executable main routine minimal. Pass variables (do not use globals) in main business logic function

2.9 Test coverage MUST be kept higher than 90% after changes

2.10 Docstrings. Always. Always!


# 3. Versioning

3.1 Use [Semantic Versioning](https://semver.org/)

3.2 When merging code, explicit dependencies SHOULD NOT use pre-release version


# 4. Issues

4.1 Issue title should use [Convention Commit structure](https://www.conventionalcommits.org/en/v1.0.0-beta.2/)

4.2 Issues need proper problem statement

4.2.1. What is the current state

4.2.2. If current state is not behaving as expected, what was the expected state

4.2.3. What is the desired new state.

4.3  Issues need proper resolution statement

4.3.1. Bullet point list of short sentences describing practical steps to reach desired state
		
4.3.2. Builet point list of external resources informing the issue and resolution

4.4 Tasks needs to be appropriately labelled using GROUP labels.


# 5. Code submission

5.1 A branch and new MR is always created BEFORE THE WORK STARTS

5.2 An MR should solve ONE SINGLE PART of a problem

5.3 Every MR should have at least ONE ISSUE associated with it. Ideally issue can be closed when MR is merged

5.4 MRs should not be open for more than one week (during normal operation periods)

5.5 MR should ideally not be longer than 400 lines of changes of logic

5.6 MRs that MOVE or DELETE code should not CHANGE that same code in a single MR. Scope MOVEs and DELETEs in separate commits (or even better, separate MRs) for transparency


# 6. Code reviews

6.1 At least one peer review before merge

6.2 If MR is too long, evaluate whether this affects the quality of the review negatively. If it does, expect to be asked to split it up

6.3 Evaluate changes against associated issues' problem statement and proposed resolution steps. If there is a mismatch, either MR needs to change or issue needs to be amended accordingly

6.4 Make sure all technical debt introduced by MR is documented in issues. Add them according to criteria in section ISSUES if not

6.5 If CI is not working, reviewer MUST make sure code builds and runs

6.6 Behave!

6.6.1 Don't be a jerk

6.6.2 Don't block needlessly

6.6.3 Say please
