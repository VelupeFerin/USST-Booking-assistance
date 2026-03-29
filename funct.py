import time


def get_current_time():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def waiting_until(time_args):
    if time_args[2] < 0:
        return
    t = time.localtime()
    time.sleep((3600 * (time_args[0] - t.tm_hour) + 60 * (time_args[1] - t.tm_min) + time_args[2] - t.tm_sec) % 86400)


def grt_sqc(cmp, n):
    if cmp == "516":
        k = 19
    else:
        k = 8
    if n == k:
        return range(k, 0, -1)
    sequence = [n]
    c = 1
    addn = n + c
    while 1 <= addn <= k:
        sequence.append(addn)
        c *= -1
        if c > 0:
            c += 1
        addn = n + c
    if c > 0:
        for j in range(n - c, 0, -1):
            sequence.append(j)
    else:
        for j in range(k, n - c, -1):
            sequence.append(j)
    return sequence
