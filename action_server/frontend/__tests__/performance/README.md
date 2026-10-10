# Performance Tests

This directory contains performance benchmarks for UI components in the Action Server frontend.

## Table Performance Tests

The `Table.perf.test.tsx` file contains comprehensive performance tests for the Table component.

### Test Coverage

#### 1. Render Performance
- Tests rendering of 100, 500, and 1000 rows
- Validates render times stay within acceptable thresholds:
  - 100 rows: < 1000ms (very conservative for CI environment stability)
  - 500 rows: < 1500ms
  - 1000 rows: < 2000ms
- Checks consistency across multiple renders
- These synchronous jsdom measurements do not establish real-browser timing.
- Thresholds are conservative to catch severe regressions, not measure exact performance

#### 2. DOM Structure Efficiency
- Validates minimal DOM node generation
- Ensures no excessive wrapper elements
- Verifies correct number of rows and cells

#### 3. Re-render Performance
- Measures update performance when data changes
- Uses five fixed paired mount/update samples with deterministic data, retains every duration, and compares medians (update/mount < 1.25).
- Verifies every updated value, cell count and retained row DOM identity.
- The mount median retains the existing 1000ms severe-regression limit. jsdom has no browser layout/frame scheduler, so this gate does not establish 60fps. Real-browser performance needs separate controlled acceptance.

#### 4. Scroll Performance
- Validates overflow-auto container for scrolling
- Measures layout property access (no thrashing)
- Ensures sub-millisecond measurement times

#### 5. Memory Usage Validation
- Reports memory usage if performance.memory API is available
- Validates memory doesn't increase excessively (< 10MB for 1000 rows)
- Checks for memory leaks across multiple render/cleanup cycles

#### 6. Interactive Element Performance
- Tests performance with clickable rows
- Tests performance with selected rows
- Ensures interactive features don't impact render time

#### 7. Performance Regression Suite
- Provides baseline metrics for all table sizes
- Validates sub-linear scaling (1000 rows shouldn't be > 20x slower than 100)

### Running the Tests

```bash
# Run all performance tests
npm test -- __tests__/performance/

# Run Table performance tests only
npm test -- __tests__/performance/Table.perf.test.tsx

# Run with verbose output
npm test -- __tests__/performance/ --reporter=verbose
```

### Performance Thresholds

The tests use the following performance thresholds (very conservative for CI stability):

```typescript
const PERF_THRESHOLDS = {
  SMALL_RENDER: 1000,   // 100 rows: < 1000ms (very conservative for CI)
  MEDIUM_RENDER: 1500,  // 500 rows: < 1500ms
  LARGE_RENDER: 2000,   // 1000 rows: < 2000ms
  UPDATE_TO_MOUNT_RATIO: 1.25, // Five paired jsdom mount/update samples
};
```

**Important**: These thresholds are intentionally very conservative to ensure test stability across different CI environments. They are designed to catch severe performance regressions (10x+ slower), not to measure exact performance. They do not establish a real-browser frame-rate target.

### Test Results

Illustrative jsdom output (not an acceptance receipt):

```
=== Table Performance Baseline ===
100 rows: ~20-40ms
500 rows: ~90-130ms
1000 rows: ~180-280ms
===================================

Performance scale factor (1000/100): ~7-8x
```

Release acceptance requires attributable measurements on the candidate and environment.

### Notes

- Tests run in jsdom environment, so actual browser performance may differ
- Memory API (`performance.memory`) is not available in all environments
- Scroll measurements return 0 in jsdom since there's no actual layout
- For real-world performance testing, consider Playwright or Lighthouse tests

### Adding New Performance Tests

When adding new performance tests:

1. Use `performance.now()` for timing measurements
2. Set reasonable thresholds based on component complexity
3. Clean up after each test with `cleanup()`
4. Consider both initial render and re-render performance
5. Test with realistic data sizes
6. Include console logging for debugging
7. Document any environment limitations (like jsdom)
