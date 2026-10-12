# Week 4 관찰 기록

## Task 1

Stop-and-wait 방식으로 패킷에 순번을 부여하고 ACK를 받지 못한 패킷은 재전송했다. 수신자는 순서가 맞는 패킷만 조립하고 중복·순서 변경 패킷은 무시했다.
2,000바이트 전송의 최소 패킷 수는 250개이며, 실제 전송 패킷 수는 379개였다. 손실이 전송을 가장 먼저 지연시켰고 순번과 ACK로 중복 및 순서 변경을 처리했다.

## Task 2

SYN, SYN-ACK, ACK와 양쪽 initial sequence number, MSS, window scale, SACK 옵션을 확인했다. Sequence number는 연결마다 임의의 초기값을 사용하므로 0이 아니다.
Campus Wi-Fi의 median throughput은 168.43 Mbps, tethering은 174.46 Mbps이며, handshake 시간과 네트워크 혼잡이 spread에 영향을 주었다. 실제 병목은 수신 window보다 RTT와 네트워크 용량이었다.

## Task 3

FixedWindow은 window를 64로 고정해 goodput은 높지만 큐를 가득 채우고 손실과 지연을 증가시킨다. 따라서 공유 링크에서는 다른 흐름의 성능을 악화시키는 sender이다.
YourControl은 ACK마다 window를 조금씩 증가시키고 loss 발생 시 절반으로 줄이며 약 20패킷까지 사용한다. 이 방식은 손실과 평균 큐를 제한하면서 goodput을 안정적으로 유지한다.
