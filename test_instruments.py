#!/usr/bin/env python3
"""
FXCM instrument health check.

Tests every forex pair and commodity 5 times with 45-second gaps,
then prints a summary of which instruments are live, stale, or broken.

Run on Railway:
    railway run python test_instruments.py
"""

import time

# ======================================================
# ALL FXCM SYMBOLS TO TEST
# ======================================================

FOREX = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD",
    "AUDUSD", "NZDUSD",
    "EURGBP", "EURJPY", "EURCHF", "EURAUD",
    "GBPJPY", "GBPCHF", "GBPAUD",
    "AUDJPY", "CADJPY", "CHFJPY", "NZDJPY",
    "AUDCAD", "AUDNZD", "EURNZD", "GBPCAD",
]

COMMODITIES = [
    "XAUUSD", "XAGUSD", "USOIL", "COPPER",
]

ALL_SYMBOLS = FOREX + COMMODITIES

ROUNDS    = 5
INTERVAL  = 45  # seconds between rounds


# ======================================================
# HELPERS
# ======================================================

def fmt(symbol, bid, ask):
    if symbol in ("XAUUSD", "XAGUSD", "USOIL", "COPPER"):
        return f"{bid:.2f} / {ask:.2f}"
    return f"{bid:.5f} / {ask:.5f}"


# ======================================================
# MAIN
# ======================================================

def main():
    from fxcm import get_price, init_fxcm

    print("=" * 64, flush=True)
    print("FXCM INSTRUMENT HEALTH CHECK", flush=True)
    print(f"Symbols: {len(ALL_SYMBOLS)}   Rounds: {ROUNDS}   Interval: {INTERVAL}s", flush=True)
    print("=" * 64, flush=True)

    print("\n🔄 Connecting to FXCM ...", flush=True)
    init_fxcm()
    print("✅ Connected\n", flush=True)

    # history[symbol] = list of (bid, ask) or None per round
    history = {sym: [] for sym in ALL_SYMBOLS}

    for rnd in range(1, ROUNDS + 1):

        print(f"\n{'─' * 64}", flush=True)
        print(f"  ROUND {rnd}/{ROUNDS}", flush=True)
        print(f"{'─' * 64}", flush=True)

        for symbol in ALL_SYMBOLS:

            try:
                data  = get_price(symbol)
                bid   = data["bid"]
                ask   = data["ask"]
                entry = (bid, ask)
                history[symbol].append(entry)

                prev = history[symbol][-2] if len(history[symbol]) > 1 else None

                if prev is None:
                    tag = "FIRST"
                elif prev[0] != bid or prev[1] != ask:
                    tag = "✅ NEW"
                else:
                    tag = "⚠  SAME"

                print(
                    f"  {symbol:<10}  {fmt(symbol, bid, ask):>22}  {tag}",
                    flush=True,
                )

            except Exception as err:
                history[symbol].append(None)
                print(f"  {symbol:<10}  ❌ {err}", flush=True)

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

    for symbol in ALL_SYMBOLS:

        entries = history[symbol]

        if any(e is None for e in entries):
            broken.append(symbol)
            continue

        bids = [e[0] for e in entries]

        if len(set(bids)) > 1:
            live.append(symbol)
        else:
            stale.append(symbol)

    print(f"\n✅  LIVE — price changed at least once ({len(live)}):", flush=True)
    for s in live:
        last = history[s][-1]
        print(f"      {s:<10}  {fmt(s, last[0], last[1])}", flush=True)

    print(f"\n⚠   STALE — connected but price never moved ({len(stale)}):", flush=True)
    for s in stale:
        last = history[s][-1]
        print(f"      {s:<10}  {fmt(s, last[0], last[1])}", flush=True)

    print(f"\n❌  BROKEN — fetch failed every round ({len(broken)}):", flush=True)
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
