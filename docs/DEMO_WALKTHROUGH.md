# RepoPilot Demo Walkthrough

This walkthrough uses a small Java or Python sample repository with twelve baseline tests, two of which expose the requested behavior.

1. Start the API and console.
2. Enter the sample repository path and task: `Fix the discount calculation for expired coupons.`
3. The intake event creates an isolated run workspace. The analysis event reports language, build system, source/test directories, file counts, and ranked search hits with scores.
4. The baseline gate records `10 passed, 2 failed` and marks those two failures as pre-existing.
5. The Task and Debug agents identify `applyDiscount` and explain that the expired-coupon branch is bypassing the guard before the percentage is clamped.
6. The Test Generator writes a new acceptance test in a new test file. Existing tests are protected and cannot be overwritten.
7. The first Code Agent attempt intentionally changes a shared rounding helper. The Regression Guardian reports a previously passing test as newly failed.
8. The Manager rolls back the attempt, feeds the exact failing test and guard output back to the Code Agent, and retries with a two-line targeted edit.
9. The Hallucination Guard checks imports, symbols, dependencies, compilation, and the minimal diff budget.
10. The final report shows `13 passed, 0 failed`, `0 regressions`, the generated test, plain-English root cause, and the unified diff.

The run is accepted only when the previously passing ten tests remain green, the generated target test passes, compilation succeeds, and no safety gate rejects the patch. The `10/12` baseline failures remain visible as pre-existing failures rather than being misreported as regressions.
