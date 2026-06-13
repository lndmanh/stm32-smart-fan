function assert(condition, message) {
  if (!condition) {
    throw new Error(message || 'Assertion failed');
  }
}

assert.ok = assert;
assert.equal = (a, b) => assert(a === b, `${a} !== ${b}`);
assert.notEqual = (a, b) => assert(a !== b, `${a} === ${b}`);

module.exports = assert;
