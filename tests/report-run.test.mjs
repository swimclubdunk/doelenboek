// Tests for the pure parts of src/report-run.js. Run: node --test "tests/*.test.mjs"
import test from 'node:test';
import assert from 'node:assert/strict';
import RR from '../src/report-run.js';

test('a stored photo is passed to the PDF as is only when its bytes really are the JPEG or PNG it claims', () => {
  assert.equal(RR.looksLike('image/jpeg', '/9j/4AAQSkZJRg'), true);
  assert.equal(RR.looksLike('image/png', 'iVBORw0KGgoAAAANSUhEUg'), true);
  assert.equal(RR.looksLike('image/jpeg', 'iVBORw0KGgoAAAANSUhEUg'), false);   // a PNG called JPEG
  assert.equal(RR.looksLike('image/jpeg', 'AAAAAAAAAAAA'), false);             // not an image at all
  assert.equal(RR.looksLike('image/webp', 'UklGRiQAAABXRUJQ'), false);         // WebP is always drawn again
});
