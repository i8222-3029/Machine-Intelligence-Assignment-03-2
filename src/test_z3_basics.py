"""
Z3 기본 설정 및 탐색 - 테스트 파일
섹션 1: Bool 변수와 기본 논리 연산 테스트
"""

from z3 import Bool, Bools, Or, And, Not, Solver

print("=" * 60)
print("Z3 기본 설정 및 탐색 테스트")
print("=" * 60)

# 1. Bool 변수 생성
print("\n1. Bool 변수 생성")
P, Q = Bools('P Q')
print(f"P = {P}, Q = {Q}")

# 2. Solver 생성
s = Solver()
print(f"\nSolver 생성: {s}")

# 3. 쌍조건문 추가: P == Q
print("\n2. 쌍조건문 추가: P == Q")
s.add(P == Q)
print("s.add(P == Q) 완료")

# 4. 사실 추가: P == True
print("\n3. 사실 추가: P == True")
s.add(P)
print("s.add(P) 완료")

# 5. 만족 가능성 확인
print("\n4. 만족 가능성 확인")
result = s.check()
print(f"s.check() 결과: {result}")

# 6. 모델 검사
print("\n5. 모델 검사")
model = s.model()
print(f"s.model(): {model}")
print(f"P 값: {model[P]}")
print(f"Q 값: {model[Q]}")

print("\n" + "=" * 60)
print("모든 테스트 완료!")
print("=" * 60)
