/**
 * Which script a data text is written in, and whether a reader of the UI language can read it (pure; no DOM, no
 * store). The deck's own words come from its packs in the reader's language; DATA texts (an official warning, a
 * news line, a field report) arrive in whatever language their source wrote them. Rule (English first):
 *
 *   - a text the reader can read is shown as it is;
 *   - a text mostly in Bengali script, shown to a reader of English or Hindi, is NOT machine-translated (an official
 *     warning is never re-worded by a machine): the surface shows an honest English line instead ("Official text in
 *     Bengali") and keeps the original one level down (the object page, a disclosure), marked lang="bn";
 *   - the same for Devanagari shown to a reader of English or Bengali.
 */

const BENGALI = /[ঀ-৿]/g;
const DEVANAGARI = /[ऀ-ॿ]/g;
const LATIN = /[A-Za-z]/g;

export type Script = 'bn' | 'hi' | 'latin' | null;

/** The script most of a text's letters are in (null for an empty text or one with no letters). Danda and digits do not count. */
export function scriptOf(text: string | null | undefined): Script {
	const s = String(text ?? '');
	const bn = (s.match(BENGALI) ?? []).filter((c) => c !== '।' && c !== '॥').length;
	const hi = (s.match(DEVANAGARI) ?? []).filter((c) => c !== '।' && c !== '॥' && !/[०-९]/.test(c)).length;
	const la = (s.match(LATIN) ?? []).length;
	const max = Math.max(bn, hi, la);
	if (max === 0) return null;
	// placeholders such as [WITHHELD] are Latin capitals inside a Bengali line: Bengali wins when it carries the words
	if (bn === max || bn >= la * 0.6) return bn > 0 ? 'bn' : null;
	if (hi === max) return 'hi';
	return 'latin';
}

/** Can a reader of the UI language `lang` read this text as it is? English readers read Latin; Bengali readers Bengali and Latin; Hindi readers Devanagari and Latin. */
export function readableIn(text: string | null | undefined, lang: string): boolean {
	const sc = scriptOf(text);
	if (sc === null || sc === 'latin') return true;
	return sc === lang;
}

/** The first text a reader of `lang` can read, else null (e.g. the English and the Bengali copy of one warning). */
export function pickReadable(texts: readonly (string | null | undefined)[], lang: string): string | null {
	for (const t of texts) if (t && readableIn(t, lang)) return t;
	return null;
}
