# Week 3 · observation

# Observation

## Task 1
루트 서버는 최종 IP가 아니라 TLD의 NS delegation을 반환하므로 resolver는 `198.41.0.4 → 210.101.61.1 → 163.152.11.6` 순서로 authoritative 서버까지 질의했다.
glue A가 없으면 NS 이름을 다시 해석하고, CNAME은 대상 이름을 재질의하도록 처리했다.

## Task 2
최종 CNAME의 조직 도메인이 원래 사이트와 다르면 third-party CDN으로 분류했으며, 9개 중 7개가 resolver별로 다른 주소를 반환했다.
이 규칙은 Netflix 같은 자체 CDN과 CNAME 없는 anycast CDN을 오판할 수 있다.

## Task 3
Baseline은 고정 60초 캐시로 TTL을 무시해 stale 266개를 만들었지만, YourCache는 실제 TTL을 사용해 stale 0개와 upstream 275회를 기록했다.
각 이름은 최초 조회와 TTL 만료 후 재조회가 필요하므로 이 workload에서 올바른 캐시의 최소 upstream 질의 수는 275회다.