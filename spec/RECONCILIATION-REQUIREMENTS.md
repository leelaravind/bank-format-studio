# BALANCE RECONCILIATION REQUIREMENTS

Status: PHASE 0 RESEARCH — defines invariants future conversion logic MUST satisfy. No implementation.
Date: 2026-08-09

## 1. Sign model

All arithmetic uses exact decimal arithmetic (never binary floats).

Signed value of a balance:
```
signed(balance) = +amount  if credit_debit == C
                  -amount  if credit_debit == D
```
(A `D` closing balance is an overdraft — negative account position.)

Signed movement of a transaction (MT940 `:61:` sf3 / camt `CdtDbtInd` + `RvslInd`):
```
C   → +amount        (credit)
D   → -amount        (debit)
RD  → +amount        (reversal of a debit: funds move credit-direction)  [MT940]
RC  → -amount        (reversal of a credit: funds move debit-direction)  [MT940]
camt: CdtDbtInd CRDT → +, DBIT → -; RvslInd=true does NOT flip the sign —
      camt reversal entries already carry the movement direction in CdtDbtInd.
```
The RD/RC ↔ (CdtDbtInd, RvslInd) mapping above must itself be verified by test
fixtures, because it is a classic implementation bug source. Working hypothesis
to verify against sources: `RD` ↔ `CRDT + RvslInd=true`, `RC` ↔ `DBIT + RvslInd=true`.

## 2. Primary invariant (per statement page-set, single currency)

```
INV-1:  signed(opening) + Σ signed(movement_i) = signed(closing)
```
- MT940: opening = `:60F:` (or `:60M:`), closing = `:62F:` (or `:62M:`), movements = all `:61:` lines between them.
- camt.053: opening = `Bal[OPBD]`, closing = `Bal[CLBD]`, movements = all `Ntry` with `Sts=BOOK`.

## 3. Supporting invariants

```
INV-2  (currency consistency, MT940): currency of :60x:, :62x:, :64:, :65: must share
       the same ISO code (first two letters must match; 3rd char may differ per SWIFT
       usage rules — verify). All movements are implicitly in statement currency.
INV-3  (currency consistency, camt): Bal[OPBD].Ccy == Bal[CLBD].Ccy == Acct.Ccy when
       present; entries whose Amt/@Ccy differs from account currency must trigger a
       WARNING and are excluded from INV-1 only if the file provides no equivalent
       account-currency amount (then reconciliation FAILS with explanation).
INV-4  (page chaining, MT940): for multi-page statements, :62M: of page n must equal
       :60M: of page n+1 (amount, C/D, currency); the chain ends in :62F:.
       :28C: statement number must be identical across pages; sequence numbers
       strictly increasing.
INV-5  (camt totals cross-check): when Stmt/TxsSummry is present, NbOfNtries,
       TtlCdtNtries/Sum and TtlDbtNtries/Sum must match the counted/summed entries;
       mismatch → WARNING (bank data error), not silent acceptance.
INV-6  (date sanity): booking/value dates should fall within FrToDt period when
       given (WARNING otherwise); balance dates: closing date ≥ opening date.
INV-7  (conversion conservation): after ANY conversion A→B, opening, closing,
       Σ credits, Σ debits, and transaction count computed from B must equal those
       computed from A. This is the product's core "balance reconciliation" promise.
INV-8  (round-trip conservation): A→B→A′ must preserve INV-7 quantities exactly;
       field-level differences are allowed only where DATA-MAPPING-RESEARCH.md
       documents loss, and each must be listed in the information-loss report.
```

## 4. Statement-level derived figures (reported to user)

- total credits = Σ amount where signed > 0 (including RD)
- total debits = Σ amount where signed < 0 (including RC)
- transaction count, credit count, debit count
- computed closing vs declared closing, with difference if any

## 5. Edge cases that MUST have test coverage

| # | Case | Expected behaviour |
|---|---|---|
| E1 | Zero transactions (`:60F:` directly followed by `:62F:`) | valid; INV-1 with empty sum; opening == closing |
| E2 | Multi-page MT940 (`:60M:/:62M:` chain) | INV-4 enforced; reconciliation runs over the whole chain and per page |
| E3 | Reversals (RD/RC, RvslInd) | sign rules of §1; round-trip preserves reversal flag |
| E4 | Balance stated as `D` (overdraft) crossing zero mid-statement | signed arithmetic handles sign change |
| E5 | Multiple balance types in camt (OPBD, CLBD, CLAV, FWAV, ITBD, PRCD) | only OPBD/CLBD drive INV-1; PRCD (previous closing) may substitute OPBD when OPBD absent — verify against real files; others carried through/reported |
| E6 | camt entry with Sts != BOOK | excluded from INV-1; WARNING; not convertible to MT940 |
| E7 | Duplicate entries (identical refs, amount, dates) | not an arithmetic error — reconcile normally but emit duplicate WARNING |
| E8 | Currency mismatch across balances | hard validation error |
| E9 | Amount with more decimal places than ISO 4217 allows for the currency (e.g. 3 dp for EUR, 2 dp for JPY where 0 allowed) | WARNING (JPY with decimals); arithmetic still exact |
| E10 | Declared closing ≠ computed closing | reconciliation FAILURE with human-readable diff (amount and which side) |
| E11 | Partial statement (missing `:62F:`) | hard parse/validation error; never guess a closing balance |
| E12 | Statement number/sequence gaps across files in one batch | WARNING (possible missing statement) |
| E13 | camt batch entry (1 Ntry, n TxDtls) | Ntry amount must equal Σ TxDtls amounts when details carry amounts; reconcile at Ntry level |
| E14 | 15-digit MT940 maximum amount / very large values | exact decimal, no overflow, no scientific notation on output |

## 6. Test requirements derived from this document

Each invariant INV-1..8 and edge case E1..E14 must map to at least one fixture in
`spec/FIXTURE-PLAN.md` and, where conversion is involved, one golden case per
`spec/GOLDEN-CASE-REQUIREMENTS.md`. No production code exists yet; these are
acceptance criteria for the future implementation plan.
