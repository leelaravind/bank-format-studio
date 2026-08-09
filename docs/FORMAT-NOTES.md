# FORMAT NOTES — MT940 (original technical summary)

Status: PHASE 0 RESEARCH. Compiled 2026-08-09 from legally accessible public references
(bibliography in §7); no proprietary SWIFT documentation reproduced. Facts verified
against the downloaded public fixtures in `sample-data/public/mt940/`.

## 1. Envelope / block structure

An MT940 "Customer Statement Message" may arrive in two envelopes:

- **Full SWIFT FIN blocks**: `{1:F01<BIC12>...}{2:O940<BIC>...}{3:...}{4:` … tags … `-}{5:}`. Block 4 holds the tag payload; it terminates with `-` on its own line before `}`. (Seen in the ASNB fixture.)
- **Bare tag files**: the file starts directly at `:20:` (or a bank-proprietary preamble) with no FIN blocks. Dominant form for bank-portal exports. Observed preambles: Rabobank `:940:` first line; ABN AMRO three plain lines (`ABNANL2A` / `940` / `ABNANL2A`); ING `0000 01INGBNL2AXXXX00001` + `940 00` lines.

A file may contain **multiple statements** concatenated; each begins at the next `:20:` (or after a `-` separator line, as in German files).

## 2. Tag table

| Tag | M/O | Name | Format (SWIFT notation) |
|---|---|---|---|
| `:20:` | M | Transaction Reference Number | `16x` |
| `:21:` | O | Related Reference (answers an MT920 request) | `16x` |
| `:25:` | M | Account Identification | `35x` — BBAN, `BLZ/account`, IBAN, or `IBAN CCY` |
| `:28C:` (or `:28:`) | M | Statement Number / Sequence Number | `5n[/5n]` |
| `:60F:` / `:60M:` | M | Opening balance (F = first, M = intermediate) | `1!a6!n3!a15d` |
| `:61:` | O, 0–n | Statement line | `6!n[4!n]2a[1!a]15d1!a3!c16x[//16x][34x]` |
| `:86:` | O, 0–n per `:61:` | Information to Account Owner (transaction level) | `6*65x` |
| `:62F:` / `:62M:` | M | Closing balance / intermediate closing balance | `1!a6!n3!a15d` |
| `:64:` | O | Closing available balance | `1!a6!n3!a15d` |
| `:65:` | O, 0–n | Forward available balance (one per future value date) | `1!a6!n3!a15d` |
| `:86:` (after 62/64/65) | O | Information to Account Owner (message level) | `6*65x` |

Notation: `!` fixed length, `a` letters, `n` digits, `x` SWIFT X charset, `d` decimal with **comma** separator, `[]` optional, `6*65x` = up to 6 lines of 65 chars.

## 3. Balance line semantics

`<D|C><YYMMDD><CCY><amount>` — e.g. `:60F:C130101EUR000000001000,00`

1. D/C mark: C = credit balance, D = debit (overdrawn).
2. Date `YYMMDD`. A bank's `:62F:` must equal the next statement's `:60F:`.
3. ISO 4217 currency.
4. Amount, max 15 chars incl. comma; some banks zero-pad (Rabobank), most don't; trailing decimals may be omitted after the comma (`84349,74` vs `6800,` — a bare trailing comma is legal; `EUR2187` with no comma also observed).

**Pagination**: long statements split across messages; `:28C:` carries `statement/sequence` (e.g. `28C:00004/00001`); intermediate pages close with `:62M:` and the next opens with `:60M:` carrying the running balance; final page uses `:62F:`.

## 4. `:61:` statement line — subfield breakdown

| # | Subfield | Format | Notes |
|---|---|---|---|
| 1 | Value date | `6!n` YYMMDD | mandatory |
| 2 | Entry (book) date | `[4!n]` MMDD | optional; **no year** — inferred from value date (year-boundary logic needed); some banks omit it or pad with spaces |
| 3 | D/C mark | `2a` | `D`, `C`, `RD` (reversal of debit), `RC` (reversal of credit) |
| 4 | Funds/capital code | `[1!a]` | optional; often 3rd letter of currency (`R` in EUR); Sberbank(HU) fixture uses `F` |
| 5 | Amount | `15d` | comma decimal; may be zero-padded or comma-terminated |
| 6 | Transaction type ID code | `1!a3!c` | `N`+3 chars (`NTRF`, `NMSC`, `NCHK`, `NSTO`, `N102`, `N426`), `F`+code (`FMSC`), or `S`+3-digit MT number (space-padded `S   ` observed) |
| 7 | Customer reference | `16x` | `NONREF` when absent; Rabobank puts code words here (`EREF`/`MARF`/`PREF`/`NONREF`) pointing at `:86:` content |
| 8 | Bank reference | `[//16x]` | after `//` |
| 9 | Supplementary details | `[34x]` | **on a continuation line**; usage varies wildly — counterparty IBAN (Rabobank), free text (NL banks), or `/OCMT/.../CHGS/...` (German convention). Treat as opaque 34x by default. |

## 5. `:86:` — three structural families

1. **Unstructured free text** — ABN AMRO, ING (NL): human-readable, positional but not code-word delimited.
2. **Slash code words** — Rabobank / SEPA-era Dutch-Nordic style: `/EREF/…/MARF/…/PREF/…/RTRN/…/ACCW/…/BENM/ or /ORDP/` with nested `/NAME/`, `/ID/`, `/ADDR/`, then `/REMI/`, `/CSID/`, `/ISDT/`, `/ULTD/`, `/ULTB/`, `/PURP//CD/` (ISO purpose code).
3. **German DK (DFÜ-Abkommen Annex 3) structure** — first 3 digits = **GVC** (Geschäftsvorfallcode, e.g. 166 credit transfer), then `?`-delimited subfields: `?00` posting text, `?10` primanota, `?20`–`?29` remittance lines (27 chars each) carrying SEPA code words `EREF+`, `KREF+`, `MREF+`, `CRED+`, `DEBT+`, `SVWZ+`, `ABWA+`, `ABWE+`; `?30` counterparty BIC/bank code, `?31` counterparty account/IBAN, `?32`/`?33` counterparty name, `?34` Textschlüsselergänzung, `?60`–`?63` remittance continuation. **Code words may split mid-word across `?2x` boundaries** (rewrap before parsing).

## 6. Continuation lines, character set, real-world tolerance requirements

- Tag content continues on following lines until the next `:xx:` line (or `-` terminator). The 6×65 limit on `:86:` is routinely exceeded in real exports — parse by tag boundaries, not length limits.
- **SWIFT X charset**: `a–z A–Z 0–9 / - ? : ( ) . , ' + { } CR LF space`. Real exports violate it: national characters (Polish, Hungarian), CP1250/CP1252 bytes, tabs, soft hyphens (U+00AD in the ING fixture). Treat input encoding as unknown; never assume ASCII.
- Line endings: CRLF standard; LF-only, missing final newline, and empty lines mid-file all observed.

### Observed bank-variant matrix (from downloaded fixtures)

| Variant | Characteristics |
|---|---|
| ASNB (NL) | Full FIN blocks, many concatenated messages, free-text sf9, unstructured `:86:`; variant with spaces instead of entry date |
| ABN AMRO (NL) | 3-line preamble; `:28:` not `:28C:`; codes `N192`/`N426`; loose decimals (`9,`, `11,8`); unstructured `:86:` |
| ING (NL) | Proprietary header lines; `:28C:000`; `:61:` without entry date; tabs + soft hyphens in `:86:` |
| Rabobank (NL) | `:940:` first line; IBAN in `:25:`; zero-padded amounts; code words in sf7; counterparty IBAN in sf9; slash-structured `:86:` |
| German DK (Sparkasse/Dresdner/legacy) | `:25:` as `BLZ/account`; GVC + `?`-subfields; legacy DEM; `-` statement separators; `EUR2187` no-comma balance; `CR` mark combos |
| mBank (PL) | Leading blank line; `//MB` bank refs; `911-…` sf9; semicolon-separated Polish `:86:`; Windows-1250 bytes |
| Sberbank (HU) | Non-standard `:NS:` tags at statement and transaction level; funds code `F`; space-padded `S` type codes; non-UTF-8 accents |
| Edge cases mapped by mt-940 test suite (not downloaded) | citi, Knab, SNS, Triodos, PostFinance, Raiffeisen; empty `:86:`, empty lines, missing final CRLF, binary characters, February-30 dates, overly long details |

## 7. Reference bibliography (all accessed 2026-08-09)

| Reference | Publisher | Covers |
|---|---|---|
| https://media.rabobank.com/m/6518fca7cb62192a/original/Format-description-SWIFT-MT940-Structured.pdf (v3.331) | Rabobank | Full tag-by-tag spec incl. RD/RC and slash code words. **PDF is copyright Rabobank — facts used, text not copied, PDF not redistributed** |
| https://www.rabobank.com/products/manage-my-trade-and-cash/transaction-banking/swift-for-corporates/downloads | Rabobank | Index of MT940S format PDFs |
| https://www.sepaforcorporates.com/swift-for-corporates/account-statement-mt940-file-format-overview/ | SEPA for Corporates | Tag-level overview, SWIFT notation, 60F/60M semantics |
| https://www.kontopruef.de/mt940s.shtml | kontopruef.de | German DFÜ/DK MT940: `:61:` subfields incl. `/OCMT//CHGS/`, `:86:` GVC + `?00…?63` map, SEPA code words |
| https://danskeci.com/-/media/pdf/danskeci-com/reconciliation/swift-mt/mt940_extended.pdf | Danske Bank | Extended implementation guide (URL recorded; fetch blocked by TLS issue — unverified) |
| https://www.hypovereinsbank.de/content/dam/hypovereinsbank/unternehmen/pdf/Downloadcenter/SEPA-Geschaeftsvorfallcodes-Rueckgabecodes-de.pdf | HypoVereinsbank | GVC + SEPA return code tables |
| https://www.national-bank.de/fileadmin/user_upload/Service/Electronic_Banking_Center/swift_mt940.pdf | National-Bank AG | MultiCash MT940/942 German structure |
| https://developer.gs.com/docs/services/transaction-banking/mt940-gvc-intro/ | Goldman Sachs Developer | MT940 per DFÜ agreement, GVC intro |
| https://www.hettwer-beratung.de/sepa-spezialwissen/sepa-technische-anforderungen/sepa-gesch%C3%A4ftsvorfallcodes-gvc-mt-940/ | Hettwer Beratung | SEPA GVC codes in field 86 |
| https://www.abnamro.nl/en/commercialbanking/products/payments/sepa/downloads.html | ABN AMRO | SEPA guidelines + MT94x Formatenboek index |
| https://en.wikipedia.org/wiki/MT940 | Wikipedia | Positioning; camt.053 as successor |
| https://github.com/WoLpH/mt940 | Rick van Hattem | BSD-3-Clause parser; test corpus is a de-facto variant map |

## 8. Risks & ambiguities (carried into SOURCE-PACK verdict)

1. Rabobank PDF is copyright-restricted — cite facts only; never bundle or quote it.
2. The "Sberbank" fixture is Sberbank **Hungary** (HUF) — labelled accordingly.
3. `:61:` subfield 9 semantics genuinely differ per bank — must be treated as opaque by default with per-variant interpreters.
4. Entry-date year inference is ambiguous at year boundaries; impossible dates (Feb 30) occur in the wild.
5. Charset is a floor, not a guarantee — encoding detection required.
6. `:28:` vs `:28C:`, occasional missing `:62F:` in some public fixtures, bare-comma/no-comma amounts — parser tolerance matrix required.
7. RD/RC semantics confirmed via two agreeing sources (Rabobank + kontopruef.de); Danske PDF unverified.

---

# FORMAT NOTES — camt.053

See `references/camt053/` and the ISO 20022 section of SOURCE-PROVENANCE.md.
Version landscape and V1 target selection: see `spec/V1-SCOPE-RECOMMENDATION.md`.
Element-level mapping: see `spec/DATA-MAPPING-RESEARCH.md`.
