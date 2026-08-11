"""
ASR reference/hypothesis normalizer for the k6net6lke benchmark.

Applies the SAME transformation to both reference and hypothesis so that
word-level WER scoring is not dominated by superficial formatting
differences (digits vs. spelled-out words, hyphens, smart quotes, etc.).

Pipeline:

    1. Unicode NFC.
    2. Estonian path only: find compound tokens via estnltk
       (numeric_date, numeric_time, numeric, hyphenation) and spell them
       out in words. Standalone digit runs are also spelled out.
       Russian: num2words(lang='ru'). English: num2words(lang='en') or
       Whisper's EnglishTextNormalizer if available.
    3. Unit / symbol expansion (%, °C, €, $, ...).
    4. Unicode-aware punctuation -> space (NOT deletion).
    5. Lowercase.
    6. Whitespace collapse + strip.

Usage:
    python3 normalize_asr_text.py --lang et < input.txt > output.txt

Or as a library:
    from normalize_asr_text import normalize
    normalize("Covid-19 patsient", lang="et")
    # -> 'covid üheksateist patsient'

See BENCHMARK_ISSUES.md for the motivation.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata

# ---------------------------------------------------------------------------
# Estonian cardinal speller (num2words has no 'et' locale as of 0.5.13)
# ---------------------------------------------------------------------------

_ET_UNITS = [
    "null", "üks", "kaks", "kolm", "neli",
    "viis", "kuus", "seitse", "kaheksa", "üheksa",
]
_ET_TEENS = [
    "kümme", "üksteist", "kaksteist", "kolmteist", "neliteist",
    "viisteist", "kuusteist", "seitseteist", "kaheksateist", "üheksateist",
]
# Tens: index 2..9 used
_ET_TENS = [
    None, None,
    "kakskümmend", "kolmkümmend", "nelikümmend",
    "viiskümmend", "kuuskümmend", "seitsekümmend",
    "kaheksakümmend", "üheksakümmend",
]
# Hundreds: index 2..9 used (100 handled separately as "sada")
_ET_HUNDREDS_STEM = [
    None, None,
    "kakssada", "kolmsada", "nelisada",
    "viissada", "kuussada", "seitsesada",
    "kaheksasada", "üheksasada",
]


def _et_spell_int(n: int) -> str:
    """Spell a non-negative integer in nominative Estonian.

    Handles 0..10**12 - 1. Good enough for years, counts, ages, percentages,
    and every digit token present in this benchmark's reference data.
    """
    if n < 0:
        return "miinus " + _et_spell_int(-n)
    if n < 10:
        return _ET_UNITS[n]
    if n < 20:
        return _ET_TEENS[n - 10]
    if n < 100:
        t, u = divmod(n, 10)
        if u == 0:
            return _ET_TENS[t]
        return f"{_ET_TENS[t]} {_ET_UNITS[u]}"
    if n < 1000:
        h, rest = divmod(n, 100)
        head = "sada" if h == 1 else _ET_HUNDREDS_STEM[h]
        if rest == 0:
            return head
        return f"{head} {_et_spell_int(rest)}"
    if n < 1_000_000:
        k, rest = divmod(n, 1000)
        head = "tuhat" if k == 1 else f"{_et_spell_int(k)} tuhat"
        if rest == 0:
            return head
        return f"{head} {_et_spell_int(rest)}"
    if n < 1_000_000_000:
        m, rest = divmod(n, 1_000_000)
        head = "miljon" if m == 1 else f"{_et_spell_int(m)} miljonit"
        if rest == 0:
            return head
        return f"{head} {_et_spell_int(rest)}"
    # Fall back to digit-by-digit spellout for astronomical values.
    return " ".join(_ET_UNITS[int(d)] for d in str(n))


def _et_spell_number(token: str) -> str:
    """Spell a bare number token that may contain a decimal comma/dot."""
    token = token.strip()
    # Negative sign
    neg = False
    if token.startswith(("-", "\u2212")):
        neg = True
        token = token[1:]
    if not token:
        return ""
    # Decimal: "5,5" or "5.5" -> "viis koma viis"
    m = re.fullmatch(r"(\d+)[.,](\d+)", token)
    if m:
        int_part, frac_part = m.groups()
        int_words = _et_spell_int(int(int_part))
        # Spell the fractional part digit-by-digit (standard Estonian
        # convention for decimals: "null koma kaks viis" for 0,25)
        frac_words = " ".join(_ET_UNITS[int(d)] for d in frac_part)
        out = f"{int_words} koma {frac_words}"
    elif token.isdigit():
        out = _et_spell_int(int(token))
    else:
        # Mixed / weird: spell each digit that's a digit, keep the rest
        parts = []
        for ch in token:
            if ch.isdigit():
                parts.append(_ET_UNITS[int(ch)])
            elif ch.isalpha():
                parts.append(ch)
        out = " ".join(p for p in parts if p)
    return ("miinus " + out) if neg else out


# ---------------------------------------------------------------------------
# Russian and English number spellers via num2words
# ---------------------------------------------------------------------------

try:
    from num2words import num2words as _num2words
except ImportError:  # pragma: no cover
    _num2words = None


def _spell_number(token: str, lang: str) -> str:
    token = token.strip()
    neg = False
    if token.startswith(("-", "\u2212")):
        neg = True
        token = token[1:]
    if not token:
        return ""

    if lang == "et":
        return _et_spell_number(("-" if neg else "") + token)

    if _num2words is None:
        # No speller available: fall back to digit-by-digit for the token.
        return " ".join(ch for ch in token if ch.isdigit() or ch.isalpha())

    # Decimal detection: prefer dot in num2words input
    m = re.fullmatch(r"(\d+)[.,](\d+)", token)
    try:
        if m:
            value = float(f"{m.group(1)}.{m.group(2)}")
            out = _num2words(value, lang=lang)
        else:
            out = _num2words(int(token), lang=lang)
    except (NotImplementedError, ValueError):
        out = token
    return ("минус " if neg and lang == "ru" else "minus " if neg else "") + out


# ---------------------------------------------------------------------------
# Unit and symbol table
# ---------------------------------------------------------------------------

# Order matters: longer keys must come before shorter keys that are a prefix
# (e.g. "km/h" before "km").
_UNIT_TABLES: dict[str, list[tuple[str, str]]] = {
    "et": [
        ("km/h", " kilomeetrit tunnis "),
        ("°C", " kraadi "),
        ("°F", " kraadi fahrenheiti "),
        ("%", " protsenti "),
        ("€", " eurot "),
        ("$", " dollarit "),
        ("£", " naela "),
        ("&", " ja "),
        ("kg", " kilogrammi "),
    ],
    "ru": [
        ("км/ч", " километров в час "),
        ("°C", " градусов "),
        ("°F", " градусов по фаренгейту "),
        ("%", " процентов "),
        ("€", " евро "),
        ("$", " долларов "),
        ("£", " фунтов "),
        ("&", " и "),
    ],
    "en": [
        ("km/h", " kilometers per hour "),
        ("°C", " degrees celsius "),
        ("°F", " degrees fahrenheit "),
        ("%", " percent "),
        ("€", " euros "),
        ("$", " dollars "),
        ("£", " pounds "),
        ("&", " and "),
    ],
}


def _expand_units(text: str, lang: str) -> str:
    for src, dst in _UNIT_TABLES.get(lang, []):
        text = text.replace(src, dst)
    return text


# ---------------------------------------------------------------------------
# Punctuation -> space
# ---------------------------------------------------------------------------

# Unicode punctuation: \p{P} via the `regex` package would be ideal, but we
# avoid the extra dependency and use an explicit set that covers ASCII
# string.punctuation plus the editorial punctuation actually seen in the
# benchmark refs (295 occurrences of „ " " « » – — … etc.).
_ASCII_PUNCT = r"""!"#$%&'()*+,./:;<=>?@[\]^_`{|}~"""
_UNICODE_PUNCT = (
    "„" "“" "”" "‟" "‚" "‘" "’" "‛"
    "«" "»" "‹" "›"
    "–" "—" "―" "‐" "‑" "‒"
    "…" "·" "•" "·"
    "′" "″" "‴" "‵" "‶" "‷"
    "¡" "¿"
    "§" "¶" "†" "‡"
)
# Hyphen is intentionally excluded from _ASCII_PUNCT above so that
# hyphenated compounds like "Covid-19" are kept together until the
# estnltk pass rewrites them. After the estnltk pass we strip remaining
# hyphens in _strip_trailing_punct below.
_PUNCT_TABLE = str.maketrans(
    {ch: " " for ch in (_ASCII_PUNCT + _UNICODE_PUNCT)}
)
_POST_HYPHEN_TABLE = str.maketrans({"-": " "})


def _punct_to_space(text: str) -> str:
    return text.translate(_PUNCT_TABLE)


def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Estonian compound-token rewriting via estnltk
# ---------------------------------------------------------------------------

try:
    from estnltk import Text as _EstnltkText  # type: ignore
except ImportError:  # pragma: no cover
    _EstnltkText = None


_ET_MONTHS = [
    None,
    "jaanuar", "veebruar", "märts", "aprill", "mai", "juuni",
    "juuli", "august", "september", "oktoober", "november", "detsember",
]


def _et_spell_date(day: int, month: int, year: int) -> str:
    parts = [_et_spell_int(day)]
    if 1 <= month <= 12:
        parts.append(_ET_MONTHS[month])
    else:
        parts.append(_et_spell_int(month))
    parts.append(_et_spell_int(year))
    return " ".join(parts)


def _et_spell_time(hours: int, minutes: int) -> str:
    return f"{_et_spell_int(hours)} {_et_spell_int(minutes)}"


_DATE_RE = re.compile(r"(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})")
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})(?::\d{2})?")
_INT_RE = re.compile(r"\d+")
# Number with Estonian case ending attached, e.g. "21-aastane", "5-le"
_HYPHEN_NUM_RE = re.compile(r"^(\d+)-(\w+)$")


def _rewrite_span(span_text: str, span_type: str, lang: str) -> str | None:
    """Produce a replacement for an estnltk compound-token span.

    Returns ``None`` if we don't know how to rewrite this type — the caller
    then leaves the span alone and lets the later layers handle it.
    """
    if span_type in {"email", "www_address", "xml_tag"}:
        # ASR can't realistically produce these; drop entirely so they
        # don't pollute WER.
        return " "

    if span_type == "numeric_date":
        m = _DATE_RE.fullmatch(span_text.strip("."))
        if m:
            d, mo, y = (int(x) for x in m.groups())
            if y < 100:  # "dd/mm/yy" -> assume 20xx
                y += 2000
            if lang == "et":
                return " " + _et_spell_date(d, mo, y) + " "
            if lang == "ru" and _num2words is not None:
                return " " + " ".join(
                    [_num2words(d, lang="ru"),
                     _num2words(mo, lang="ru"),
                     _num2words(y, lang="ru")]
                ) + " "
            if lang == "en" and _num2words is not None:
                return " " + " ".join(
                    [_num2words(d, lang="en"),
                     _num2words(mo, lang="en"),
                     _num2words(y, lang="en")]
                ) + " "
        return None

    if span_type == "numeric_time":
        m = _TIME_RE.fullmatch(span_text)
        if m:
            h, mi = (int(x) for x in m.groups())
            if lang == "et":
                return " " + _et_spell_time(h, mi) + " "
            if _num2words is not None:
                return " " + _num2words(h, lang=lang) + " " + _num2words(mi, lang=lang) + " "
        return None

    if span_type == "numeric":
        # Grab every digit run and spell each.
        def _sub_int(m: re.Match[str]) -> str:
            return _spell_number(m.group(), lang)
        return " " + _INT_RE.sub(_sub_int, span_text) + " "

    if span_type == "hyphenation":
        # e.g. "Covid-19" -> "Covid üheksateist", "21-aastane" -> "kahekümne üks aastane".
        m = _HYPHEN_NUM_RE.match(span_text)
        if m:
            digits, suffix = m.groups()
            return f" {_spell_number(digits, lang)} {suffix} "
        if "-" in span_text:
            parts = span_text.split("-")
            out_parts = []
            for p in parts:
                if p.isdigit():
                    out_parts.append(_spell_number(p, lang))
                else:
                    out_parts.append(p)
            return " " + " ".join(out_parts) + " "
        return None

    if span_type == "sign":
        # "+5" / "-5" -> signed number
        m = re.fullmatch(r"([+\-])(\d+)", span_text)
        if m:
            sign, digits = m.groups()
            prefix = "miinus " if sign == "-" and lang == "et" else ("плюс " if sign == "+" and lang == "ru" else "")
            return " " + prefix + _spell_number(digits, lang) + " "
        return None

    return None


def _rewrite_with_estnltk(text: str, lang: str) -> str:
    if _EstnltkText is None or lang != "et":
        return text
    t = _EstnltkText(text)
    try:
        t.tag_layer(["compound_tokens"])
    except Exception:
        return text
    spans = []
    for ct in t.compound_tokens:
        spans.append((ct.start, ct.end, list(ct.type)[0] if ct.type else ""))
    # Replace right-to-left so indices remain valid.
    spans.sort(key=lambda s: s[0], reverse=True)
    out = text
    for start, end, type_ in spans:
        span_text = out[start:end]
        rewrite = _rewrite_span(span_text, type_, lang)
        if rewrite is not None:
            out = out[:start] + rewrite + out[end:]
    return out


# ---------------------------------------------------------------------------
# Non-estnltk fallback: spell bare digit runs
# ---------------------------------------------------------------------------

_BARE_NUMBER_RE = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?(?![\w.])")


def _spell_bare_numbers(text: str, lang: str) -> str:
    def repl(m: re.Match[str]) -> str:
        return " " + _spell_number(m.group(), lang) + " "
    return _BARE_NUMBER_RE.sub(repl, text)


# ---------------------------------------------------------------------------
# English path: prefer Whisper's EnglishTextNormalizer when available
# ---------------------------------------------------------------------------

try:
    from whisper.normalizers import EnglishTextNormalizer as _EnTextNormalizer  # type: ignore
    _en_normalizer = _EnTextNormalizer()
except Exception:  # pragma: no cover
    _en_normalizer = None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def normalize(text: str, lang: str) -> str:
    """Normalize ``text`` for WER scoring.

    ``lang`` is a 2-letter code: ``et``, ``ru``, or ``en``.
    """
    if not text:
        return ""

    # 1. Unicode NFC so composed/decomposed forms of "õ", "ü" etc. compare equal.
    text = unicodedata.normalize("NFC", text)

    if lang == "en" and _en_normalizer is not None:
        # Whisper's normalizer already does NFC-ish + lowercase + punct
        # + number expansion + contraction expansion. It's the
        # leaderboard standard for English; short-circuit the rest.
        return _collapse_ws(_en_normalizer(text))

    # 2. Estonian: rewrite compound tokens (dates, times, numeric, Covid-19).
    #    Russian and English both fall through to bare number spelling.
    text = _rewrite_with_estnltk(text, lang)

    # 3. Unit / symbol table.
    text = _expand_units(text, lang)

    # 4. Spell any remaining bare digit tokens.
    text = _spell_bare_numbers(text, lang)

    # 5. Punctuation -> space. NB: replaces, does not delete — fixes the
    #    SLTev/ASRev.py bug that merged "Covid-19" into a single token.
    text = _punct_to_space(text)
    text = text.translate(_POST_HYPHEN_TABLE)

    # 6. Lowercase.
    text = text.lower()

    # 7. Whitespace collapse.
    text = _collapse_ws(text)

    return text


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _normalize_file(in_path: str, out_path: str, lang: str) -> None:
    if in_path == "-":
        in_text = sys.stdin.read()
    else:
        with open(in_path, encoding="utf-8") as f:
            in_text = f.read()

    out_lines = [normalize(line, lang) for line in in_text.splitlines()]
    out_text = "\n".join(out_lines) + ("\n" if in_text.endswith("\n") else "")

    if out_path == "-":
        sys.stdout.write(out_text)
    else:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(out_text)


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Normalize ASR reference/hypothesis text for fair WER scoring.",
    )
    parser.add_argument("--lang", required=True, choices=["et", "ru", "en"])
    parser.add_argument(
        "--in", dest="inputs", action="append", default=[],
        help="Input file (repeatable). If omitted, read from stdin.",
    )
    parser.add_argument(
        "--out", dest="outputs", action="append", default=[],
        help="Output file (repeatable, must match --in order). If omitted, write to stdout.",
    )
    # Legacy short form: `-o file input`. Kept so existing callers still work.
    parser.add_argument(
        "-o", "--output", default=None,
        help="Legacy single-output path (use --in/--out for batching).",
    )
    parser.add_argument(
        "input", nargs="?", default=None,
        help="Legacy single input positional (use --in/--out for batching).",
    )
    args = parser.parse_args(argv)

    # Resolve inputs and outputs from either the batched --in/--out form
    # or the legacy single-file form.
    if args.inputs or args.outputs:
        if len(args.inputs) != len(args.outputs):
            sys.stderr.write(
                f"normalize_asr_text: --in count ({len(args.inputs)}) "
                f"must match --out count ({len(args.outputs)})\n"
            )
            return 2
        pairs = list(zip(args.inputs, args.outputs))
    else:
        in_path = args.input if args.input is not None else "-"
        out_path = args.output if args.output is not None else "-"
        pairs = [(in_path, out_path)]

    for in_path, out_path in pairs:
        _normalize_file(in_path, out_path, args.lang)
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
