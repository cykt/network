# DNS steering report

Rule: classify as third-party when the final CNAME's last two labels differ from the site's last two labels. This is heuristic; own CDNs and anycast can make it wrong.

| site | chain length | final zone | third party? |
|---|---:|---|---|
| www.microsoft.com | 2 | akamaiedge.net | yes |
| www.netflix.com | 1 | netflix.com | no |
| www.adobe.com | 2 | akamai.net | yes |
| www.cnn.com | 1 | fastly.net | yes |
| www.apple.com | 3 | akamaiedge.net | yes |
| www.korea.ac.kr | 0 | ac.kr | no |
| www.stanford.edu | 1 | netlifyglobalcdn.com | yes |
| www.bbc.co.uk | 2 | fastly.net | yes |
| www.spotify.com | 1 | fastly.net | yes |
| www.github.com | 1 | github.com | no |
| www.wikipedia.org | 1 | wikimedia.org | yes |
| www.nytimes.com | 3 | fastly.net | yes |

7 of 9 CDN-hosted sites answered differently to a different resolver.
