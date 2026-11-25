#!/usr/bin/env python3
"""
FXCM instrument health check.

Discovers ALL symbols from the FXCM OFFERS table, then tests them
5 times with 45-second gaps and prints a live / stale / broken summary.

Run inside the Railway container:
    python test_instruments.py
"""

import time

ROUNDS   = 5
INTERVAL = 45  # seconds between rounds


# ======================================================
# HELPERS
# ======================================================

def fmt_price(bid, ask):
    # pick decimal places based on price magnitude
    if bid >= 1000:
        return f"{bid:.2f} / {ask:.2f}"
    elif bid >= 10:
        return f"{bid:.3f} / {ask:.3f}"
    else:
        return f"{bid:.5f} / {ask:.5f}"


def discover_symbols(fx, fxcorepy):
    """Return a sorted list of all symbol names in the FXCM OFFERS table."""
    offers  = fx.get_table(fxcorepy.O2GTableType.OFFERS)
    symbols = []
    for row in offers:
        sym = (
            row.instrument
            .replace("/", "")
            .replace(" ", "")
            .upper()
        )
        symbols.append(sym)
    return sorted(symbols)


# ======================================================
# MAIN
# ======================================================

def main():
    from fxcm import get_price, init_fxcm
    from forexconnect import fxcorepy

    print("=" * 64, flush=True)
    print("FXCM INSTRUMENT HEALTH CHECK", flush=True)
    print(f"Rounds: {ROUNDS}   Interval: {INTERVAL}s", flush=True)
    print("=" * 64, flush=True)

    print("\n🔄 Connecting to FXCM ...", flush=True)
    fx = init_fxcm()
    print("✅ Connected\n", flush=True)

    print("🔍 Discovering symbols from OFFERS table ...", flush=True)
    all_symbols = discover_symbols(fx, fxcorepy)
    print(f"   Found {len(all_symbols)} symbols\n", flush=True)
    for s in all_symbols:
        print(f"   {s}", flush=True)

    # history[symbol] = list of (bid, ask) or None per round
    history = {sym: [] for sym in all_symbols}

    for rnd in range(1, ROUNDS + 1):

        print(f"\n{'─' * 64}", flush=True)
        print(f"  ROUND {rnd}/{ROUNDS}", flush=True)
        print(f"{'─' * 64}", flush=True)

        for symbol in all_symbols:

            try:
                data  = get_price(symbol)
                bid   = data["bid"]
                ask   = data["ask"]
                history[symbol].append((bid, ask))

                prev = history[symbol][-2] if len(history[symbol]) > 1 else None

                if prev is None:
                    tag = "FIRST"
                elif prev[0] != bid or prev[1] != ask:
                    tag = "✅ NEW"
                else:
                    tag = "⚠  SAME"

                print(
                    f"  {symbol:<12}  {fmt_price(bid, ask):>24}  {tag}",
                    flush=True,
                )

            except Exception as err:
                history[symbol].append(None)
                print(f"  {symbol:<12}  ❌ {err}", flush=True)

        if rnd < ROUNDS:
            print(f"\n⏳ Waiting {INTERVAL}s before next round ...\n", flush=True)
            time.sleep(INTERVAL)

    # ======================================================
    # SUMMARY
    # ======================================================

    print(f"\n{'=' * 64}", flush=True)
    print("  SUMMARY", flush=True)
    print(f"{'=' * 64}", flush=True)

    live   = []
    stale  = []
    broken = []

    for symbol in all_symbols:
        entries = history[symbol]

        if any(e is None for e in entries):
            broken.append(symbol)
            continue

        bids = [e[0] for e in entries]
        if len(set(bids)) > 1:
            live.append(symbol)
        else:
            stale.append(symbol)

    print(f"\n✅  LIVE — price moved at least once ({len(live)}):", flush=True)
    for s in live:
        last = history[s][-1]
        print(f"      {s:<12}  {fmt_price(last[0], last[1])}", flush=True)

    print(f"\n⚠   STALE — price never changed ({len(stale)}):", flush=True)
    for s in stale:
        last = history[s][-1]
        print(f"      {s:<12}  {fmt_price(last[0], last[1])}", flush=True)

    print(f"\n❌  BROKEN — fetch failed ({len(broken)}):", flush=True)
    for s in broken:
        print(f"      {s}", flush=True)

    print(f"\n{'=' * 64}", flush=True)
    total = len(live) + len(stale) + len(broken)
    print(
        f"  Live: {len(live)}/{total}   "
        f"Stale: {len(stale)}/{total}   "
        f"Broken: {len(broken)}/{total}",
        flush=True,
    )
    print(f"{'=' * 64}\n", flush=True)


if __name__ == "__main__":
    main()
