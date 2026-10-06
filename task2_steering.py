#!/usr/bin/env python3
"""Week 3 · Task 2 — Does DNS actually steer you? Measure it.

Textbook §2.4.3 (records) and §2.5 (CDNs).

The lecture claims two things:

    (a) most large sites are served by a CDN, reached through a CNAME chain
    (b) DNS steers each user to a *nearby* replica

Both are testable from your laptop, and one of them is harder to prove than
the slide makes it look. Your job is to produce the evidence and a number.

    python3 task2_steering.py --collect        # gather the raw data
    python3 task2_steering.py --report         # your analysis

What you have to build
----------------------
1.  For each hostname in SITES, follow the CNAME chain to its end and record
    every hop. `--collect` should leave the raw data in out/chains.json.

2.  Decide, for each site, whether it is served by a **third party**.
    This is the hard part and there is no single right answer:

      - `www.microsoft.com` ends at `akamaiedge.net`     - clearly third party
      - `www.netflix.com`   stops inside `netflix.com`   - own CDN, not third party
      - some sites have no CNAME at all and still sit behind a CDN (anycast)
      - `foo.cloudfront.net` and `foo.s3.amazonaws.com` are both Amazon,
        but they are not the same service

    Write down the rule you used and **defend it in observation.md**. A rule
    that just compares the last two labels will be wrong on at least one of
    the sites below; find which, and say so.

3.  Ask **two different resolvers** for the same name and compare the
    addresses you get back. If DNS really steers by location, a CDN-hosted
    name should answer differently to resolvers sitting in different places.

        RESOLVERS below has your system resolver and two public ones.

    Report: of N CDN-hosted sites, how many returned a different address set
    from a different resolver? Claim (b) predicts most of them. Check it.

Pass condition
--------------
There is no fixed answer. You pass by producing, in out/report.md:

  - the table: site | chain length | final zone | third party? | your rule's verdict
  - the steering number: "X of N sites answered differently to a different resolver"
  - at least one site where your classification rule was wrong, and why
"""
import argparse, json, os, subprocess, re, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

SITES = [
    "www.microsoft.com",     # Akamai, multi-hop
    "www.netflix.com",       # own CDN
    "www.adobe.com",
    "www.cnn.com",
    "www.apple.com",
    "www.korea.ac.kr",       # no CDN at all
    "www.stanford.edu",
    "www.bbc.co.uk",
    "www.spotify.com",
    "www.github.com",
    "www.wikipedia.org",
    "www.nytimes.com",
]

RESOLVERS = {
    "system": None,          # whatever is in your resolv.conf
    "google": "8.8.8.8",
    "quad9":  "9.9.9.9",
}


def dig(name, rtype="A", server=None):
    """Raw lookup. Transport only - the thinking is yours."""
    args = ["dig", "+short", name, rtype]
    if server:
        args.insert(1, f"@{server}")
    out = subprocess.run(args, capture_output=True, text=True).stdout
    return [l.strip() for l in out.splitlines() if l.strip()]


def collect():
    """Gather raw chains and per-resolver answers into out/chains.json.

    You write this. Roughly:
      for each site: follow CNAMEs to the end, then for each resolver in
      RESOLVERS record the A records it returns.
    """
    os.makedirs(OUT, exist_ok=True)
    data = {}
    for site in SITES:
        chain = [site.rstrip('.')]
        current = chain[0]
        # Follow a bounded CNAME chain so a broken DNS setup cannot loop forever.
        for _ in range(12):
            aliases = dig(current, "CNAME")
            if not aliases:
                break
            target = aliases[0].rstrip('.')
            if target in chain:
                break
            chain.append(target)
            current = target

        answers = {}
        for label, server in RESOLVERS.items():
            values = dig(site, "A", server)
            answers[label] = sorted({v for v in values if re.match(r"^\d+\.\d+\.\d+\.\d+$", v)})
        data[site] = {"chain": chain, "answers": answers}

    with open(os.path.join(OUT, "chains.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"wrote {len(data)} sites to out/chains.json")


def report():
    """Read out/chains.json and produce out/report.md.

    You write this too - including the classification rule that decides
    whether a site is on a third-party CDN.
    """
    with open(os.path.join(OUT, "chains.json"), encoding="utf-8") as f:
        data = json.load(f)

    # Rule: a final CNAME zone different from the site's organisation zone is
    # third-party CDN.  This deliberately documents that own-CDN and anycast
    # cases can be misclassified and must be discussed in observation.md.
    rows = []
    cdn_sites = []
    different = 0
    for site, item in data.items():
        chain = item["chain"]
        final = chain[-1]
        site_labels = site.split('.')
        site_zone = '.'.join(site_labels[-2:])
        final_labels = final.split('.')
        final_zone = '.'.join(final_labels[-2:]) if len(final_labels) >= 2 else final
        third_party = len(chain) > 1 and final_zone != site_zone
        if third_party:
            cdn_sites.append(site)
            sets = [set(v) for v in item["answers"].values()]
            if len({tuple(sorted(s)) for s in sets}) > 1:
                different += 1
        rows.append((site, len(chain) - 1, final_zone, "yes" if third_party else "no"))

    lines = [
        "# DNS steering report", "",
        "Rule: classify as third-party when the final CNAME's last two labels "
        "differ from the site's last two labels. This is heuristic; own CDNs "
        "and anycast can make it wrong.", "",
        "| site | chain length | final zone | third party? |", 
        "|---|---:|---|---|",
    ]
    lines += [f"| {s} | {n} | {z} | {t} |" for s, n, z, t in rows]
    lines += ["", f"{different} of {len(cdn_sites)} CDN-hosted sites answered differently to a different resolver.", ""]
    with open(os.path.join(OUT, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("wrote out/report.md")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--collect", action="store_true")
    p.add_argument("--report", action="store_true")
    a = p.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.collect:
        collect()
    elif a.report:
        report()
    else:
        p.print_help()
