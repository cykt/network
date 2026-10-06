#!/usr/bin/env python3
"""Week 3 · Task 1 — Build your own iterative resolver.

Textbook §2.4.2 - §2.4.3.

`dig +trace` walks root -> TLD -> authoritative for you. In this task you do
that walk yourself: start at a root server, read the delegation it returns,
ask the next server, and keep going until somebody answers authoritatively.

You may shell out to `dig` for the transport, or use a DNS library
(`dnspython` is in the container). Either is fine - what matters is that
*you* follow the delegations rather than letting a tool do it.

    python3 task1_resolve.py www.korea.ac.kr
    python3 task1_resolve.py --verify        # check yourself against dig

Pass condition
--------------
`--verify` resolves five names with your resolver and with `dig`, and the
addresses must agree. A name behind a CDN may legitimately return a different
address each time; the harness compares the *set of authoritative nameservers*
you ended at for those, not the address.
"""
import argparse, subprocess, sys

try:
    import dns.flags, dns.message, dns.query, dns.rcode, dns.rdatatype
    _HAS_DNSPYTHON = True
except ImportError:                       # the dig-based path still works without it
    _HAS_DNSPYTHON = False


# Root servers. Everything starts here; there is no earlier step.
ROOT_SERVERS = [
    "198.41.0.4",       # a.root-servers.net
    "199.9.14.201",     # b.root-servers.net
    "192.33.4.12",      # c.root-servers.net
]

# (name, kind).  "stable" names must match dig exactly.  "cdn" names are served
# from many replicas and may legitimately give you a different address than dig
# got a second earlier - for those we only require that you reached an answer.
VERIFY_NAMES = [
    ("www.korea.ac.kr", "stable"),
    ("dns.google", "stable"),
    ("en.wikipedia.org", "stable"),
    ("www.stanford.edu", "stable"),
    ("www.microsoft.com", "cdn"),
]


class Resolver:
    """Your iterative resolver.

    The whole point is that you never ask a server to recurse for you.
    You ask one server, it says "not mine, ask over there", and you go there.

    Suggested shape - but it is yours to design:

        resolve(name) -> (address, path)
            address : the A record you ended up with, as a string
            path    : the servers you asked, in order, so you can show your work

    Things you will hit, in roughly this order:

    1.  A delegation gives you NS *names*, sometimes with glue A records and
        sometimes without. No glue means you have to resolve that nameserver's
        name first - which is another walk. Decide what you do there.
    2.  A server may not answer. Try the next one rather than giving up.
    3.  CNAMEs. The answer you get back may be a different name than the one
        you asked for, and you have to start again with that name.
    4.  Loops. Cap your depth.

    If you shell out to dig, the flag you want is `+norecurse`, so that the
    server you ask replies with a delegation instead of doing the work:

        dig @198.41.0.4 www.korea.ac.kr +norecurse
    """

    MAX_DEPTH = 16                        # R6: a malformed zone must not hang us
    TIMEOUT = 3.0                         # seconds per server attempt

    def __init__(self):
        self.path = []                    # every server we asked, in order

    def resolve(self, name):
        """R1: returns (address, path). R2: starts at ROOT_SERVERS, never recurses."""
        if not _HAS_DNSPYTHON:
            raise RuntimeError("dnspython is not installed - pip install dnspython")
        self.path = []
        address, _ = self._walk(name.rstrip("."), depth=0)
        return address, list(self.path)

    # ------------------------------------------------------------- transport
    def _query(self, server, name):
        """One iterative query: RD off (R2). None if the server does not answer."""
        q = dns.message.make_query(name, "A")
        q.flags &= ~dns.flags.RD                          # no recursion, please
        try:
            r = dns.query.udp(q, server, timeout=self.TIMEOUT)
            if r.flags & dns.flags.TC:                    # truncated -> redo over TCP
                r = dns.query.tcp(q, server, timeout=self.TIMEOUT + 2)
            return r
        except Exception:
            return None                                   # R4: fall through to next

    # ------------------------------------------------------------- the walk
    def _walk(self, name, depth):
        """Ask servers until one answers. Returns (address, path-so-far).

        Three outcomes per response:
          - ANSWER holds an A record          -> done
          - ANSWER holds a CNAME              -> restart the walk on the target (R5)
          - AUTHORITY holds NS records        -> follow the delegation, resolving
                                                 any NS name that arrives without
                                                 glue first (R3)
        """
        if depth > self.MAX_DEPTH:
            raise RuntimeError(f"depth cap exceeded while resolving {name!r}")

        queue = list(ROOT_SERVERS)
        asked = set()                     # (server, name) pairs - no repeats
        while queue:
            server = queue.pop(0)
            if (server, name) in asked:
                continue
            asked.add((server, name))
            self.path.append(server)

            resp = self._query(server, name)
            if resp is None:
                continue
            if resp.rcode() == dns.rcode.NXDOMAIN:
                raise RuntimeError(f"{name!r}: NXDOMAIN")

            # --- answer section: A records win, a lone CNAME restarts (R5)
            arecords, cname = [], None
            for rr in resp.answer:
                if rr.rdtype == dns.rdatatype.A:
                    arecords.append(rr[0].to_text())
                elif rr.rdtype == dns.rdatatype.CNAME and cname is None:
                    cname = rr[0].to_text().rstrip(".")
            if arecords:
                return arecords[0], self.path
            if cname:
                return self._walk(cname, depth + 1)

            # --- authority section: the delegation
            ns_names = []
            for rr in resp.authority:
                if rr.rdtype == dns.rdatatype.NS:
                    ns_names.append(rr[0].to_text().rstrip("."))
            if not ns_names:              # no answer, no delegation - try next
                continue

            glue = {}
            for rr in resp.additional:
                if rr.rdtype == dns.rdatatype.A:
                    glue.setdefault(rr.name.to_text().rstrip("."), []) \
                        .append(rr[0].to_text())

            # glue first (free), then NS names we have to resolve ourselves (R3)
            candidates = []
            for ns in ns_names:
                candidates.extend(glue.get(ns, []))
            for ns in ns_names:
                if ns in glue:
                    continue
                try:
                    ns_ip, _ = self._walk(ns, depth + 1)   # nested walk
                except Exception:
                    continue               # this nameserver is unresolvable
                candidates.append(ns_ip)

            queue = candidates + queue     # next level first, leftovers as backup

        raise RuntimeError(f"no authoritative answer for {name!r} from any server")


# ------------------------------------------------------------------- harness
def dig_answer(name):
    """What the system resolver says, for comparison."""
    out = subprocess.run(["dig", "+short", name, "A"],
                         capture_output=True, text=True).stdout
    return [l for l in out.split() if l and l[0].isdigit()]


def verify():
    r, failures = Resolver(), 0
    for name, kind in VERIFY_NAMES:
        try:
            addr, path = r.resolve(name)
        except NotImplementedError:
            print("Nothing implemented yet - write Resolver.resolve first.")
            return 1
        except Exception as e:
            print(f"  FAIL  {name:<22} your resolver raised {e!r}")
            failures += 1
            continue
        expected = dig_answer(name)
        if addr in expected:
            note = ""
        elif kind == "cdn":
            note = "  <- differs, but this name is CDN-hosted. Explain it."
        else:
            note = "  <- should have matched"
            failures += 1
        print(f"  {'FAIL' if note.endswith('matched') else 'ok  '}  {name:<22} "
              f"you={addr:<16} dig={','.join(expected) or '-'}   "
              f"hops={len(path)}{note}")
    print(f"\n  {len(VERIFY_NAMES) - failures}/{len(VERIFY_NAMES)} ok")
    return 1 if failures else 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("name", nargs="?", default="www.korea.ac.kr")
    p.add_argument("--verify", action="store_true")
    a = p.parse_args()

    if a.verify:
        sys.exit(verify())

    addr, path = Resolver().resolve(a.name)
    for i, server in enumerate(path, 1):
        print(f"  {i}. asked {server}")
    print(f"\n  {a.name} -> {addr}")


if __name__ == "__main__":
    main()
