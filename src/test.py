def f1(a, b, c):
    return a + b + c

a = 1
bc = [2, 3]

print(f1(a, *bc))

import datetime as dt
print(dt.datetime.now(dt.UTC))