/**
 * Locates a citation's quote inside its source text.
 *
 * Matching follows the API's citation check: case, runs of whitespace, commas and
 * typography (dashes, curly quotes) are ignored, so a quote that spans a line break, or that a model
 * wrote with a non-breaking hyphen, is still found. The result is a range in the original
 * text, ready to highlight.
 */

export type Range = { start: number; end: number };

/** The same table as the API's `TYPOGRAPHIC_EQUIVALENTS`: code point to its plain form. */
const PLAIN_FORMS: Record<string, readonly number[]> = {
  "-": [0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2015, 0x2212, 0xfe58, 0xfe63, 0xff0d],
  "'": [0x2018, 0x2019, 0x201a, 0x201b, 0x2032],
  '"': [0x201c, 0x201d, 0x201e, 0x201f, 0x2033],
  "...": [0x2026],
  "": [0x200b, 0x200c, 0x200d, 0x2060, 0xfeff],
};

const PLAIN = new Map<string, string>(
  Object.entries(PLAIN_FORMS).flatMap(([plain, codes]) =>
    codes.map((code) => [String.fromCodePoint(code), plain] as const),
  ),
);

type Normalised = { text: string; positions: number[] };

function normalise(source: string): Normalised {
  let text = "";
  const positions: number[] = [];
  let pendingSpace = false;
  for (let index = 0; index < source.length; index += 1) {
    const character = source[index];
    // A comma counts as a space, as in the API: adding or dropping one changes no word.
    if (/\s/.test(character) || character === ",") {
      pendingSpace = text.length > 0;
      continue;
    }
    if (pendingSpace) {
      text += " ";
      positions.push(index - 1);
      pendingSpace = false;
    }
    // Each character of the plain form maps back to the one character it replaced.
    for (const plain of PLAIN.get(character) ?? character) {
      text += plain.toLowerCase();
      positions.push(index);
    }
  }
  return { text, positions };
}

export function findQuote(source: string, quote: string): Range | null {
  const needle = normalise(quote).text;
  if (needle.length === 0) return null;
  const haystack = normalise(source);
  const at = haystack.text.indexOf(needle);
  if (at === -1) return null;
  return {
    start: haystack.positions[at],
    end: haystack.positions[at + needle.length - 1] + 1,
  };
}

export type Segment = { text: string; highlighted: boolean };

/** The source split around the quote, or the whole source unhighlighted when it is absent. */
export function highlightQuote(source: string, quote: string): Segment[] {
  const range = findQuote(source, quote);
  if (range === null) return [{ text: source, highlighted: false }];
  return [
    { text: source.slice(0, range.start), highlighted: false },
    { text: source.slice(range.start, range.end), highlighted: true },
    { text: source.slice(range.end), highlighted: false },
  ].filter((segment) => segment.text.length > 0);
}
