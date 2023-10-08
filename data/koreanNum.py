num_map = {
    '하나': 1, '한': 2, '둘': 2, '두': 2, '셋': 3, '세': 3, '넷': 4, '네': 4, '다섯': 5, '여섯': 6, '일곱': 7, '여덟': 8, '아홉': 9, '열': 10
}

def korean_to_number(word):
    return num_map.get(word, None)
