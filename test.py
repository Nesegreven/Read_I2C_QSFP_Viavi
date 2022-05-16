byte_158 = input('9e: ')
byte_159 = input('9f: ')


# Code to convert hex to binary
res = "{0:016b}".format(int(byte_158 + byte_159, 16))


#exponent = res[:5]
#mantissa = res[5:]

# From string in binary to decimal

sumExponent = 0
sumMantissa = 0

for i in range(16):
    if i < 5:
        sumExponent = int(res[i]) * 2 ** (4 - i) + sumExponent
    if i >= 5:
        sumMantissa = int(res[i]) * 2 ** (15 - i) + sumMantissa

if sumMantissa >= 1000:
    print(str(sumMantissa / 1000), "E", str(sumExponent - 21))
else:
    print(str(sumMantissa), "E", str(sumExponent - 24))