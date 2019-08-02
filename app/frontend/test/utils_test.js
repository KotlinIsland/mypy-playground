import { parseMessages } from '../src/utils';

describe('parseMessages', () => {
  it('should parse and return annotations', () => {
    const stdout = `main.py:12: error: Argument 1 to "fib" has incompatible type "str"; expected "int"
main.py:13: error: Argument 1 to "fib" has incompatible type "Callable[[int], Iterator[int]]"; expected "int"`;
    const annotations = [
      {
        row: 11,
        type: 'error',
        text: 'Argument 1 to "fib" has incompatible type "str"; expected "int"',
      },
      {
        row: 12,
        type: 'error',
        text: 'Argument 1 to "fib" has incompatible type "Callable[[int], Iterator[int]]"; expected "int"',
      },
    ];
    expect(parseMessages(stdout)).toEqual(annotations);
  });
});
